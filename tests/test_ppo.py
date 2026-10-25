"""Resuming a run, and what happens to a checkpoint when the observation changes shape."""

from __future__ import annotations

from gamma import ppo

def test_resuming_keeps_what_still_fits_when_the_observation_grows(tmp_path):
    """A strict load refuses the whole checkpoint over one widened row.

    Adding a global feature widens one weight matrix by a column, and refusing on that
    throws away every generation the run had rather than the column that changed.
    """
    import torch

    narrow = torch.nn.Linear(4, 3)
    torch.nn.init.constant_(narrow.weight, 1.5)
    torch.save({"net": narrow.state_dict(), "updates": 42}, tmp_path / "beta.pt")

    wide = torch.nn.Linear(6, 3)
    torch.nn.init.constant_(wide.weight, 0.0)

    class Stub:
        def __init__(self, net):
            self.net = net
            self.config = type("C", (), {"device": "cpu"})()
            self.updates = 0
        load = ppo.PPO.load

    agent = Stub(wide)
    agent.load(tmp_path / "beta.pt")

    assert agent.updates == 42, "the run resumes where it was"
    assert torch.allclose(wide.weight[:, :4], torch.full((3, 4), 1.5)), (
        "what was learned about the old inputs is kept")
    assert torch.allclose(wide.weight[:, 4:], torch.zeros((3, 2))), (
        "and the new ones start at nothing rather than at noise")


def test_a_checkpoint_saved_now_says_how_its_input_is_scaled_and_an_old_one_is_upgraded(tmp_path):
    import torch

    from gamma.net import INPUT_FORMAT, PolicyNet

    class Stub:
        def __init__(self, net):
            self.net = net
            self.config = type("C", (), {"device": "cpu"})()
            self.updates = 0
        load = ppo.PPO.load
        save = ppo.PPO.save

    make = lambda: PolicyNet(channels=14, window=48, globals_size=12, n_types=6, n_blocks=6)
    source = Stub(make())
    source.save(tmp_path / "now.pt")
    assert torch.load(tmp_path / "now.pt")["input_format"] == INPUT_FORMAT

    torch.save({"net": source.net.state_dict(), "updates": 7}, tmp_path / "old.pt")
    resumed = Stub(make())
    resumed.load(tmp_path / "old.pt")
    before = source.net.state_dict()["trunk.0.weight"]
    after = resumed.net.state_dict()["trunk.0.weight"]
    assert torch.allclose(after[:, 0], before[:, 0] / 255), "a flag channel, rescaled"
    assert torch.equal(after[:, 5], before[:, 5]), "the health channel, untouched"
