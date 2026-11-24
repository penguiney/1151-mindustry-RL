# 實驗紀錄(T2_copper_lead_income)
**勝利條件** 從本局開始 450 次 step 內，往核心輸入 200 個 copper 和 200 個 lead 即為勝利。

## 第一次測試 0步
 
**主要嘗試** exp21的模型

**獎勵設計** 
勝利 10.0
```python
succeeded=_income({"copper": 200, "lead": 200}),
reward=lambda before, after: (
    _carrying(0.001)(before, after)
    + _drill_tiles("copper", 0.125)(before, after)
    + _drill_tiles("lead", 0.025)(before, after)
    + _connected_drill_tiles("copper", 0.125)(before, after)
    + _connected_drill_tiles("lead", 0.025)(before, after)
    + _torn(-0.1)(before, after)
    + _churn(-2.0)(before, after)
    + _drilled_tiered("copper", [(1, 0.1), (11, 0.3)])(before, after)
    + _drill_while_unrouted(-0.5, 3)(before, after)
),
```

**測試指令** python -m tools.evaluate checkpoints/exp21/beta.pt --task T2_copper_lead_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4 --items copper,lead,sand
```
    beta  reward  +96.693 +-46.931  worst   +4.328  wave  1.00  built  240.8  produced    477.6  solved 6/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 87% | first_turret 1%
            copper   machine   317.2  hand    42.0 ( 12% by hand) | drills   6.6  connected  92%  running  90%
            lead     machine    17.2  hand    17.7 ( 51% by hand) | drills   0.9  connected  78%  running  78%
            sand     machine   128.8  hand    50.1 ( 28% by hand) | drills   3.1  connected  88%  running  78%

            seed       reward  solved      copper            lead             sand      
                                        machine drills   machine drills   machine drills
            10002      +115.0    0/10     398.9    7.3       0.0    0.0     306.7    5.5
            10003      +132.3    0/10     460.4    8.9       1.9    0.3     269.7    6.1
            10004      +138.3    0/10     471.1    7.7       2.8    0.3     256.4    5.4
            10005      +202.8    0/10     694.2   10.1       3.6    0.7     289.7    7.8
            10013      +131.4    0/10     449.6    7.0      30.7    0.6     222.4    4.0
            10006       +58.1    1/10     177.9    4.9      47.2    2.4      32.4    1.7
            10007      +122.0    0/10     408.9    7.9       1.9    0.1      71.6    1.9
            10008       +94.2    0/10     270.5    7.8      52.3    1.8       0.0    0.6
            10009       +69.3    5/10     209.0    5.2      52.6    3.8       1.5    0.3
            10010       +67.5    0/10     224.4    5.4       0.0    0.0      80.0    1.4
            10001       +78.5    0/10     264.7    5.2       0.0    0.0     316.2    5.6
            10011       +88.4    0/10     298.4    6.1       0.0    0.0      62.4    2.5
            10017       +82.8    0/10     260.3    7.0      37.1    2.1      12.9    2.5
            10024       +29.8    0/10      41.5    4.1       7.1    0.5       0.0    0.3
            10026       +40.1    0/10     128.4    4.6      20.2    1.0       9.5    0.7
```
**結論 ：** 正常，模型沒有被提示過挖鉛。
另外在上一個任務中挖到 200 銅就會自動停止，所以看不出來，實際上 exp21 挖銅的效率在過半的地圖上已經超越 200 了。

---

## 第二次測試 1000000步

**主要嘗試** 將銅礦與鉛礦的相關獎勵調至一樣，加上收入里程碑 `_income_rungs`，銅礦或鉛礦的收入到達 50、100、150、200 時各給 5 分，並更換新的一組訓練種子，從 exp21 接續訓練一百萬步。

在這之前與之後試過的做法（下面列的其他嘗試都是從 exp21 接續訓練一百萬步，除非另外註明）：
- 提高鉛礦的獎勵 -> 模型行為沒有太大變化，鉛維持十幾個。
- `drill_tiered (21, 0)` 鑽頭產出二十個礦物以後不再獎勵 -> 模型開始嘗試大量蓋鑽頭，但大多為無效鑽頭 (沙或是沒有接上的) ，link 錢不夠的次數增加，鉛少量增加至 21。
- `_until_income("copper", 200, ...)` 收到 200 個銅礦後不再獎勵銅礦 -> 鉛沒有成長，entropy 上升；並且觀察到，銅礦收入到 200 時已經沒剩多少時間挖鉛，獎勵方向有問題。
- 鉛礦的獎勵調至與銅礦相同 -> 鉛沒有成長。
- 鉛礦的獎勵調至與銅礦相同，並換新訓練種子 -> 無效，觀察到種子 68 核心旁有 26 格鉛，但模型寧願跑去遠處蓋銅。
- 鉛礦的獎勵調至大於銅礦 -> 鉛 machine 13.5 → 50.5，第一次啟動鉛，但在測試種子 10008、10017 上 agent 什麼都沒挖。
- exp22-7：從 exp22-6 再接續 1M 步，並換新訓練種子 -> 鉛 machine 168.7、銅掉到 87.2，每張圖專門挑一種礦（10009 鉛 404、銅 0）。
- exp22-8 : 這次
- exp22-9：增加`drill_tiered (31, 0)`、單邊里程碑降到 2 分、增加雙邊里程碑 `_joint_income_rungs`（銅鉛都到門檻才給 4 分），訓練共兩百萬步 -> 退步，鉛 machine 只有 21.6，總鑽頭 14.9 最多，鉛鑽頭只有 53% 接上。

**獎勵設計** 
勝利 10.0
```python
succeeded=_income({"copper": 200, "lead": 200}),
reward=lambda before, after: (
    _carrying(0.001)(before, after)
    + _drill_tiles("copper", 0.1)(before, after)
    + _drill_tiles("lead", 0.1)(before, after)
    + _connected_drill_tiles("copper", 0.1)(before, after)
    + _connected_drill_tiles("lead", 0.1)(before, after)
    + _torn(-0.1)(before, after)
    + _churn(-2.0)(before, after)
    + _drilled_tiered("copper", [(1, 0.1), (11, 0.2)])(before, after)
    + _drilled_tiered("lead", [(1, 0.1), (11, 0.2)])(before, after)
    + _drill_while_unrouted(-0.5, 3)(before, after)
    + _income_rungs("copper", (50, 100, 150, 200), 5.0)(before, after)
    + _income_rungs("lead", (50, 100, 150, 200), 5.0)(before, after)
),
```

**訓練指令** python -m tools.train_beta --task T2_copper_lead_income --seed 1,2,43,74,10,48,91,33,62,64,3,44,9,82,41,56,26,92,52,47,4,5,12,27,18,42,68,21,81,88 --steps 1000000 --out checkpoints/exp22-8

**測試指令** python -m tools.evaluate checkpoints/exp21/beta.pt checkpoints/exp22-8/beta.pt --task T2_copper_lead_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4 --items copper,lead,sand
```
  evaluate  300/300 episodes  100%   5:02 elapsed   finished

  exp21/beta  reward  +91.061 +-36.530  worst   +7.716  wave  1.00  built  240.0  produced    486.7  solved 8/150  core tenu 100%
              first_drill 100% | first_conveyor 100% | first_wall 81% | first_turret 3%
              copper   machine   323.8  hand    30.3 (  9% by hand) | drills   6.5  connected  93%  running  91%
              lead     machine    11.9  hand    15.8 ( 57% by hand) | drills   0.7  connected  77%  running  69%
              sand     machine   137.6  hand    64.5 ( 32% by hand) | drills   3.2  connected  86%  running  79%

              seed       reward  solved      copper            lead             sand      
                                          machine drills   machine drills   machine drills
              10002      +103.8    0/10     418.3    7.3       0.0    0.0     295.7    5.6
              10003      +110.1    0/10     439.9    8.9       9.9    0.2     234.0    5.3
              10004      +124.3    0/10     507.6    7.6       7.2    0.5     282.9    6.0
              10005      +168.1    0/10     717.8   10.7       9.3    0.5     271.1    6.6
              10013      +113.4    0/10     441.6    7.6      23.6    0.7     243.7    5.0
              10006       +60.7    1/10     149.4    4.6      19.5    1.3      22.3    1.1
              10007      +108.8    0/10     431.9    7.7       0.6    0.1      81.5    2.2
              10008       +96.6    0/10     285.8    6.5      40.6    1.1       0.0    0.8
              10009       +90.8    7/10     182.2    4.6      43.6    3.1      22.2    0.6
              10010       +60.0    0/10     204.4    4.5       0.0    0.0     121.7    2.2
              10001       +74.6    0/10     267.6    5.4       0.0    0.0     303.8    5.9
              10011       +76.7    0/10     263.4    5.6       1.9    0.1      91.4    2.2
              10017       +83.2    0/10     260.5    6.4      15.7    1.5      48.1    2.8
              10024       +31.9    0/10      72.0    3.9       1.5    0.4      28.6    0.9
              10026       +63.1    0/10     214.0    5.5       4.9    0.6      16.7    1.4
exp22-8/beta  reward  +89.091 +-37.868  worst   +3.242  wave  1.00  built  207.8  produced    586.9  solved 4/150  core tenu 100%
              first_drill 100% | first_conveyor 100% | first_wall 72% | first_turret 4%
              copper   machine   244.5  hand    51.6 ( 17% by hand) | drills   5.8  connected  91%  running  91%
              lead     machine    82.0  hand    29.4 ( 26% by hand) | drills   2.2  connected  88%  running  88%
              sand     machine   244.6  hand   110.3 ( 31% by hand) | drills   6.2  connected  87%  running  87%

              seed       reward  solved      copper            lead             sand      
                                          machine drills   machine drills   machine drills
              10002       +96.7    0/10     376.0    7.6       0.0    0.0     541.9   13.1
              10003      +100.8    1/10     245.9    6.2     113.6    2.7     228.3    5.5
              10004      +107.1    0/10     426.7    7.8       1.9    0.3     482.4   11.6
              10005      +155.6    0/10     657.8   11.9      20.2    0.8     489.4   11.8
              10013      +120.2    1/10     330.0    5.9     116.5    2.6     319.4    7.6
              10006       +48.5    1/10      80.0    3.9      20.4    1.9      73.7    2.1
              10007      +117.2    0/10     457.3   10.6      21.2    0.9     587.7   14.5
              10008      +100.8    1/10      81.0    2.4     277.1    5.1      61.8    2.1
              10009       +66.3    0/10       0.0    0.4     220.6    5.1      62.5    1.3
              10010       +84.9    0/10     307.7   10.0      13.3    1.0      41.6    2.5
              10001       +66.0    0/10     221.3    5.1       1.7    0.1     473.7    8.7
              10011       +58.2    0/10     111.8    4.4      52.8    2.5      66.2    2.3
              10017       +72.2    0/10     187.7    6.0      41.3    1.7     116.2    5.0
              10024       +47.5    0/10      14.5    0.8     139.6    3.5      38.0    1.9
              10026       +94.3    0/10     170.5    3.4     189.4    4.1      86.2    3.6

exp21/beta minus exp22-8/beta: +1.97 +-4.30, 0.5 standard deviations
Not enough evidence to separate them. More episodes, or a bigger difference, or both.
```
**結論 ：** 從 exp21 訓練 1M 步，鉛 machine 就從 11.9 到 82.0，銅維持在 244.5，比 exp22-7 平衡很多。
exp22-4、exp22-5 同樣是同價但沒有里程碑，鉛沒有成長，所以收入里程碑可能是啟動鉛的主要原因（待消融確認）。
仍有只挖一種的情況：10009 銅 0、10008 銅 81。
沙鑽頭從 3.2 增加到 6.2，比銅鑽頭還多。沙在 Mindustry 是 lowPriority，只要鑽頭下有一格銅或鉛就不會挖沙，所以這些是蓋在純沙上的鑽頭，沒有任何正獎勵，只是模型愛亂蓋鑽頭。

## 第三次測試 1000000步

**主要嘗試** 獎勵不變，從 checkpoints/exp22-8 再接續一百萬步。

**獎勵設計** 同上

**訓練指令** python -m tools.train_beta --task T2_copper_lead_income --seed 1,2,43,74,10,48,91,33,62,64,3,44,9,82,41,56,26,92,52,47,4,5,12,27,18,42,68,21,81,88 --steps 1000000 --out checkpoints/exp22-8-2

**測試指令** python -m tools.evaluate checkpoints/exp22-8/beta.pt checkpoints/exp22-8-2/beta.pt --task T2_copper_lead_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4 --items copper,lead,sand
```
    exp22-8/beta  reward  +85.242 +-35.754  worst   +8.661  wave  1.00  built  204.7  produced    571.0  solved 2/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 76% | first_turret 7%
            copper   machine   244.3  hand    50.0 ( 17% by hand) | drills   5.8  connected  90%  running  89%
            lead     machine    61.4  hand    27.4 ( 31% by hand) | drills   1.9  connected  80%  running  78%
            sand     machine   254.9  hand    92.2 ( 27% by hand) | drills   6.2  connected  89%  running  87%

            seed       reward  solved      copper            lead             sand      
                                        machine drills   machine drills   machine drills
            10002       +94.0    0/10     370.1    8.3       0.0    0.0     681.1   14.3
            10003       +98.8    0/10     215.9    5.3     120.3    4.0     248.2    4.9
            10004      +114.4    0/10     462.9    8.4       4.4    0.5     550.5   12.4
            10005      +148.7    0/10     620.7   10.9      18.3    0.7     505.3   12.4
            10013      +121.8    0/10     372.8    6.7      95.6    2.1     371.1    8.7
            10006       +70.4    1/10     161.6    5.0      38.8    2.1      93.9    2.7
            10007      +117.5    0/10     460.5   10.5       7.5    0.7     633.3   15.4
            10008       +88.2    1/10      77.1    2.5     224.2    4.3      40.7    2.2
            10009       +57.6    0/10      43.7    1.4     127.5    4.6      24.8    0.9
            10010       +54.8    0/10     169.9    7.5       0.0    0.1     127.1    2.8
            10001       +59.4    0/10     190.4    5.5       1.5    0.7     395.3    7.2
            10011       +58.0    0/10     137.4    3.5      48.5    1.2      83.0    2.6
            10017       +61.0    0/10     146.2    6.0      28.5    2.3       7.1    1.7
            10024       +53.5    0/10      32.0    1.3     118.8    3.6      13.6    1.6
            10026       +80.5    0/10     203.8    4.9      86.9    2.2      47.9    3.8
    exp22-8-2/beta  reward  +85.950 +-39.127  worst   +0.106  wave  1.00  built  218.7  produced    485.0  solved 5/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 66% | first_turret 11%
            copper   machine   229.7  hand    39.3 ( 15% by hand) | drills   4.9  connected  91%  running  89%
            lead     machine    84.2  hand    21.3 ( 20% by hand) | drills   2.1  connected  84%  running  81%
            sand     machine   158.3  hand    88.5 ( 36% by hand) | drills   3.1  connected  90%  running  86%

            seed       reward  solved      copper            lead             sand      
                                        machine drills   machine drills   machine drills
            10002       +92.5    0/10     358.6    6.6       0.0    0.3     315.2    5.1
            10003       +93.0    1/10     227.9    5.1      85.6    2.1     157.5    2.7
            10004      +113.6    0/10     445.7    7.4       8.3    0.5     326.4    5.9
            10005      +149.8    0/10     631.6   10.1      12.1    0.5     148.6    4.1
            10013      +132.8    3/10     298.2    4.9     167.9    3.2     180.2    3.2
            10006       +48.7    0/10     109.7    3.9      39.1    2.2     104.1    1.9
            10007      +119.3    0/10     474.0    9.9       0.0    0.0     297.2    5.7
            10008      +120.4    1/10      94.7    2.3     343.7    6.3      27.2    0.7
            10009       +75.5    0/10       0.0    0.2     271.2    5.6     110.7    2.0
            10010       +56.0    0/10     180.0    5.1       0.0    0.2     155.8    3.0
            10001       +63.1    0/10     195.4    3.8      17.5    0.6     354.7    6.3
            10011       +74.9    0/10      56.7    1.6     203.3    5.3      32.6    0.4
            10017       +30.1    0/10      59.2    3.1      20.8    2.1     120.2    2.4
            10024       +37.5    0/10      63.0    3.3      51.3    1.7      20.9    0.8
            10026       +81.9    0/10     251.4    5.9      41.9    1.4      23.7    2.3
```




因為舊測試種子 15 個裡有 8 個鉛貧，挑了一組 T2 測試種子，從 seeds.md「銅鉛都不是遠也不是貧」裡選 15 個沒用過的，鉛近 8 個（10015, 10023, 10027, 10029, 10037, 10045, 10063, 10065）、鉛中 7 個（10000, 10016, 10021, 10022, 10030, 10034, 10048）。這些圖兩種礦都拿得到，如果模型還是只挖一種就是策略的問題，不是地圖的問題。

**測試指令** python -m tools.evaluate checkpoints/exp22-8/beta.pt checkpoints/exp22-8-2/beta.pt --task T2_copper_lead_income --seed 10015,10023,10027,10029,10037,10045,10063,10065,10000,10016,10021,10022,10030,10034,10048 --envs 4 --items copper,lead,sand
```
  evaluate  300/300 episodes  100%   3:24 elapsed   finished

exp22-8/beta  reward +121.054 +-35.390  worst  +50.010  wave  1.00  built  221.9  produced    770.5  solved 19/150  core tenu 100%
              first_drill 100% | first_conveyor 100% | first_wall 87% | first_turret 3%
              copper   machine   337.6  hand    24.9 (  7% by hand) | drills   6.7  connected  97%  running  96%
              lead     machine   117.7  hand    20.8 ( 15% by hand) | drills   3.0  connected  91%  running  93%
              sand     machine   304.4  hand   203.7 ( 40% by hand) | drills   7.5  connected  92%  running  90%

              seed       reward  solved      copper            lead             sand      
                                          machine drills   machine drills   machine drills
              10015      +185.3    1/10     681.3   11.1     101.6    4.5     499.8   12.5
              10023      +123.9    2/10     301.5    5.3     142.0    3.9     368.6    8.4
              10027      +116.9    0/10     448.8    9.1      14.8    0.6     505.8   11.7
              10029      +130.8    4/10     267.7    5.9     161.0    2.8     148.4    4.3
              10037      +100.9    3/10     152.6    3.5     174.7    3.9     185.9    3.3
              10045      +167.2    2/10     518.6    9.4     136.0    5.1     373.5    9.3
              10063      +113.7    3/10     236.5    5.2     146.6    3.5     259.2    6.8
              10065      +113.0    0/10     422.2    8.2      33.2    1.0     450.5   11.2
              10000      +100.9    2/10     179.8    3.9     159.8    4.3     189.7    5.1
              10016       +86.0    1/10     142.6    3.7     146.2    4.0      50.6    1.2
              10021       +96.8    0/10      37.3    1.5     319.8    4.9      63.7    1.7
              10022      +143.1    0/10     561.9    9.6      36.7    1.3     541.5   13.1
              10030      +100.6    0/10     372.5    8.0      23.1    1.0     297.7    8.6
              10034       +80.4    1/10     189.1    4.7      78.5    2.7     226.1    5.6
              10048      +156.3    0/10     552.0   10.7      91.7    2.2     405.1   10.4
exp22-8-2/beta  reward +119.376 +-27.534  worst  +54.922  wave  1.00  built  239.0  produced    606.2  solved 20/150  core tenu 100%
              first_drill 100% | first_conveyor 100% | first_wall 81% | first_turret 5%
              copper   machine   308.9  hand    15.9 (  5% by hand) | drills   5.6  connected  97%  running  96%
              lead     machine   137.2  hand    15.1 ( 10% by hand) | drills   2.8  connected  95%  running  94%
              sand     machine   150.3  hand   180.3 ( 55% by hand) | drills   3.0  connected  91%  running  84%

              seed       reward  solved      copper            lead             sand      
                                          machine drills   machine drills   machine drills
              10015      +158.4    1/10     540.2    7.5      98.7    3.1     187.2    3.3
              10023      +141.4    5/10     292.8    4.4     194.4    3.9     152.6    2.6
              10027      +123.2    0/10     489.5    8.6      14.9    0.5     314.2    6.4
              10029      +132.5    7/10     196.7    4.5     227.4    3.8      42.0    1.4
              10037      +102.1    0/10     115.2    2.8     259.1    4.7     174.1    2.8
              10045      +163.9    1/10     532.2    8.7     118.8    2.8     168.3    4.0
              10063       +96.7    1/10     268.3    5.8      75.0    1.9     162.6    3.5
              10065      +112.8    0/10     424.5    7.2      17.6    0.4     203.2    5.4
              10000       +98.0    2/10     212.6    3.7     119.5    3.3     168.6    2.5
              10016      +103.7    0/10     112.8    2.8     265.1    5.1      33.1    0.6
              10021      +110.4    0/10      33.5    0.9     390.9    6.4      54.0    1.4
              10022      +117.3    0/10     443.4    7.1      26.0    1.0     235.4    4.6
              10030       +93.0    0/10     336.0    7.2      22.2    0.6     103.8    2.3
              10034      +102.7    0/10     342.5    6.7      55.5    1.6     209.7    4.1
              10048      +134.6    3/10     294.0    5.4     172.7    2.8      45.4    0.7
```
**結論 ：** 多訓練 1M 步後，沙鑽頭從 6.2 降到 3.1，總鑽頭從 13.9 降到 10.1，亂蓋鑽頭會隨訓練自己減少。鉛 machine 在舊測試種子上從 61.4 到 84.2，solved 從 2 到 5；在 T2 測試種子上兩者差不多（solved 19 和 20）。

同一個 exp22-8 在第二次和這次評估，鉛 machine 分別是 82.0 和 61.4，solved 是 4 和 2，評估雜訊不小。
換成 T2 測試種子後 solved 從 2～5 變成 19～20，舊測試種子的鉛貧圖讓 solved 的上限很低。
兩種礦都拿得到的圖上仍有分配問題：產量足夠（銅加鉛平均約 450），但會一直挖已經超過 200 的那一種。10015（銅 540、鉛 99）、10045（銅 532、鉛 119）銅挖過頭；10027、10065 鉛就在核心旁邊卻只挖銅；10021（銅 34、鉛 391）只挖鉛。

模型在大部分圖上已經會挖銅礦和鉛礦了，有鑑於學期目標是 GZ_capture 而不是完美完成 T2，所以 T2 先停在這裡。