<div align="center">

# mindustry-ai

**Teaching machines to play [Mindustry](https://github.com/Anuken/Mindustry).**

An open reinforcement learning environment for the automation tower-defense RTS,
plus the agents that learn to survive, build and win in it.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-early%20development-orange.svg)](#roadmap)
[![Mindustry](https://img.shields.io/badge/Mindustry-v8-orange.svg)](https://github.com/Anuken/Mindustry)

</div>

---

> [!NOTE]
> **本專案改自 [yamakajump/mindustry-ai](https://github.com/yamakajump/mindustry-ai)**，
> 原作者為 yamakajump，依 [GPL-3.0](LICENSE) 授權使用與修改，本專案同樣以 GPL-3.0 釋出。
> 下方「目前專案目標與 GZ_capture 設定」及「修改紀錄」由本專案補充；後續英文內容保留原作者的研究背景與歷史紀錄，不代表本專案目前已達成的成果。

## 目前專案目標與 GZ_capture 設定

**目前目標：訓練 Beta 通過 Mindustry 戰役第一關 Ground Zero，使用任務 `GZ_capture`。**
`T1_copper` 等任務作為基礎能力實驗；目前的主要成功指標是 `GZ_capture` 的過關率，而非只提高採礦量或總獎勵。以下依目前程式設定整理。

### 任務與過關條件

| 設定 | 目前值 |
|---|---|
| 任務名稱 | `GZ_capture` |
| 世界 | 戰役區域 `groundZero`（Ground Zero），不是 `Ancient_Caldera` |
| 起始核心資源 | 銅 300、鉛 300 |
| 成功條件 | 觀察中的 `wave > 10`；程式不是以「擊殺第 10 波最後一個敵人」直接判斷 |
| 失敗條件 | 使用 Task 預設的 `game_over == true` |
| 回合上限 | 4,000 次決策；未成功或失敗時，到上限以 truncated 結束 |
| 每次決策 | 推進 30 個遊戲 tick；不是 30 秒，也不是一個完整建造流程 |
| 成功獎勵 | 額外 +50，並結束回合 |

遊戲回合重置不會讓模型重新初始化。訓練的總步數 `--steps` 與上述單回合上限是不同設定。

### Reward：每一步如何計分

`gamma/tasks.py` 的 `_survive_and_defend()` 定義：

```text
每步 reward = (下一步 wave − 目前 wave)
            − 0.003 × max(0, 目前核心血量 − 下一步核心血量)
            + 0.002 × (核心銅庫存變化 + 核心鉛庫存變化)

若下一步 wave > 10，再加成功獎勵 50。
```

| 事件 | 分數影響 |
|---|---|
| 波次增加 1 | +1；波次計時器會自行推進，並非每殺一波敵人直接加分 |
| 核心失去 100 點血量 | −0.3；回血不會由這一項得到正分 |
| 核心增加 100 銅或鉛 | +0.2 |
| 建造或供彈等用途消耗 100 銅或鉛 | −0.2；以這一步的庫存淨變化計算 |
| 滿足成功條件 | 額外 +50 |

**此任務沒有直接給鑽頭放置、鑽頭挖出、擊殺、里程碑或拆除獎懲。** 這些行為只能透過資源、血量、波次與成功條件間接影響分數。機器送貨和手動送貨也不分開計分，均反映於核心庫存；同一步收入與花費會互相抵銷。核心毀滅沒有獨立的固定扣分，但失血仍會扣分，遊戲結束會終止回合。

### Action：AI 可以做什麼

以下以 `tools/train_beta.py` 預設的 embodied 模式為準：AI 操作一個遊戲單位，建造受距離、資源和遊戲規則限制。動作表示為 `(type, block, x, y, rotation)`，不是每個動作都使用全部欄位。

| 動作類型 | 行為 | 主要參數／限制 |
|---|---|---|
| `noop` | 不下新指令，讓遊戲繼續推進 | 不代表清除既有移動、採礦或建造指令 |
| `move` | 朝指定位置移動 | `x, y`；一個 step 不保證到達 |
| `build` | 將單棟建築加入建造佇列 | `block, x, y, rotation`；單位在範圍內才能施工 |
| `mine` | 指定手動採礦格 | `x, y`；依單位採礦等級與距離執行 |
| `unload` | 請單位回核心交付攜帶物品 | 不使用目標座標；需要移動與交付時間 |
| `break` | 排入拆除自己的建築 | `x, y`；embodied 模式送出 `demolish` 指令 |
| `drill` | 在指定位置排入一顆機械鑽頭 | `x, y` 是 2×2 左下角；須有可挖礦、地形可建造且可負擔 |
| `link` | 將指定的未接線鑽頭以輸送帶接向核心或既有運輸網 | `x, y` 指向鑽頭；自動計算路線，檢查銅與佇列已承諾成本 |
| `stamp`（有載入設計庫時） | 依選定預製設計與目標位置執行布局放置 | `block` 欄位用作設計索引；受地形、路線、資源與施工限制 |

預設有 8 種基本動作，訓練與評估目前均預設不載入設計庫。明確指定 `--designs docs/designs.json` 並成功載入後增加 `stamp`，共 9 種；訓練和評估必須使用相同設計庫設定。舊的 `connect` 不是目前預設動作清單。`--direct` 則改用直接編輯世界的動作模式，不等同上述操作單位的條件。

預設建築目錄為 `conveyor`、`junction`、`router`、`mechanical-drill`、`copper-wall`、`duo`。目前採礦動作啟用時，`build` 不能選機械鑽頭，必須使用 `drill`。AI 沒有獨立的射擊、指定攻擊目標或裝填砲塔動作；防守需透過建築、運輸及遊戲機制實現。

`info["action_mask"]` 提供動作、建築與位置的合法性提示；位置分成 `free`、`owned`、`mineable`、`any`、`drillable`、`unlinked` 六組，依動作使用。遮罩不保證所有組合都能執行，最終仍可能因距離、路線或資源等因素遭拒絕。指令被接受也不代表建築已完工。

### State：模型實際接收的觀察

模型的 observation 是 `{"spatial": ..., "global": ...}`，另使用 action mask 限制選擇。以下是訓練入口的預設設定，不等於引擎回傳的全部原始資料。

**局部地圖 `spatial`：預設形狀為 `(14, 48, 48)`。** 視窗跟隨單位，沒有單位時以核心為中心；靠地圖邊界會調整視窗位置。動作的 `x, y` 是視窗內的格子座標，再由環境轉為世界座標。

| 通道 | 資訊 |
|---|---|
| `solid` | 地形或方塊是否為實心障礙 |
| `buildable` | 地板是否允許建造，不代表該格目前為空 |
| `block` | 是否存在建築；不直接編碼建築種類 |
| `block_ally`、`block_enemy` | 建築是否屬於己方／非己方 |
| `block_health` | 建築血量比例，以 0～255 編碼，進網路時除以 255 |
| `unit_ally`、`unit_enemy` | 該格己方／敵方單位數量 |
| `ore_<礦名>` | 該格是否有指定礦物 |

引擎先提供 8 個基本通道，再依當張地圖的礦物、按 item id 排序追加礦物通道；不是固定六種礦物。`LocalWindow` 依預設 `--channels 14` 補零或截斷到 14 通道。其他旗標不再一律除以 255，單位通道保留數量。因此 14 是輸入通道數設定，不代表地圖一定包含 6 種礦物。

**全域數值 `global`：17 個 float32，依下列順序與除數正規化。** 除以尺度不代表會截斷到 0～1。

| 欄位 | 意思 | 輸入模型前除以 |
|---|---|---:|
| `tick` | 遊戲 tick | 10,000 |
| `wave` | 波次計數 | 20 |
| `wave_time` | 下一波的倒數 tick | 3,600 |
| `enemies` | 敵人數量 | 20 |
| `core_health` | 核心血量 | 4,000 |
| `copper`、`lead`、`coal`、`sand` | 核心四種物品庫存，各一個欄位 | 各 1,000 |
| `carrying` | 單位攜帶物品數量，未編碼物品種類 | 30 |
| `unit_x`、`unit_y` | 單位的世界格子座標 | 各 256 |
| `core_dx`、`core_dy` | 核心位置減單位位置的位移 | 各 256 |
| `plans` | 單位建造／拆除佇列長度 | 50 |
| `plan_dx`、`plan_dy` | 單位到最近佇列藍圖的位移；空佇列為 0 | 各 256 |

**原始資料 `info["raw"]` 與模型輸入不同。** 原始資料還包含 `produced`（機器送入）、`hand_delivered`（手動送入）、鑽頭資料、詳細建造佇列與遊戲結束旗標等，供獎勵、評估和紀錄使用；不能因原始資料有某欄位，就認為目前策略網路也看得到。模型目前沒有直接接收機器／手動累積送入量、攜帶物品種類、砲塔彈藥或完整藍圖清單。

### 訓練與評估指令

在專案根目錄的 PowerShell 執行。以下使用獨立輸出目錄保存 GZ 模型，避免接續或覆寫 T1 的 `checkpoints/beta.pt`：

```powershell
.\.venv\Scripts\python.exe -m tools.train_beta --task GZ_capture --envs 1 --steps 100000 --out checkpoints/GZ_capture
```

會自動開啟儀表板 `http://127.0.0.1:8800`，預設另啟一個慢速展示環境；不需要展示環境時加 `--no-watch`。若 GZ 輸出目錄已有 `beta.pt`，預設接續該模型；加 `--fresh` 才從新模型開始，但仍會向同一輸出目錄寫入結果。

```powershell
.\.venv\Scripts\python.exe -m tools.evaluate checkpoints/GZ_capture/beta.pt --task GZ_capture --episodes 5 --no-random --max-steps 4000 --items copper,lead --out docs/measurements/GZ_capture.json
```

評估時明確設 `--max-steps 4000`，避免評估工具預設的 1,500 步先停止回合。主要查看成功率 `solved / episodes`，再看波次、核心存活與資源運輸表現。Ground Zero 是指定戰役區域，評估報告的 `held_out` 標記不代表已驗證跨不同生成世界的泛化能力。

設定來源：`gamma/tasks.py`（任務與獎勵）、`gamma/env.py`（動作與 global）、`gamma/window.py`（局部視窗）、`gamma/net.py`（輸入尺度）、`bridge/src/mindustryai/net/ObservationEncoder.java`（地圖通道）。

### 基礎任務：T1、T2、T4

這些任務用於檢查採礦、資源管理與生存能力；主要目標仍是通過 `GZ_capture`。以下依目前 `gamma/tasks.py` 設定整理，各任務的 reward 獨立，不會自動繼承，也不會自動依序升級。

| 任務 | 成功條件 | 每回合步數上限 | 成功額外獎勵 |
|---|---|---:|---:|
| `T1_copper` | 核心當下銅庫存 ≥ 250 | 450 | +10 |
| `T1_copper_income` | 本局送入核心的銅累計 ≥ 200 | 450 | +10 |
| `T2_two_ores` | 核心當下銅庫存 ≥ 250，且鉛庫存 ≥ 120 | 450 | +10 |
| `T2_copper_lead_income` | 本局送入核心的銅、鉛累計各 ≥ 200 | 450 | +10 |
| `T4_survive` | 波次計數 `wave > 5` | 3,000 | +10 |

以上皆使用 `Ancient_Caldera` 地圖，每次決策推進 30 個遊戲 tick。成功或遊戲結束可提前終止回合；未成功或失敗時，到步數上限以 truncated 結束。指定同一張地圖不等於固定所有礦藏配置，重現實驗時需另外控制世界種子。目前沒有名為 T3 的註冊任務。

#### T1_copper：採銅與鑽頭運作

每一步將下列 reward 相加；成功再加 +10：

| 項目 | 計分方式 |
|---|---|
| 單位攜帶物品數量增加 | 每個 +0.001，不限定礦種；攜帶量下降不扣分 |
| 新鑽頭覆蓋銅礦格 | 每格 +0.25 |
| 新鑽頭覆蓋鉛礦格 | 每格 +0.05 |
| 拆除自己的建築 | 每棟 −0.1 |
| 蓋完立即拆除（churn） | 每次額外 −2，可與拆除扣分疊加 |
| 每顆鑽頭挖出的第 1～5 個銅 | 每個 +0.1 |
| 每顆鑽頭挖出的第 6～10 個銅 | 每個 +0.15 |
| 每顆鑽頭挖出的第 11 個銅起 | 每個 +0.3 |

分級採礦獎勵以每顆鑽頭各自的累積挖出量計算，不是所有鑽頭共用門檻。**目前 T1 沒有直接的核心庫存變化或機器送貨獎勵**；挖出銅不等於已送回核心，得到正分也不代表達成銅庫存 250 的成功條件。

#### T1_copper_income：累計送入 200 銅

reward 的項目與係數和上面的 T1_copper 表格相同，差別在成功條件。累計量是本局的 `produced`（機器送入）加 `hand_delivered`（手動送入）：開局庫存不算，花掉也不扣回，所以邊送邊蓋不會讓進度倒退。

#### T2_two_ores：同時累積銅與鉛

```text
每步 reward = 0.01 × (下一步核心銅庫存 − 目前核心銅庫存)
            + 0.02 × (下一步核心鉛庫存 − 目前核心鉛庫存)
```

銅庫存每淨增加 1 得 +0.01，鉛每淨增加 1 得 +0.02；淨消耗則按相同係數扣分。同一步的收入與支出會抵銷，手動與機器送貨不分開計分。兩種庫存必須同時達標，成功再加 +10。此任務沒有 T1 的攜帶量、鑽頭放置、分級採礦或拆除獎懲。

#### T2_copper_lead_income：累計送入 200 銅與 200 鉛

累計方式與 T1_copper_income 相同，銅、鉛必須各自達標。reward 也和 T1_copper 表格相同，因此分級採礦獎勵只算銅，鉛只有新鑽頭覆蓋礦格的每格 +0.05。

#### T4_survive：生存五波

```text
每步 reward = 下一步 wave − 目前 wave
```

波次每增加 1 得 +1，`wave > 5` 時成功並額外 +10。此任務沒有直接的資源、建造、擊殺、核心受傷或核心毀滅固定獎懲；遊戲結束仍會終止回合。波次由遊戲計時與規則推進，不能將 +1 直接解讀為 AI 剛消滅一整波敵人。

選擇任務時使用 `--task` 加上表格中的任務名稱，例如 `--task T1_copper_income`。比較不同 reward 的訓練結果應看成功率與任務指標，不能直接用總分高低判定哪個模型較好。

### GroundZero紀錄
#### 目標
1. 取得15銅(手動)
2. 建造1個機械鑽頭
3. 從鑽頭移入5銅到核心 (或許可以從鑽頭速度加分)
4. 從鑽頭移入100銅到核心
5. 從鑽頭移入100鉛到核心
6. 建造兩個雙炮
7. 為雙炮補彈藥
8. 建造6個銅牆
9. 分散炮

#### 建造花費
1. 機械鑽頭：12銅
2. 輸送帶：1銅
3. 雙炮：35銅 (彈藥填補可以加分？)
4. 分配器：3個銅 (要怎麼讓他做到什麼時候該放分配器？？)
5. 銅牆：6銅 (怎麼圍起來)
6. 分散炮：85銅、45鉛

#### 其他紀錄
1. 1個step大約0.5秒
2. 第一波約在第480step出現(4min)

#### task
Task1： 採 100 銅
Task2： 採 100 銅 + 採 100 鉛

### 修改紀錄

**2026-10-22**

- `bridge/.../StepLoop.java`：observation 新增 `drilled`（以鑽頭 progress 下降偵測每次挖出）與 `drill_tiles`（新鑽頭覆蓋的礦格數）。
- `gamma/tasks.py`：新增 reward 項 `_drilled`、`_drill_tiles`、`_torn`、`_churn`，並調整 T1_copper 的 reward。
- `bridge/.../SceneEncoder.java`：建築改由地圖格子掃描取得，不再依賴 `Groups.build`，修正回放與 dashboard 中閒置建築被誤報為移除又重建的問題。
- `gamma/monitor.py`、`gamma/playback.py`、`viewer/dashboard.html`：回放大畫面新增獨立的暫停、時間軸與速度控制，不影響進行中的訓練；回放播完停在最後一格，可拖回重看。
- `tools/watch.py`：`--wait` 預設值由 300 秒改為 10 秒。
- 新增 `debug/`：實驗用的除錯與診斷腳本。
- 新增 `lab_record.md`：實驗紀錄。
- `.gitignore` 新增 `server-*/`；移除 `.github/workflows/pages.yml`。

**2026-10-23**

- `gamma/env.py`：connect 的 A* 繞開不可建造的格子（深水）。
- `bridge/.../StepLoop.java`：observation 新增 `connected_drill_tiles`（挖出量超過自身緩衝的鑽頭所覆蓋的礦格數）與 `drill_mined`（每個現存鑽頭本局挖出量，以 building id 為 key）；重置時一併清除所有鑽頭追蹤資料。
- `gamma/tasks.py`：新增 `_produced_gain`、`_connected_drill_tiles` 與讀取函式 `_drill_mined`、`_drill_mined_steps`。
- `bridge/.../StepLoop.java`：observation 新增 `hand_delivered`（unit 親手交給核心的礦，逐 tick 計算；引擎的 `produced` 只計運輸方塊送入）。
- `tools/evaluate.py`：可同時評估兩個 checkpoint 並互相比較；新增 `--items`、`--settle`、`--running-window`，依礦種回報機器／手動送入量、手挖比例、鑽頭數、接通率與運轉率（新增 `tests/test_evaluate.py`）。

**2026-10-25**

- `gamma/env.py`：connect 改為在 agent 指定的格子蓋一顆鑽頭（2×2 的左下角），不再由 `mining.pack` 依 `ORE_VALUE` 在 24×24 範圍內挑選；傳送帶從鑽頭四周 8 格中最近的一格出發。新增位置遮罩 `drillable`（整個 2×2 可建造且至少一格有機械鑽頭挖得動的礦），connect 改用此遮罩，`POSITION_SETS` 由 4 個變為 5 個。
- `tools/train_beta.py`：遮罩平面數改依 `POSITION_SETS` 的長度。
- `gamma/env.py`：`connect` 拆成兩個動作類型。`drill` 在 `drillable` 遮罩的位置放一顆機械鑽頭；`link` 從自己尚未接線的鑽頭拉傳送帶到核心或既有網路（新增遮罩 `unlinked`，`POSITION_SETS` 變為 6 個）。
- `gamma/env.py`：`link` 先算出整條線要幾格，核心的銅不夠付整條線（每格 `BELT_COPPER` = 1）就拒絕，理由 `can't afford`，不排任何計畫。原本只要有 1 銅就能下 link，整條線排進佇列後蓋到沒銅就停住。
`place`／`build` 不能再放機械鑽頭。動作類型由 7 個變為 8 個，舊 checkpoint 無法再載入。
- `bridge/.../StepLoop.java`：observation 新增 `drills`（自己蓋好的鑽頭 `[x, y, linked]`，linked 表示旁邊有運輸方塊或核心）。
- `gamma/replay.py`、`gamma/journal.py`：記錄 `drill` 與 `link` 動作。
- `bridge/.../StepLoop.java`、`gamma/bridge.py`：新增指令 `ground`，回傳整張地圖每格的可通行旗標（不可建造地形、建築、自己的運輸方塊或核心、自己的建築）。`gamma/env.py` 的 `_ground()` 改用它，不再只看 48×48 的觀察視窗、把視窗外當成空地，修正傳送帶在視窗外跨越深水與岩石；路線只穿過自己的運輸方塊與核心，不再穿過自己的鑽頭與牆。
- `tools/train_beta.py`、`tools/evaluate.py`：新增`--seed` 可給逗號分隔的清單（`--seed 1,10000,42`）。訓練時每局從清單隨機抽一個（`Task.world_seeds`，各 env 依自己的 port 抽，不會同步），不加時沿用任務本身的設定。；evaluate 依序輪流（第 i 局用第 i mod n 個），每個 policy 跑同一組種子，並逐種子列出 reward、成功數與每種礦的機器送入量和鑽頭數。journal 每局多記 `world_seed`。新增 `tests/test_seeds.py`。
- 新增 `tools/scan_seeds.py`：列出每個種子在核心周圍 12／24／40／60 格內的礦格數與可蓋全礦 2×2 鑽頭的位置數，用來挑訓練與測試種子（`python -m tools.scan_seeds 1-100`）。
- `gamma/net.py`：修正地圖輸入的尺度。原本 14 個通道一律除以 255，但除了 `block_health`（0～255）以外都只存 0／1，進網路時只剩 0.0039，比 global 弱 255 倍，礦物位置幾乎影響不了決策。現在只有 `block_health` 除以 255，其他通道維持 0／1。checkpoint 新增 `input_format` 欄位；載入舊 checkpoint（`ppo.load`、`tools/evaluate.py`）時，第一層卷積在旗標通道上的權重會一起除以 255，輸出和原本相同，可以直接接續訓練。`tools/sanity_ppo.py` 的合成觀察改用 0／1。
- `bridge/.../StepLoop.java`：observation 的 `unit` 新增 `plan_queue`，依佇列順序列出每個藍圖的 `[x, y, 方塊, 尚需銅量, 是否拆除]`；尚需銅量 = 需求 × `buildCostMultiplier` × (1 − 進度)。原本只回傳佇列長度 `plans`。
- `gamma/env.py`：global 從 14 個變成 17 個，新增 `plans`（佇列長度）以及 `plan_dx`、`plan_dy`（unit 到佇列中最近一個藍圖的位移，佇列為空時是 0），全部直接讀自遊戲的佇列。原本觀察裡完全看不到藍圖：exp15 共 23 局，`link` 排的 2755 格中有 583 格沒蓋起來，其中 204 格在下令之後從未進入 unit 的建造範圍（約 28 格）。
- `gamma/env.py`：`link` 與 `drill` 判斷付不付得起時，先扣掉佇列裡尚需的銅（不論是誰排的，手動 `build` 也算）。原本每條線各自和核心目前的銅比較，連續幾步下的線全都會通過。`drill` 付不起時拒絕，理由 `can't afford`。
- `gamma/ppo.py`：載入邏輯抽成 `load_weights`，`tools/evaluate.py` 也改用它，所以舊 checkpoint 在 global 變寬之後仍能評估。加寬時新增的欄位改為 0（原本保留新網路的隨機初始值，和說明不符），接續訓練時行為不變。新增 `tests/test_plans.py`。
- `tools/evaluate.py`：預設不再和 random policy 比較。random 沒有找礦的能力，在這些地圖上幾乎挖不到礦，分數沒有參考價值。要比較時加 `--random`（`--no-random` 仍可用，等同預設）。

**2026-10-26**
- `tools/train_beta.py`：增加`--port`預設為8800。`--watch`預設改為關閉，`--designs` 預設改為不載入，`--save-every`預設改為100 gen 存一次，`--out`預設改到 checkpoints/scratch。
- 新增 `tools/watch_beta.py`：在和訓練相同的 dashboard 上觀看一個 checkpoint 執行，不訓練，不寫入pt、journal。`--port`預設為8810，其他參數與train_beta維持一致。
- `tools/evaluate.py`：有給 `--seed` 時，`--episodes` 改為每個種子的局數（種子依序輪流，總局數 = episodes × 種子數）；沒給 `--seed` 時仍是總局數，每局隨機種子。各種子的結果改成對齊的表格。
- 新增 `tools/watch.py`：取代 `watch_beta` 與 `train_watch`，在 dashboard 上同時觀看多種策略，不訓練。`--policy` 必填，逗號分隔，可混合 checkpoint（`.pt`）與內建策略（`alpha`、`masked-random`、`random`）；`--matches` 為每種策略各開幾場（預設 1），速度預設為最高速（`--speed max`，要看清楚可用 `--speed 2`），其他預設與 `watch_beta` 相同；卡片上的 Join in Mindustry 位址預設不顯示，加 `--join` 才顯示。所有對局每一局用同一張地圖：有 `--seed` 時依序輪流（第 i 局用第 i mod n 個），沒有時每局隨機抽一個種子、各對局共用；先跑完的對局會等其他對局都跑完這一局才開始下一局，`--no-sync` 可關閉。原本的 `tools/watch.py`（在 Mindustry 客戶端裡播錄影）改名為 `tools/watch_client.py`。

- `tools/watch.py`：dashboard 的 pause 鍵可以暫停觀看用的對局（`train_beta --watch` 的那場也是）；stop 鍵在 `watch` 裡改為 leave，直接結束、不再警告會存檔。
- `gamma/monitor.py`：從 dashboard 點開的錄影（第 9000 號）不再算進 leaderboard 與頂端統計；只有錄影時（`watch_replay`）照常計入。
- `viewer/dashboard.html`：縮圖改用隊伍色，我方黃、敵方紅；單位畫圈，建築依實際佔地畫成方形，施工中半透明。說明欄改為四行；刪除對局上方的說明段落與右上角的錄影進度條（`watch_replay` 改為自動打開錄影）。頂端欄改為 task、solved（成功／完成局數）、generation（真正的世代編號）、steps（訓練步數／`--steps`）、steps/s、elapsed。

- bridge `mine()`：格子上有東西（例如 sand-boulder）時拒絕挖礦，理由為 `something stands on the ore: <方塊>`。原本會回報成功，但引擎每一幀都清掉挖礦目標，實際上什麼都沒挖到。
- `tools/watch.py`：內建策略（`alpha`、`masked-random`、`random`）改為收到整張地圖。原本每場對局都向 bridge 要 checkpoint 用的 48×48 視窗，內建策略把視窗座標當成整張地圖的座標，alpha 會飛到地圖角落、什麼都挖不到。現在只有 checkpoint 要視窗。

**2026-11-04**

- `gamma/tasks.py`：新增任務 `T1_copper_income`（450 步內送入核心的銅累計 ≥ 200）與 `T2_copper_lead_income`（銅、鉛各 ≥ 200），並加入 `CURRICULUM`，兩者 reward 相同。新增判定函式 `_income`，計算本局的 `produced` + `hand_delivered`：開局庫存不算，花掉也不扣回。
- `lab_record.md` 改名為 `t1_copper_record.md`；新增 `t1_copper_income_record.md`：T1_copper_income 的實驗紀錄。
- `tools/evaluate.py`：`--out` 預設由 `checkpoints/scratch` 改為 `checkpoints/scratch/evaluate.json`。原本預設值是資料夾，評估跑完寫檔時會 `PermissionError`，結果 JSON 存不下來。
- `tools/train_beta.py`：`--envs` 預設由 6 改為 4。
- `gamma/archive.py`：每場對局新增保留最近 30 局失敗（`keep_failed`，預設 30）。原本只留最佳、最近與成功的局，任務變得可以過關之後失敗局幾乎被刪光：exp15 的 111 局失敗只留下 3 局。
- `gamma/replay.py`：錄影 header 新增 `world_seed`。同一張地圖的各局只差在礦藏配置，原本要比對 overlay 才分得出是哪個種子。
- `gamma/env.py`：`CONNECT_BUDGET` 由 60 改為 256，`link` 與 `stamp` 共用。Ancient_Caldera 是 256×256，60 格拒絕了大部分請求：55 局共 1,370 次 `link` 有 417 次 `too far`、只有 326 次成功。太長的線現在由銅與建造時間自行付出代價，不在這裡拒絕。`tests/test_library.py` 的上限改為 `< 405`。
- `t1_copper_income_record.md`：新增第二次測試（exp15，`CONNECT_BUDGET` 256）。

### 整理 

---

> [!WARNING]
> **Early development. No agent plays the game yet.**
> This README describes what the project is for and reports honestly on where it
> actually stands. Every claim about agent performance in this file is backed by a
> reproducible run, or it is not in this file. See the [roadmap](#roadmap).

## Why Mindustry

[Mindustry](https://github.com/Anuken/Mindustry) is a real-time strategy game where you
mine resources, route them through conveyor networks, refine them into higher tier
materials, and spend the output on turrets and units. Then waves of enemies come to
take it apart.

That makes it an unusually good testbed for machine learning, because winning requires
three skills that rarely appear together in one game:

- **Long-horizon economics.** A silicon smelter pays for itself in ten minutes, not now.
  An agent that only optimises the next second never builds one.
- **Spatial reasoning.** Conveyor layouts, turret coverage and factory footprints are
  geometry problems on a grid, not a list of build orders.
- **Reactive combat.** All of the above has to survive contact with an enemy that
  actively destroys it.

Factorio has [a learning environment](https://arxiv.org/abs/2503.09617). StarCraft II has
[pysc2](https://github.com/google-deepmind/pysc2). Mindustry has nothing. This project is
that missing piece.

## What makes it hard

Being honest about the difficulty up front, because it shapes every design decision here.

| Obstacle | Why it hurts |
|---|---|
| **Enormous action space** | Roughly 200 block types, on maps up to 500x500 tiles, times rotation and configuration, plus per-unit commands. Wider than StarCraft II. |
| **Slow simulation** | Mindustry simulates thousands of blocks and item movements per tick, and cost grows with the factory. Less of a problem than expected: [measured](docs/measurements/throughput.md) at 592x realtime per instance on an empty map. |
| **No thread safety** | The engine is single threaded by design. Parallelism means many JVM processes, not many threads. |
| **Sparse, delayed reward** | The payoff for a good factory arrives minutes after the decisions that built it. |
| **Nothing was built for this** | No observation API, no fast reset, no metrics. That plumbing is most of the work. |

## How it works

Three processes, split by language boundary. A JVM mod inside the Mindustry headless
server exposes state and executes actions. A Python package holds the Gymnasium
environment and the training loop. A static web viewer replays matches.

The design choice that matters most: **the agent can perform every action a human player
can**, with no hand-written vocabulary capping what it is allowed to try. That space is
made learnable by factoring one action into dependent components with their own network
heads, and by masking every head to legal choices computed by the engine itself. Scripted
macros exist, but as one action among many rather than as the whole repertoire, so nothing
stops the agent from ignoring them and inventing something better.

Full details in [`docs/architecture.md`](docs/architecture.md). The reasoning behind each
choice, including the alternatives that were rejected, is in
[`docs/decisions/`](docs/decisions/).

## A different world every episode

The thing that decides whether this project works is not the reward and not the network. It
is how many maps the agent sees.

An agent trained on one map learns that map. This is measured rather than suspected:
[CoinRun](https://arxiv.org/abs/1812.02341) and
[Procgen](https://arxiv.org/abs/1912.01588) both show that a fixed set of levels gets
memorised, and that generalisation only appears once the training set runs into the
hundreds. And the failure is invisible from inside, because a reward curve rising on the
maps you trained on is exactly what memorisation looks like.

Mindustry hands over the fix. Serpulo is a planet of 272 sectors, 194 of them generated by
the game's own planet generator. Every episode draws a different one: its own terrain, its
own ore, its own size. Capping on the game's own threat estimate leaves 147 worlds to train
across, which is on the right side of where Procgen sees generalisation begin.

**A fifth of them are held back and never trained on.**

```bash
python tools/evaluate.py checkpoints/beta-best.pt
```

That scores a checkpoint on worlds it has never seen (add `--random` to score a masked
random floor beside it). It is
the only measurement here that can tell learning from memorising, and it is the number
worth quoting. See [decision 12](docs/decisions/0012-train-on-many-worlds.md).

### What the agent is graded on

The agent has to work out for itself that a drill mines, that a drill needs ore under it,
that ore has to reach the core. Nothing tells it. The trick is to grade it on something
that happens to rise faster once it has figured that out.

It is graded on a **ladder of firsts**. A first drill. A first conveyor. The first ore a
machine delivered without a hand carrying it, which is worth six times the drill. A
hundred of it, a thousand, ten thousand. A first turret, a first kill, a first generator,
a first crafter. Each rung is paid **once per episode and never again**, because each one
reads a counter that only climbs, so the ladder cannot be farmed by building and breaking
the same conveyor.

On top of the ladder, one number paid per unit: **ore a machine delivered to the core.**
The engine draws that line itself. A conveyor hands items over through `handleItem` and
the game counts it; a unit banking a stack goes through `handleStack` and it does not. So
automation is separated from hand mining by Mindustry rather than by anything invented
here, and hand mining pays a tenth as much, which means carrying ore in is always the
worse way to earn the same reward.

This replaced a potential function that was provably safe and measurably inert: entropy
12.067 to 11.672 over eleven updates, policy loss 0.009. The shape it replaced it with is
not invented either. On [microRTS](https://arxiv.org/abs/2010.03956), the closest
published build-and-fight benchmark, a sparse agent scored **0.00 out of 10** on producing
combat units and an agent on plain additive event rewards scored **9.57**.
[Factorio](https://arxiv.org/abs/2503.09617) scores on the value of what is *produced*
rather than held. [Crafter](https://arxiv.org/abs/2109.06780) pays +1 the first time each
of its twenty-two achievements is unlocked in an episode and nothing afterwards. Same
shape, three times over. See
[decision 14](docs/decisions/0014-milestones-over-potential.md).

## Train, and watch it happen

```bash
python tools/train_beta.py --task frontier
```

That is the whole command. It clears servers a previous run left behind, builds the
bridge plugin if it is missing, starts the environments, opens the dashboard and trains
until stopped.

The dashboard on `127.0.0.1:8800` shows every match at once, **animated with the game's
own sprites**: the agent flying, mining and building, enemies arriving in waves,
construction hatched until it completes, damage flashing, buildings exploding, shots in
flight. Beside them, what the game itself never shows:

- **the learning curve**, mean reward per generation, raw and smoothed
- **saved versions**, one checkpoint every ten generations plus `beta-best.pt`, chosen on
  the average across a generation rather than on one lucky episode
- **replays** of the best episodes, one click to watch them back
- the objective, the leaderboard, and a legend for everything on screen

Each match is its own Mindustry process, because the engine is not thread safe. No
dependencies beyond the standard library: a dashboard that needs a web framework
installed is a dashboard that is not running when you want it.

Tasks, in the order they were built:

| Task | World | What it asks |
|---|---|---|
| `T1_copper`, `T2_two_ores`, `T4_survive` | one fixed map | the early curriculum, useful as a floor rather than a target |
| `GZ_capture` | Ground Zero | the campaign's own objective: survive to wave 10 |
| `endless` | one fixed map | survive and produce, no finishing line |
| **`frontier`** | **a new generated world every episode** | **land, build an economy, hold it** |
| `frontier_shaped` | the same worlds | the control: `frontier` graded the old way, so the reward change is measured rather than argued about |

One extra match is played alongside the run at a speed a person can follow, so there is
always something to join in the game. It is deliberately outside the training batch:
rollout collection is lockstep, so a slow environment inside it holds every other one at
its own pace, and one watchable match cost the whole run a factor of thirty in throughput
before this was noticed.

Useful flags: `--envs N`, `--worlds N` to narrow the training pool without touching the
held-out half, `--direct` to drop the body and train faster, `--watch` to add the
showcase match, `--record` to archive replays. To watch policies
without training: `python tools/watch.py --policy checkpoints/beta.pt,alpha`.

The dashboard drives the run: **pause** to look at something without losing the machine,
**stop & save** to bring it down cleanly. Stopping is not killing. The checkpoint is
written on the way out and the next run picks up from it, which is what `--fresh` is for
when you actually meant to start over.

Each saved version is listed with the share of its episodes that reached each rung, not
just its mean reward. A mean that rose because one episode got lucky looks identical to a
policy that got better; a rate does not.

Every match archives its best five episodes, its latest three, and every episode that
solved. To watch the best one of a run inside the real game:

```bash
python tools/watch_client.py         # best episode of the last run, in the Mindustry client
python tools/watch_client.py --list  # everything archived, best first
```

That one is a **re-simulation, not a recording**: the episode's world is loaded on a real
server, the agent's own moves, mining, banking and building are reissued in order, and you
join as a spectator. So you see what a player would have seen, waves and units and all,
rather than blocks appearing on an empty map.

The in-game reader is the other half. `python tools/install_mod.py` puts it in Mindustry
along with the replays, and the **AI replay** button in the main menu opens them without
anything else running. It rebuilds the world from the replay itself, which is why it works
on generated sectors that exist under no name.

### Or join it in the real game

Every environment is a real headless server with its game port open. The watched match
prints its address on startup:

```
Mindustry -> Play -> Join Game -> 127.0.0.1:6920
```

That is the engine rendering itself, so it is the best possible picture of one match. The
dashboard is the better picture of a training run. They are not substitutes.

## Watch it play

Two ways, and they are not equivalent.

### In the game, with a remote in your hand

```bash
python tools/install_mod.py
```

Restart Mindustry and press **AI replay** in the main menu. Pick an episode and watch it
play out with a transport bar: play and pause, 0.5x to 8x, step forward and back, scrub
anywhere on the timeline, jump to the core. Space and the arrow keys work too. You keep
full control of the camera the whole time, because it is your game running.

Everything the engine draws is there, conveyor animations, items sliding along them,
block connections, lighting, wave effects, because the game itself is rendering it.

Rewinding is the part worth explaining: a simulation cannot be run backwards. The mod
keeps a full snapshot of the world in memory every forty steps, in the engine's own save
format because that is the only thing that captures items in transit, units and wave
timers. Going back restores the nearest one and replays forward from it.

The installer finds your Mindustry on its own. The Steam build keeps its data inside its
install folder rather than in the usual application data path, which is an easy way to
end up staring at "no mods found".

### Live, over the network

```bash
python tools/watch_client.py replays/showcase/alpha-t1.jsonl.gz
```

Then **Play → Join Game → 127.0.0.1:6567**. No mod needed: the training server already
speaks Mindustry's network protocol, so a stock client can join it. Less control than the
mod, but this one also works **live during training**, not just on recordings.

### In a browser, for sharing

**[Alpha building a copper chain](https://yamakajump.github.io/mindustry-ai/?replay=replays/alpha-t1.jsonl.gz)**
 | [a random policy going bankrupt](https://yamakajump.github.io/mindustry-ai/?replay=replays/random-t1.jsonl.gz)

Drawn with the game's own sprites, pan and zoom, no install. Being honest about it: this
is a map, not the game. There are no animations, conveyors do not connect visually, and
there is no lighting. It exists so a replay can be shared as a link, which the real client
cannot do.

A full 450 step episode is about 16 KB, because only the typed map and the actions taken
are stored, not the state. The same format will carry live training over a WebSocket. See
[decision 3](docs/decisions/0003-one-replay-format.md).

## Where it stands

The first curriculum task is live, with a benchmark. `T1` asks an agent to grow the core's
copper stock to 250 within 450 decisions, which is the budget before the first wave lands.

**Direct mode**, where the agent edits the world without a body:

| Policy | Solved | Mean reward | Actions accepted |
|---|---|---|---|
| Random | 0/5 | -1.98 | 9% |
| Masked random | 0/5 | -2.00 | 11% |
| **Alpha** (scripted) | **2/5** | **+4.12** | **60%** |

**Embodied**, where it inhabits a unit and plays under a player's limits: it has to fly to
the ore, mine by hand, carry the load back, and can only build within about 27 tiles.

| Policy | Mean final copper | Mean reward |
|---|---|---|
| Masked random | 0 | -2.00 |
| **Embodied Alpha** | **192** | **-0.08** |

Acceptance rate stops being informative once there is a body: `move` is nearly always
legal, so a policy can be accepted 95% of the time while bankrupting itself.

Random policies do not merely score badly, they go bankrupt: they spend the starting
copper on blocks placed at random, build nothing that produces, and every later action is
refused for lack of funds. Masking gets more actions accepted and still scores no better,
because knowing which moves are legal is not knowing which are good. That gap is the part
that has to be learned.

Alpha solving two in five is the calibration working. A baseline that always won would
make the task useless as a target; one that never won would leave no evidence it is
solvable. Full numbers and method in [`docs/measurements/baselines.md`](docs/measurements/baselines.md).

## What stopped Beta, and what came of it

Beta has been trained. Roughly 1.3 million steps across 406 generations, on 147 generated
worlds, with a reward built around a ladder of first-time milestones. Scored on worlds it
had never trained on, twelve episodes each:

| policy | reward | delivered by machine | solved |
|---|---|---|---|
| `beta-best` | **-9.52** | 0.0 | 0/12 |
| masked random | **-9.25** | 0.0 | 0/12 |

It does not clear the random floor. That is the number this project reports, and it says
no.

The reason turned out to be structural rather than a matter of tuning, and it is worth
stating plainly because it cost a day to find. Value in this game lives in **connected
structures**, and every partial one is worth exactly nothing. Reading 177 archived episodes
with [`tools/analyse_replays.py`](tools/analyse_replays.py):

| | |
|---|---|
| drills placed | 4,481 |
| conveyors placed | 5,719 |
| episodes where the tiles ever met end to end, drill to core | **1** |

The count is bracketed by two readings, one honouring rotations and one ignoring them
entirely, and both give one. The arithmetic in
[`tools/analyse_game.py`](tools/analyse_game.py) says why: a ten-tile conveyor line is one
chance in a million **on rotations alone**, before choosing which ten of 2,304 tiles.
Expected complete lines per episode: 0.002. A policy choosing tiles one at a time is not
going to find that, and no amount of training time changes it.

So the structures are searched for rather than learned, and that search moved into its own
repository: **[mindustry-forge](https://github.com/yamakajump/mindustry-forge)**. It
evolves layouts, stamps each into a running game, and keeps the ones that deliver. What it
found from nothing but "get copper to the edge" was a vertical conveyor trunk fed by drills
on both sides. Put back on three worlds it had never seen, it beat the hand-written
baseline on all three while using half the blocks per unit delivered.

Those designs come back here as a single action, `stamp`, alongside every primitive the
policy already had. The guardrail for that is measured rather than argued: the same
structure placed at random tiles delivers **zero**, against about 195 when placed where the
ore is. The value is in the decision, which is what the policy is for, not in the structure.

## Milestones

Mindustry players do not have a fixed avatar. They embody a core unit that upgrades with
their core: **Alpha**, then **Beta**, then **Gamma**. The agents follow the same path,
because it maps cleanly onto how capable they actually are.

| Milestone | What it is | Status |
|---|---|---|
| **Alpha** | A scripted baseline. It plays, badly but predictably. The yardstick everything else is measured against. | **solves T1 two times in five** |
| **Beta** | The first agent that genuinely learns. Beats Alpha. | **trained, does not yet clear the random floor** |
| **Gamma** | An agent that beats competent human players. | the point of all this |

The name is a double meaning worth stating once: in Mindustry, Gamma is the final form of
the player's own avatar. In reinforcement learning, gamma is the discount factor, the term
in the Bellman equation that decides how much an agent values the future over the present.
Building a factory that pays off in ten minutes is exactly a high-gamma problem.

## Roadmap

Ordered by dependency, not by excitement.

- [x] **Bridge foundation.** A JVM plugin loaded by the headless server, driven from Python, with simulation speed under control.
- [x] **Throughput benchmark.** [Measured](docs/measurements/throughput.md): 592x realtime on one instance, 4,806x across 24.
- [x] **Bridge protocol.** A socket speaking length-prefixed frames, with the world frozen between decisions. [Measured](docs/measurements/throughput.md) at 2,247 decisions/s.
- [x] **Observations.** Spatial tensors on the binary frame type, 14 channels, plus scalars. [Measured](docs/measurements/throughput.md) at 481 steps/s with a 896 KB tensor.
- [x] **Actions.** Placing and breaking blocks, priced against the core, refused by the engine when illegal.
- [x] **Environment.** Gymnasium-compatible: factored action space, masks for every head, reward, curriculum tasks.
- [x] **Alpha.** The scripted baseline, and a [benchmark](docs/measurements/baselines.md) to score anything against it.
- [ ] **Beta.** First learned agent. Clears the early curriculum stages and beats Alpha on them. Trained; [does not yet clear the random floor](docs/decisions/0014-milestones-over-potential.md).
- [x] **Structures.** Searched for rather than learned, in [mindustry-forge](https://github.com/yamakajump/mindustry-forge), and handed back as one action. [Decision 15](docs/decisions/0015-search-for-structures-learn-where-to-put-them.md).
- [ ] **Replays.** An event log format, and a web viewer that replays a match tile by tile.
- [ ] **Full games.** Survival on real maps, the whole economy and defence loop.
- [x] **Generalisation.** A new generated world every episode, drawn from 147 of them, with a fifth held back to measure on. [Decision 12](docs/decisions/0012-train-on-many-worlds.md).
- [ ] **Level sampling.** [PLR](https://arxiv.org/abs/2010.03934) and [ACCEL](https://arxiv.org/abs/2203.01302): choose the world the agent has most to learn from, instead of drawing uniformly.
- [ ] **Self-play.** Attack and PvP modes, agents trained against each other.
- [ ] **Gamma.** Beat humans.

## Development

Requires **Java 17** and **Python 3.13**. Nothing else: the Mindustry server, the bridge
plugin and the game sprites are all fetched or built on first run, pinned to `v159.7`, and
Gradle arrives through the wrapper.

The sprites are the whole game, about four thousand files extracted from the asset jar into
`viewer/assets/sprites/` and fetched by a viewer the first time it draws one. They are not
committed: they regenerate in twenty seconds with `python tools/extract_sprites.py`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pytest    # .venv/bin/python on Linux and macOS
.venv/Scripts/python -m pytest tests/ -v
```

The tests start real Mindustry servers and drive them through stdin and the agent
socket. There are no mocks, because engine state only exists inside a running engine and a
mock of it would assert nothing. A full run takes about 45 seconds.

Throughput measurements are marked `perf` and excluded by default: a second server busy on
another core skews them. Run them alone with `pytest -m perf`.

To reproduce the throughput figures:

```bash
cd bridge && ./gradlew jar && cd ..
.venv/Scripts/python tools/measure_throughput.py --window 5
```

Add `--skip-scaling` to measure a single instance only. Results and their caveats live in
[`docs/measurements/throughput.md`](docs/measurements/throughput.md).

Once a server is running with the plugin installed, console commands are available:
`bridge-status` reports version, clock state, tick and wave; `bridge-bench <seconds>`
measures throughput over a window; `bridge-speed <n|max>` sets simulation speed;
`bridge-port` reports the agent socket.

Running the benchmark:

```bash
.venv/Scripts/python tools/benchmark.py --episodes 5
```

Driving a game from Python:

```python
from gamma.bridge import Bridge

with Bridge(port=7654, tensor=True) as bridge:
    bridge.reset("Ancient_Caldera", "survival")
    for _ in range(100):
        obs = bridge.step(repeat=30)     # world runs 30 ticks, then freezes again
        print(obs["tick"], obs["wave"], obs["items"])

        spatial = obs["spatial"]         # uint8 array, (channels, height, width)
        copper = spatial[bridge.channels.index("ore_copper")]
```

The port defaults to 7654 and is set per instance with `-Dmindustryai.port=N`, which is how
parallel environments avoid colliding.

Or through the Gymnasium environment, which manages the server for you:

```python
from gamma import tasks
from gamma.env import MindustryEnv
from gamma.alpha import AlphaPolicy
from gamma.policies import run_episode

env = MindustryEnv(tasks.T1_COPPER, jar="bridge/build/libs/mindustry-ai-bridge.jar")
print(run_episode(env, AlphaPolicy(env)))
env.close()
```

## Prior art

Several people have started down this road. None have arrived, which is the main reason
this project exists. Recorded here so nobody repeats the same five days of work.

| Project | Stars | Lifespan | What happened |
|---|---|---|---|
| [mindustry-ia-inteface-mod](https://github.com/LyeZinho/mindustry-ia-inteface-mod) | 1 | 5 days | TCP socket exposing game state. Closest to a real bridge. Abandoned. |
| [ReinforcementLearning_MindustryMod](https://github.com/RaptorNava/ReinforcementLearning_MindustryMod) | 1 | 1 day | Copper delivery with drills and conveyors. Never went further. |
| [SLAIdustry](https://github.com/Sisyph-TC/SLAIdustry) | 0 | none | Empty repository. |
| [Mindustry-Mate](https://github.com/QuantumPickleJar/Mindustry-Mate) | 0 | dead since 2023 | "Will eventually employ reinforcement learning." It did not. |
| [Mindustry-MCP](https://github.com/DeterMination-Wind/Mindustry-MCP) | 3 | active | An MCP server driving the game with an LLM. Different goal, no learning, but the most alive of the bunch. |

If you are working on something in this space, open an issue. Duplicated effort is how
this problem stayed unsolved.

## License

[GPL-3.0](LICENSE), inherited from Mindustry, which this project links against.

Mindustry is created by [Anuken](https://github.com/Anuken) and is not affiliated with
this project.
