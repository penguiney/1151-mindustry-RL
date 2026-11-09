"""Drive a Mindustry headless server as a subprocess.

The server reads commands from stdin and logs to stdout. Output is drained on a
background thread: letting the pipe buffer fill would block the server itself,
which looks exactly like a hang in the game and wastes an afternoon.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import subprocess
import threading
import time
from pathlib import Path

# Mindustry colourises its log when it believes a capable terminal is attached, which
# happens on Linux but not under the dumb terminal Windows gives it. Stripping the
# escapes here keeps patterns identical across platforms; matching them in every
# caller instead would be a permanent source of tests that pass on one OS only.
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Printed once the server has finished loading and is accepting commands.
READY_PATTERN = r"Server loaded\.|Opened a server|Loaded \d+ mod"


#: Windows takes a creation flag; POSIX takes a `nice` call before exec.
_BELOW_NORMAL: dict[str, object]
if sys.platform == "win32":
    _BELOW_NORMAL = {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS}
else:
    _BELOW_NORMAL = {"preexec_fn": lambda: os.nice(5)}


#: Logical processors kept away from the servers, so something is always free to draw.
#:
#: Below-normal priority was not enough on its own, and the measurement says why: with
#: twenty-four servers the machine sat at 96%, java taking 73.7% and the browser watching
#: it 2.0%. Lowering the priority moved the browser to 3.6%, because a priority only
#: decides who wins a contested slice and a bursty renderer rarely turns up to contest one.
#:
#: Reserving is different: these cores are not offered to the servers at all, so the
#: desktop has somewhere to run without asking. Two physical cores, which on this hardware
#: is four logical ones, is the smallest reservation that keeps a browser smooth, and it
#: costs the run about a sixteenth of its throughput.
RESERVED_CORES = 4

#: Set to False by a caller that wants the machine to itself.
#:
#: The polite behaviour is the default because a run that makes the desktop unusable gets
#: stopped, and a stopped run learns nothing. But it is a trade and the numbers should be
#: stated: on this machine, with a game also running, the servers went from about 330 steps
#: a second to 153 while the browser watching them went from frozen to smooth.
POLITE = True


def _reserve_cores_for_the_desktop(pid: int) -> None:
    """Keep a headless server off the last few logical processors.

    Best effort by design: a machine with too few cores to spare, or an OS that will not
    say, gets the default behaviour rather than an exception in the middle of starting a
    run.
    """
    total = os.cpu_count() or 0
    if not POLITE or total <= RESERVED_CORES * 2:
        return

    mask = (1 << (total - RESERVED_CORES)) - 1
    try:
        if sys.platform == "win32":
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x0200 | 0x0400, False, pid)
            if handle:
                ctypes.windll.kernel32.SetProcessAffinityMask(handle, ctypes.c_size_t(mask))
                ctypes.windll.kernel32.CloseHandle(handle)
        elif hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(pid, range(total - RESERVED_CORES))
    except Exception:
        pass


#: Started stopped, so it can be put in its job before it runs a single instruction.
_CREATE_SUSPENDED = 0x00000004


class _Job:
    """A Windows job object: everything in it dies when Python lets go of it.

    `java` on PATH is Oracle's javapath launcher, which starts the real JVM as a child and
    waits on it. Killing what `Popen` returned killed the launcher and left the JVM
    running, and so did any exit that never reached `__exit__`: a forced stop of Python,
    or an exception before the caller closed the environment. Found as two evaluations' servers still holding port 7910 after both
    Pythons were gone, which is how the next run gets "BRIDGE FAILED".

    A job takes the whole tree, launcher and JVM, because a child started inside a job
    joins it. Its last handle is closed by the OS when Python exits however it exits, and
    the job is created to kill everything in it at that moment.

    Best effort, like the core reservation: a machine where any of this is refused gets
    the old behaviour rather than a server that will not start.
    """

    def __init__(self) -> None:
        self.handle = None
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            class Basic(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                            ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class Extended(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", Basic),
                            ("IoInfo", ctypes.c_uint64 * 6),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateJobObjectW.restype = wintypes.HANDLE
            kernel32.SetInformationJobObject.argtypes = [
                wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            handle = kernel32.CreateJobObjectW(None, None)
            if not handle:
                return
            limits = Extended()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
            # 9 is JobObjectExtendedLimitInformation.
            if kernel32.SetInformationJobObject(handle, 9, ctypes.byref(limits),
                                                ctypes.sizeof(limits)):
                self.handle = handle
            else:
                kernel32.CloseHandle(handle)
        except Exception:
            self.handle = None

    def adopt(self, pid: int) -> None:
        """Put a suspended process in the job, then let it run. Resumes it either way."""
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        # SET_QUOTA | TERMINATE | SUSPEND_RESUME, what assigning and resuming need.
        process = kernel32.OpenProcess(0x0100 | 0x0001 | 0x0800, False, pid)
        try:
            kernel32.AssignProcessToJobObject(self.handle, process)
            # Before it runs, so the JVM the launcher starts inherits the reservation.
            _reserve_cores_for_the_desktop(pid)
        finally:
            ntdll.NtResumeProcess(process)
            kernel32.CloseHandle(process)

    def kill(self) -> None:
        """End everything in the job, the JVM included."""
        if self.handle is None:
            return
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject(self.handle, 1)


class ServerProcess:
    """A running headless server, usable as a context manager."""

    def __init__(
        self,
        server_dir: Path,
        java: str = "java",
        jvm_args: list[str] | None = None,
        start_timeout: float = 120.0,
        port: int | None = None,
    ) -> None:
        self.server_dir = Path(server_dir)
        self.java = java
        self.jvm_args = jvm_args or []
        self.start_timeout = start_timeout
        # Every instance binds a listen port even when nothing connects to it, so
        # parallel instances need distinct ports or all but the first fail to host.
        self.port = port
        self._proc: subprocess.Popen[str] | None = None
        self._lines: list[str] = []
        self._lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._job = _Job()

    def __enter__(self) -> ServerProcess:
        options: dict[str, object] = dict(_BELOW_NORMAL) if POLITE else {}
        if self._job.handle is not None:
            options["creationflags"] = int(options.get("creationflags", 0)) | _CREATE_SUSPENDED
        self._proc = subprocess.Popen(
            [self.java, *self.jvm_args, "-jar", "server-release.jar"],
            cwd=self.server_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            # Below the rest of the desktop, deliberately.
            #
            # Twenty-four servers saturate the machine: measured on a live run, 73.7% of a
            # sixteen core box in java and 2.0% in the browser watching it. The dashboard
            # was not slow, it was starved, and no amount of work on the rendering can give
            # a thread time it is not being scheduled.
            #
            # Below-normal costs the run almost nothing, because nothing else on the
            # machine wants the CPU most of the time and the servers still take every idle
            # cycle. What changes is that the moment somebody moves a mouse, the window
            # answering them wins.
            **options,
        )
        if self._job.handle is not None:
            self._job.adopt(self._proc.pid)
        else:
            _reserve_cores_for_the_desktop(self._proc.pid)

        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()
        self.wait_for(READY_PATTERN, timeout=self.start_timeout)
        if self.port is not None:
            self.command(f"config port {self.port}", r"port.*set to|Port|port", timeout=20)
        return self

    def _pump(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            clean = ANSI_ESCAPE.sub("", line).rstrip("\r\n")
            with self._lock:
                self._lines.append(clean)

    def send(self, command: str) -> None:
        """Write one command to the server console."""
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("server is not running")
        self._proc.stdin.write(command + "\n")
        self._proc.stdin.flush()

    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def mark(self) -> int:
        """Current output position, for use as `since` in a later `wait_for`."""
        with self._lock:
            return len(self._lines)

    def command(self, command: str, pattern: str, timeout: float = 30.0) -> str:
        """Send a command and return the first line it produces that matches.

        Prefer this over `send` followed by `wait_for`. It records the output position
        before writing, so a command issued twice in one session cannot match the reply
        to the earlier one, and it cannot miss a reply that arrives immediately either.
        """
        since = self.mark()
        self.send(command)
        return self.wait_for(pattern, timeout=timeout, since=since)

    def wait_for_bridge(self, port: int, timeout: float = 90.0) -> str:
        """Block until the bridge is listening, or say why it is not.

        Waiting on the success line alone is what makes a busy port look like a hang: the
        plugin logs its failure and the server carries on without a bridge, perfectly
        healthy from outside, so the caller waits the whole timeout and is then told only
        that a pattern never appeared. Watching for both outcomes turns two minutes of
        silence into one line naming the port and the reason.
        """
        line = self.wait_for(
            rf"listening on 127\.0\.0\.1:{port}|BRIDGE FAILED", timeout=timeout
        )
        if "BRIDGE FAILED" in line:
            raise RuntimeError(line.strip())
        return line

    def wait_for(self, pattern: str, timeout: float = 30.0, since: int = 0) -> str:
        """Block until an output line matches, and return that line.

        Searches the whole history by default, which is what start-up detection needs.
        For anything issued more than once in a session, use `command` instead: a bare
        `wait_for` will happily return a stale line from an earlier invocation.
        """
        deadline = time.monotonic() + timeout
        compiled = re.compile(pattern)
        seen = since
        while time.monotonic() < deadline:
            current = self.lines()
            for line in current[seen:]:
                if compiled.search(line):
                    return line
            seen = len(current)
            if self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(
                    f"server exited with code {self._proc.returncode}\n" + self._tail()
                )
            time.sleep(0.05)
        raise TimeoutError(f"no line matched {pattern!r} within {timeout}s\n" + self._tail())

    def _tail(self, count: int = 40) -> str:
        return "\n".join(self.lines()[-count:])

    def __exit__(self, *exc_info: object) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.poll() is None:
                self.send("exit")
                self._proc.wait(timeout=20)
        except Exception:
            pass
        finally:
            if self._proc.poll() is None:
                self._proc.kill()
                self._proc.wait(timeout=10)
            # The launcher can exit on "exit" or be killed above while the JVM it started
            # is still running; ending the job ends that too.
            self._job.kill()


def install_plugin(server_dir: Path, jar: Path) -> Path:
    """Copy a built plugin jar into the server mod directory."""
    mods = Path(server_dir) / "config" / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    target = mods / Path(jar).name
    shutil.copy2(jar, target)
    return target
