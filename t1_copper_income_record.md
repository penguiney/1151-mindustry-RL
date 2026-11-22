# 實驗紀錄(T1_copper_income)
**勝利條件** 從本局開始450次step內，往核心輸入200個copper即為勝利。

## 第一次測試 0步
 
**主要嘗試** T1_copper第十四次測試的模型

**獎勵設計** 
勝利 10.0
```python
succeeded=_income({"copper": 200}),
reward=lambda before, after: (
        _carrying(0.001)(before, after)
        + _drill_tiles("copper", 0.25)(before, after)
        + _drill_tiles("lead", 0.05)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.1), (6, 0.15), (11, 0.3)])(before, after)
    ),
```

**測試指令** python -m tools.evaluate checkpoints/exp14/beta.pt --task T1_copper_income --items copper --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --episodes 10
```
    beta  reward  +44.628 +-17.686  worst   +2.969  wave  1.00  built  121.5  produced    106.5  solved 87/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 21% | first_turret 1%
            copper   machine    78.6  hand    75.1 ( 49% by hand) | drills  10.6  connected  48%  running  41%

            seed       reward  solved      copper     
                                        machine drills
            10002       +62.5   10/10     175.7    7.8
            10003       +47.3   10/10     125.1    7.4
            10004       +55.5    9/10     143.3    7.9
            10005       +75.2   10/10     200.4    9.8
            10013       +51.8   10/10     122.5    8.3
            10006       +32.8    2/10       0.0   14.4
            10007       +40.4   10/10      84.1    8.2
            10008       +38.8    2/10      10.7   15.0
            10009       +46.9    8/10     102.4    6.5
            10010       +50.9    4/10      72.1   13.3
            10001       +22.3    0/10       6.3   10.2
            10011       +35.2    3/10      33.0   11.9
            10017       +29.6    0/10       0.0   14.0
            10024       +30.7    0/10      15.5   12.5
            10026       +49.6    9/10      87.5   11.3
```
**結論**  exp14/beta.pt 在收入 200 銅的目標上，成功率達到了 87/150（ 58% )，並且作為測試的 15 個種子均沒有參與過訓練。成敗主要看種子，而且分得很清楚：被標注為困難的種子，雖然都有蓋鑽頭，但是送入核心的量為0，被標注為容易的種子，有些能拿到 10/10 的成功率，且鑽頭數量沒有比失敗的種子多，問題很可能出在 link 動作。

---

## 第二次測試 300000步
 
**主要嘗試** 從實驗記錄中觀察到 link 動作經常被 too far 跟 can't afford 拒絕 ，其中 too far 的判定是要新建的傳送帶數量超過 CONNECT_BUDGET 格。
將 link 動作中的 CONNECT_BUDGET 從 60 改至 256 ，可覆蓋大範圍的地塊。
 從exp14接續訓練，分成兩個版本，沒有改跟有改的各訓練 300000 步來測試學習傾向。

 
**獎勵設計** 同上

**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp15
            python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp15-budget-60



**測試指令** python -m tools.evaluate checkpoints/exp15/beta.pt checkpoints/exp15-budget-60/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026


**在 CONNECT_BUDGET = 60 的情況下測試**
```
    exp15/beta  reward  +51.690 +-20.797  worst   +3.688  wave  1.00  built  131.4  produced    234.9  solved 90/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 65% | first_turret 2%
            copper   machine   127.7  hand    28.5 ( 18% by hand) | drills   8.5  connected  59%  running  59%

            seed       reward  solved      copper     
                                        machine drills
            10002       +67.6   10/10     192.2    8.5
            10003       +59.4   10/10     175.4    9.0
            10004       +66.4   10/10     189.1    8.9
            10005       +62.5    6/10     153.3   13.2
            10013       +69.8   10/10     200.1    8.6
            10006       +56.9    6/10     135.0    6.2
            10007       +63.4    9/10     156.7   10.7
            10008       +32.0    1/10       9.0   11.4
            10009       +35.0    3/10      66.7    7.6
            10010       +40.0    3/10      78.5    9.7
            10001       +57.9    7/10     162.3    5.8
            10011       +56.1    5/10     150.8    7.7
            10017       +15.4    0/10       0.0    8.2
            10024       +28.9    2/10      67.8    5.7
            10026       +64.1    8/10     178.4    6.7
    exp15-budget-60/beta  reward  +45.086 +-19.391  worst  +16.643  wave  1.00  built  103.3  produced    130.9  solved 64/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 53% | first_turret 3%
            copper   machine    84.6  hand    30.5 ( 26% by hand) | drills  11.2  connected  37%  running  34%

            seed       reward  solved      copper     
                                        machine drills
            10002       +62.3   10/10     183.1    9.2
            10003       +59.1    9/10     168.1    9.0
            10004       +63.9   10/10     175.7   10.0
            10005       +57.2    5/10     121.7   12.5
            10013       +69.8   10/10     193.2    8.7
            10006       +24.1    0/10       0.0   12.5
            10007       +63.4   10/10     162.9   10.3
            10008       +35.4    1/10      15.8   14.4
            10009       +52.9    5/10     114.2    6.1
            10010       +41.8    3/10      76.0    7.8
            10001       +30.0    0/10       0.0   15.4
            10011       +26.2    0/10       0.0   13.0
            10017       +22.8    0/10       1.3   11.9
            10024       +31.9    0/10      28.4   12.6
            10026       +35.5    1/10      29.1   14.7
```

**在 CONNECT_BUDGET = 256 的情況下測試**
```
    exp15/beta  reward  +54.402 +-19.470  worst   +2.685  wave  1.00  built  136.4  produced    236.5  solved 97/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 62%
            copper   machine   132.9  hand    31.1 ( 19% by hand) | drills   8.7  connected  59%  running  61%

            seed       reward  solved      copper     
                                        machine drills
            10002       +65.7   10/10     192.5    9.4
            10003       +60.9   10/10     168.4    8.8
            10004       +71.3   10/10     198.7    9.0
            10005       +59.9    5/10     133.4   13.0
            10013       +69.7   10/10     200.0    8.7
            10006       +52.3    7/10     132.9    5.7
            10007       +65.3    9/10     162.8   10.8
            10010       +45.2    3/10      72.8   12.2
            10001       +62.7    9/10     166.2    4.8
            10011       +54.8    5/10     131.9    7.2
            10017       +42.3    4/10      79.7    9.4
            10024       +25.6    1/10      40.6    7.0
            10026       +66.9    9/10     185.8    7.1
    exp15-budget-60/beta  reward  +53.122 +-17.934  worst  +16.738  wave  1.00  built  130.1  produced    158.2  solved 86/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 60% | first_turret 3%
            copper   machine   109.8  hand    33.2 ( 23% by hand) | drills  10.5  connected  49%  running  49%

            seed       reward  solved      copper     
                                        machine drills
            10002       +65.0    9/10     192.2    9.2
            10003       +61.5    9/10     176.7    9.5
            10004       +64.4   10/10     186.9    9.0
            10005       +73.2    8/10     183.7   12.4
            10013       +68.2   10/10     192.1    8.7
            10006       +40.8    3/10      62.6   10.1
            10007       +62.2   10/10     161.1   10.7
            10008       +48.1    3/10      36.0   12.9
            10009       +56.3    7/10     120.5    6.2
            10010       +50.7    4/10      99.3   10.1
            10001       +30.4    0/10       6.7   14.4
            10011       +42.6    3/10      44.9   11.4
            10017       +56.9    5/10      99.2   10.5
            10024       +35.0    2/10      41.4   10.0
            10026       +41.5    3/10      44.0   12.5
```
**結論 ：** 將兩種訓練條件和兩種評估條件的勝率畫成 2×2 表格：

|模型|CONNECT_BUDGET = 256 時評估|CONNECT_BUDGET = 60 時評估|
| --- | --- | --- |
|CONNECT_BUDGET = 256 時訓練|97 |90|
|CONNECT_BUDGET = 60 時訓練|86|64 |

評估時放寬預算，兩個模型都會變好： exp15 多 7 局，budget-60 多 22 局。
用同樣條件評估，CONNECT_BUDGET = 256 時訓練的模型還是比較好： 在 60 的環境下是 90 對 64，在 256 的環境下是 97 對 86。可以發現 exp15 模型的策略本身就比較好。

目前兩個模型的差距集中在中等到難的種子 (10001, 10006, 10011, 10026)，exp15-budget-60 的模型在這些種子上大量蓋鑽頭卻接不上線。

---

## 第三次測試 300000步
 
**主要嘗試** 改變 connected 的定義，現在需要真的把鑽頭接傳送帶到核心或是消耗銅的工廠才能算是 connected，此舉影響 connected_drill_tiles，暫時不影響其他結果。實驗上用 _connected_drill_tiles 取代了 _drill_tiles，從exp15接續，與對照組共訓練三十萬步測試成效。

 
**獎勵設計** 
勝利 10.0
```python
succeeded=_income({"copper": 200}),
reward=lambda before, after: (
        _carrying(0.001)(before, after)
        + _connected_drill_tiles("copper", 0.25)(before, after)
        + _connected_drill_tiles("lead", 0.05)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.1), (6, 0.15), (11, 0.3)])(before, after)
    ),
```

**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp16
            python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp16-control



**測試指令** python -m tools.evaluate checkpoints/exp16/beta.pt checkpoints/exp16-control/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026
```
    exp16/beta  reward  +44.341 +-26.578  worst   -0.052  wave  1.00  built  152.9  produced    271.2  solved 81/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 71% | first_turret 3%
            copper   machine   116.7  hand    18.9 ( 14% by hand) | drills   5.5  connected  75%  running  76%

            seed       reward  solved      copper
                                        machine drills
            10002       +66.1   10/10     199.4    7.2
            10003       +53.3    7/10     154.9    5.6
            10004       +62.6    8/10     185.5    5.0
            10005       +66.9   10/10     200.6   10.1
            10013       +64.7   10/10     194.9    8.5
            10006       +35.3    2/10      87.3    4.0
            10007       +69.4    9/10     188.7    9.2
            10008       +36.1    3/10      54.1    5.2
            10009       +14.4    1/10      35.3    1.9
            10010       +32.5    1/10      37.8    6.2
            10001       +14.2    1/10      31.2    3.8
            10011       +51.4    7/10     144.8    5.1
            10017       +19.0    2/10      26.9    2.6
            10024       +18.8    1/10      36.1    2.3
            10026       +60.6    9/10     173.0    5.7
    exp16-control/beta  reward  +47.899 +-23.587  worst   +0.080  wave  1.00  built  153.9  produced    199.3  solved 83/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 70% | first_turret 4%
            copper   machine   119.0  hand    27.4 ( 19% by hand) | drills   8.3  connected  63%  running  56%

            seed       reward  solved      copper
                                        machine drills
            10002       +66.4   10/10     185.2    9.0
            10003       +65.8   10/10     183.5    7.5
            10004       +66.5   10/10     191.3    9.7
            10005       +49.8    4/10     105.4   13.9
            10013       +65.2   10/10     187.5    9.5
            10006       +55.6    7/10     124.2    6.1
            10007       +65.6    8/10     168.5   11.0
            10008       +29.0    2/10      45.0   10.0
            10009       +23.9    1/10      40.3    4.5
            10010       +27.7    1/10      30.8   10.8
            10001       +22.2    0/10      40.1    8.0
            10011       +63.6    9/10     175.9    7.5
            10017       +29.2    1/10      73.4    5.1
            10024       +21.9    1/10      54.1    5.4
            10026       +66.1    9/10     180.5    6.7
```
成功率沒有明顯的差別，但是觀察到在難的種子上鑽頭數變少了



**測試指令** python -m tools.evaluate checkpoints/exp15/beta.pt checkpoints/exp16/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026
```
    exp15/beta  reward  +48.125 +-19.502  worst   +6.305  wave  1.00  built  140.0  produced    184.8  solved 100/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 66% | first_turret 2%
            copper   machine   121.3  hand    46.2 ( 28% by hand) | drills   9.5  connected  57%  running  63%

            seed       reward  solved      copper
                                        machine drills
            10002       +61.8   10/10     179.3    9.4
            10003       +47.7    9/10     131.4    7.9
            10004       +57.7   10/10     162.2   10.9
            10005       +67.1    9/10     187.7   13.3
            10013       +58.6   10/10     165.8    9.9
            10006       +52.1    9/10     134.2    6.6
            10007       +57.6   10/10     152.5    9.9
            10008       +39.1    5/10      59.7   13.2
            10009       +20.7    1/10      30.1    9.0
            10010       +42.0    3/10      83.2   12.1
            10001       +26.0    0/10      39.2   10.9
            10011       +56.9    9/10     157.6    6.8
            10017       +47.1    5/10     117.1    7.7
            10024       +22.5    2/10      42.0    7.3
            10026       +65.0    8/10     177.5    7.4
    exp16/beta  reward  +45.742 +-24.966  worst   +0.053  wave  1.00  built  158.2  produced    291.1  solved 93/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 82% | first_turret 4%
            copper   machine   123.5  hand    25.6 ( 17% by hand) | drills   5.5  connected  78%  running  81%

            seed       reward  solved      copper
                                        machine drills
            10002       +62.8   10/10     185.7    5.6
            10003       +51.7    7/10     138.6    5.2
            10004       +65.9   10/10     189.0    5.4
            10005       +66.1   10/10     200.5   10.9
            10013       +64.8   10/10     196.7    8.0
            10006       +42.4    5/10     102.0    4.9
            10007       +57.6    8/10     157.1    8.3
            10008       +40.8    5/10     101.7    5.3
            10009       +27.7    4/10      66.3    3.4
            10010       +44.8    5/10      85.1    8.1
            10001       +11.3    0/10      36.4    1.6
            10011       +59.8    8/10     166.8    5.6
            10017       +26.7    3/10      56.4    4.4
            10024        +9.6    0/10      14.1    1.6
            10026       +54.0    8/10     155.8    4.6
```

**結論 ：** exp16 和 exp16-control 都是從 exp15 接續訓練三十萬步，兩者的勝率都比 exp15 低 (但沒有到顯著差別)。 reward 改動沒有太影響評估結果，接續訓練 300k 步才是勝率下降的原因。
無法判斷 connected 獎勵對勝率有沒有幫助。但鑽頭數從 9.5 降到 5.5，在種子 10001、10024 上，鑽頭只剩 1.6 顆，幾乎沒有收入。
另外，exp16 送進核心的非銅礦明顯變多，可能要進一步觀察

---

## 第四次測試 300000步
 
**主要嘗試** 混合_connected_drill_tiles 與 _drill_tiles獎勵，預期減少AI退化的情形，從exp15接續訓練三十萬步以測試成效，對照組使用exp16-control。

 
**獎勵設計** 
勝利 10.0
```python
succeeded=_income({"copper": 200}),
reward=lambda before, after: (
        _carrying(0.001)(before, after)
        + _drill_tiles("copper", 0.125)(before, after)
        + _drill_tiles("lead", 0.025)(before, after)
        + _connected_drill_tiles("copper", 0.125)(before, after)
        + _connected_drill_tiles("lead", 0.025)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.1), (6, 0.15), (11, 0.3)])(before, after)
    ),
```

**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp17

**測試指令** python -m tools.evaluate checkpoints/exp17/beta.pt checkpoints/exp16-control/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4 
```
    exp17/beta  reward  +50.861 +-20.928  worst   +0.111  wave  1.00  built  145.0  produced    236.1  solved 98/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 85% | first_turret 5%
            copper   machine   133.1  hand    32.3 ( 20% by hand) | drills   7.6  connected  64%  running  65%

            seed       reward  solved      copper     
                                        machine drills
            10002       +65.4   10/10     196.8    7.5
            10003       +61.5   10/10     180.0    7.3
            10004       +66.4   10/10     193.4    8.4
            10005       +55.7    7/10     139.2   11.2
            10013       +67.8   10/10     196.8    7.8
            10006       +53.0    6/10     116.5    5.7
            10007       +62.1    9/10     163.3    9.8
            10008       +38.8    4/10      69.0   10.2
            10009       +40.5    4/10     101.0    6.2
            10010       +30.3    2/10      54.0    9.5
            10001       +57.0    6/10     147.2    7.7
            10011       +55.2    8/10     155.0    5.4
            10017       +28.0    3/10      75.8    4.5
            10024       +23.8    0/10      42.7    5.9
            10026       +57.4    9/10     166.0    6.5
    exp16-control/beta  reward  +45.266 +-23.440  worst   +0.041  wave  1.00  built  152.3  produced    177.1  solved 82/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 67%
            copper   machine   108.4  hand    34.5 ( 24% by hand) | drills   8.3  connected  59%  running  55%

            seed       reward  solved      copper     
                                        machine drills
            10002       +63.7   10/10     179.0    9.5
            10003       +60.2    9/10     173.1    7.7
            10004       +63.5   10/10     174.0   10.1
            10005       +43.4    3/10      81.5   13.6
            10013       +65.0   10/10     184.0    9.9
            10006       +52.1    6/10      99.7    5.8
            10007       +63.9   10/10     161.3   10.0
            10008       +26.5    2/10      23.6   12.6
            10009       +26.4    1/10      69.5    5.3
            10010       +24.6    1/10      33.9   10.4
            10001       +27.8    1/10      62.7    6.9
            10011       +55.2    7/10     128.0    6.9
            10017       +38.7    3/10      83.0    5.6
            10024       +13.7    1/10      26.7    3.9
            10026       +54.5    8/10     146.1    6.9
```


**測試指令** python -m tools.evaluate checkpoints/exp17/beta.pt checkpoints/exp15/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4      
```
evaluate  300/300 episodes  100%   3:51 elapsed   finished

    exp17/beta  reward  +50.964 +-21.292  worst   +3.831  wave  1.00  built  138.7  produced    212.7  solved 100/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 89% | first_turret 5%
            copper   machine   128.3  hand    29.5 ( 19% by hand) | drills   8.1  connected  60%  running  59%

            seed       reward  solved      copper     
                                        machine drills
            10002       +62.7   10/10     189.7    8.5
            10003       +58.6   10/10     176.6    7.5
            10004       +67.2   10/10     191.3    8.1
            10005       +47.7    4/10     112.0   11.1
            10013       +66.4   10/10     193.3    7.7
            10006       +56.2    7/10     122.5    6.4
            10007       +67.0    9/10     166.4   10.3
            10008       +38.5    4/10      62.6   11.8
            10009       +34.0    2/10      89.4    6.1
            10010       +26.1    1/10      29.2   12.0
            10001       +61.2    9/10     161.6    6.1
            10011       +58.9   10/10     159.5    6.0
            10017       +41.7    4/10      78.1    6.8
            10024       +17.6    0/10      27.6    6.6
            10026       +60.8   10/10     165.4    5.9
    exp15/beta  reward  +49.017 +-20.592  worst   +1.388  wave  1.00  built  140.5  produced    181.4  solved 101/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 63% | first_turret 4%
            copper   machine   122.2  hand    41.9 ( 26% by hand) | drills   9.2  connected  59%  running  64%

            seed       reward  solved      copper     
                                        machine drills
            10002       +61.3   10/10     178.4   10.0
            10003       +50.9    9/10     146.2    8.3
            10004       +60.6   10/10     172.5   10.3
            10005       +51.3    6/10     132.0   13.7
            10013       +58.4   10/10     166.2    9.0
            10006       +50.1    8/10     121.5    5.4
            10007       +62.0   10/10     153.7   11.7
            10008       +49.8    6/10      83.3   12.4
            10009       +44.5    6/10      99.2    7.2
            10010       +30.0    1/10      37.8   13.9
            10001       +34.6    1/10      82.1    8.6
            10011       +58.8    8/10     161.8    7.1
            10017       +44.9    5/10      99.0    8.2
            10024       +15.8    3/10      28.6    4.5
            10026       +62.2    8/10     170.2    7.5
```
**結論 ：** exp17 在兩次評估中為 98 與 100，與 exp15（101）持平，並明顯高於相同步數的 control（82）。混合獎勵避免了接續訓練造成的勝率下降，同時解決了 exp16 在難種子上鑽頭太少的問題。10001 從 1/10 提升到 6–9/10，但 10024 在兩次評估中都是 0/10，且鑽頭數不少，原因待查。

---

## 第五次測試 1000000步
 
**主要嘗試** 從exp17接續訓練一百萬步以測試成效，對照組使用exp17。

 **獎勵設計** 同上

 
**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 300000 --out checkpoints/exp17-1m

**測試指令** python -m tools.evaluate checkpoints/exp17-1m/beta.pt checkpoints/exp17/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4
```
    exp17-1m/beta  reward  +48.418 +-23.400  worst   -2.011  wave  1.00  built  164.3  produced    206.2  solved 88/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 82%
            copper   machine   121.5  hand    24.5 ( 17% by hand) | drills   7.0  connected  68%  running  67%

            seed       reward  solved      copper     
                                        machine drills
            10002       +66.0   10/10     193.4    8.0
            10003       +63.6    7/10     172.3    6.1
            10004       +64.2   10/10     186.3    8.1
            10005       +50.1    4/10     112.9   15.2
            10013       +66.6   10/10     193.7    7.3
            10006       +54.8    7/10     126.5    6.5
            10007       +66.9   10/10     180.0    9.3
            10008       +66.3    9/10     136.6    9.4
            10009       +29.1    1/10      76.1    3.2
            10010       +32.2    3/10      47.8    9.1
            10001       +18.7    0/10      47.3    4.4
            10011       +40.6    6/10      81.7    5.7
            10017       +34.8    5/10      81.4    3.9
            10024       +12.8    1/10      31.3    3.1
            10026       +59.6    5/10     155.6    5.9
    exp17/beta  reward  +52.388 +-20.563  worst   +0.051  wave  1.00  built  146.5  produced    243.8  solved 105/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 89% | first_turret 3%
            copper   machine   137.7  hand    30.0 ( 18% by hand) | drills   7.5  connected  65%  running  70%

            seed       reward  solved      copper     
                                        machine drills
            10002       +63.2   10/10     190.5    7.5
            10003       +59.6   10/10     176.0    7.7
            10004       +65.4   10/10     182.5    7.9
            10005       +43.3    4/10     100.8   11.3
            10013       +67.9   10/10     200.6    7.4
            10006       +61.4    8/10     166.5    4.8
            10007       +62.1   10/10     163.9   10.0
            10008       +40.5    5/10      77.8    9.3
            10009       +35.3    3/10      88.7    6.7
            10010       +35.6    1/10      67.8    9.7
            10001       +57.9    6/10     153.7    6.0
            10011       +58.2   10/10     158.2    6.4
            10017       +37.0    4/10      85.8    6.2
            10024       +33.7    4/10      70.1    4.6
            10026       +65.0   10/10     182.4    6.3
```

在難的種子上不蓋鑽頭的情形又出現了：
| | exp15 | exp17 | exp17-1m |
| --- | --- | --- | --- |
| 獲勝局數 | 95, 101 | 98, 100 | 77 |
| 平均鑽頭數 | 9.2 | 7.6–8.1 | 6.7 |
| 接上的比例 | 58% | 60–64% | 67% |
| 手送比例 | 25% | 19–20% | 18% |

這和 exp16 的情況一樣，接上的比例變高，鑽頭卻變少。exp17 還沒出現這種現象，但是練一百萬步以後就出現了。



**測試指令** python -m tools.evaluate checkpoints/exp17-1m/beta.pt checkpoints/exp17/beta.pt --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --envs 4     
```
 exp17-1m/beta  reward  +57.781 +-18.974  worst   +0.215  wave  1.00  built  177.0  produced    239.1  solved 115/150  core tenu 100%
                first_drill 100% | first_conveyor 100% | first_wall 86% | first_turret 1%
                copper   machine   152.5  hand    18.1 ( 11% by hand) | drills   7.2  connected  78%  running  83%

            seed       reward  solved      copper
                                        machine drills
            1           +63.9    8/10     181.8    5.5
            2           +63.1   10/10     190.1   11.7
            6           +64.4   10/10     190.1    7.6
            7           +63.7   10/10     189.6    6.9
            10          +60.5    7/10     118.9   10.4
            3           +54.4    4/10     113.9    4.9
            8           +61.1    9/10     173.0    7.2
            9           +29.3    2/10      60.0    5.7
            11          +63.9   10/10     200.1    8.6
            17          +51.5    7/10     153.1    4.7
            4           +64.7    8/10     147.4    7.8
            5           +71.8   10/10     187.2    8.4
            12          +67.6   10/10     190.0    8.4
            13          +22.2    1/10      40.6    2.3
            18          +64.8    9/10     152.4    7.9
    exp17/beta  reward  +57.301 +-15.368  worst   +5.503  wave  1.00  built  162.4  produced    265.2  solved 122/150  core tenu 100%
                first_drill 100% | first_conveyor 100% | first_wall 95% | first_turret 2%
                copper   machine   158.9  hand    26.6 ( 14% by hand) | drills   7.4  connected  78%  running  82%

            seed       reward  solved      copper
                                        machine drills
            1           +60.1    9/10     186.6    6.4
            2           +65.6   10/10     196.3   10.5
            6           +63.1   10/10     187.9    7.8
            7           +61.6   10/10     183.0    7.0
            10          +63.3    9/10     174.4    8.1
            3           +49.3    7/10     133.3    5.9
            8           +57.8   10/10     159.2    6.2
            9           +31.2    1/10      56.5    7.4
            11          +66.1   10/10     200.6    8.9
            17          +62.0   10/10     181.4    6.3
            4           +62.8    9/10     159.5    7.1
            5           +64.6    9/10     167.6    7.5
            12          +64.5   10/10     171.7    8.6
            13          +29.3    2/10      76.5    5.2
            18          +58.3    6/10     149.4    7.9
```
**結論 ：** 很像是過擬合。在有訓練過的種子裡，reward 和勝率都很接近。但在沒訓練過的種子，勝率的差距達到17局。如果繼續在同樣的15個種子上訓練，練越久就會越過擬合，考慮新增種子。

---

## 第六次測試 1000000步
 
**主要嘗試** 增加測試地圖種子至 30 個，從 exp17 接續訓練一百萬步以測試成效，對照組使用 exp17，預計看到過擬合情況消失。

**獎勵設計** 同上

 
**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,48,91,33,62,36,3,8,9,11,17,56,26,92,52,47,4,5,12,13,18,42,29,21,81,88 --steps 1000000 --out checkpoints/exp18

**測試指令** python -m tools.evaluate checkpoints/exp18/beta.pt checkpoints/exp17/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4
```
    exp18/beta  reward  +51.710 +-22.357  worst   +1.024  wave  1.00  built  148.8  produced    198.3  solved 98/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 79% | first_turret 3%
            copper   machine   123.9  hand    30.4 ( 20% by hand) | drills   8.4  connected  62%  running  59%

            seed       reward  solved      copper     
                                        machine drills
            10002       +65.2   10/10     191.0    8.4
            10003       +63.0   10/10     190.5    7.9
            10004       +68.0   10/10     195.5    8.1
            10005       +74.5    8/10     160.2   13.7
            10013       +69.2   10/10     200.2    9.5
            10006       +41.2    7/10      74.6    7.5
            10007       +62.7   10/10     174.8    8.6
            10008       +50.9    5/10      98.6   10.6
            10009       +45.9    6/10      82.8    7.2
            10010       +35.8    1/10      70.3    7.7
            10001       +64.0    9/10     181.0    5.7
            10011       +56.1    5/10     159.2    7.2
            10017       +18.9    2/10      28.8    6.7
            10024       +30.7    3/10      12.4    8.2
            10026       +29.4    2/10      39.1    8.9
    exp17/beta  reward  +48.166 +-23.473  worst   +0.129  wave  1.00  built  136.2  produced    221.4  solved 93/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 81% | first_turret 5%
            copper   machine   123.1  hand    29.2 ( 19% by hand) | drills   7.6  connected  59%  running  58%

            seed       reward  solved      copper     
                                        machine drills
            10002       +65.3   10/10     194.4    8.0
            10003       +60.1   10/10     175.1    6.6
            10004       +63.3   10/10     184.7    7.9
            10005       +45.1    4/10      95.2   11.5
            10013       +67.0   10/10     193.6    7.7
            10006       +47.4    6/10      88.1    5.9
            10007       +66.8    9/10     181.5   10.0
            10008       +38.4    4/10      65.1   11.8
            10009       +29.5    3/10      49.5    6.8
            10010       +28.6    2/10      55.3    9.4
            10001       +61.6    7/10     162.6    7.2
            10011       +57.0    8/10     162.0    5.7
            10017       +20.0    1/10      41.9    5.8
            10024       +13.7    1/10      30.0    3.7
            10026       +58.5    8/10     167.5    6.0
```
沒有明顯的變化，既沒有出現過擬合，也沒有從新的地圖上學習到新招式

**測試指令** python -m tools.evaluate checkpoints/exp18/beta.pt checkpoints/exp17/beta.pt --task T1_copper_income --seed 1,2,6,7,10,48,91,33,62,36,3,8,9,11,17,56,26,92,52,47,4,5,12,13,18,42,29,21,81,88 --envs 4 --items copper,lead,coal,sand

```
    exp18/beta  reward  +57.134 +-16.574  worst   +1.296  wave  1.00  built  159.6  produced    245.3  solved 250/300  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 84%
            copper   machine   150.2  hand    31.0 ( 17% by hand) | drills   8.4  connected  70%  running  75%
            lead     machine     4.7  hand     3.5 ( 43% by hand) | drills   0.6  connected  38%  running  54%
            coal     machine     2.4  hand     0.0 (  0% by hand) | drills   0.5  connected  34%  running  53%
            sand     machine    87.9  hand    34.5 ( 28% by hand) | drills   2.7  connected  84%  running  87%

            seed       reward  solved      copper            lead             coal             sand
                                        machine drills   machine drills   machine drills   machine drills
            1           +65.8   10/10     199.2    7.1       0.0    0.0       1.5    0.1     228.0    6.3
            2           +69.2   10/10     200.5   11.7       3.9    0.5       0.0    0.0      14.6    1.2
            6           +62.1   10/10     190.3    8.6       0.0    0.0       5.8    0.6      86.8    3.7
            7           +63.2   10/10     186.6    6.8      11.2    0.6      10.7    0.6     109.3    2.7
            10          +62.5    8/10     129.5   10.7       0.0    0.0       0.0    0.1       0.4    0.1
            48          +54.2    6/10     160.3    5.1      18.3    0.8       4.4    0.2     345.7    6.5
            91          +65.4   10/10     193.8    6.6       3.6    0.2       3.3    0.4     137.1    4.9
            33          +65.3   10/10     191.4    8.3       3.0    0.2       0.0    0.0      60.6    2.8
            62          +67.2   10/10     200.3    7.9       0.0    0.0       1.1    0.2      90.5    3.4
            36          +67.2   10/10     198.4   11.3       0.0    0.1       1.8    0.3      19.1    1.6
            3           +58.5   10/10     166.8    6.8       0.0    0.0      10.1    0.9     160.5    4.2
            8           +70.1   10/10     197.7    7.6       0.0    0.0       5.7    0.5      71.1    2.8
            9           +18.2    0/10      14.3    7.9       3.5    3.1       0.0    0.3       8.1    0.2
            11          +67.3   10/10     197.3    9.7       0.0    0.0       0.6    0.4      30.8    1.4
            17          +64.0   10/10     185.8    7.1       0.0    0.0       3.4    0.3      85.7    3.3
            56          +65.0   10/10     174.5    6.8      25.9    1.4       4.0    0.3      86.6    4.0
            26          +51.1   10/10     138.4    7.2      20.6    1.5       0.0    0.0      10.7    0.2
            92          +45.8    5/10     128.4    8.2       4.9    1.2       5.9    0.2     137.1    2.7
            52          +60.5    9/10     180.1    6.3       4.6    0.1       1.0    0.1     139.9    4.6
            47          +61.9    9/10     189.1    4.7       0.0    0.0       1.5    0.1     500.0    8.5
            4           +49.1    5/10      78.9   13.4       0.2    0.0       0.0    0.0       0.0    0.0
            5           +57.0   10/10     153.4    8.7       9.1    0.9       0.0    0.0       5.0    0.4
            12          +67.9   10/10     183.4    9.2       0.0    0.1       0.0    0.0      32.7    3.0
            13          +23.7    3/10      19.1    9.5       0.0    3.0       4.7    2.0      11.8    1.8
            18          +62.7    8/10     159.5    8.9       4.3    0.2       0.0    0.1      69.8    3.0
            42          +42.8    7/10      50.0    8.9       0.0    2.2       2.0    2.9       0.0    0.1
            29          +35.3    5/10      62.2    8.5       3.1    0.5       3.5    1.8       5.9    0.8
            21          +44.3    8/10      38.5    9.8       0.1    1.1       0.0    2.0       7.7    0.5
            81          +66.4    9/10     179.0    9.0       9.7    0.3       0.3    0.4      93.1    3.5
            88          +60.3    8/10     160.1    8.6      16.4    0.6       0.0    0.0      89.2    3.6

    exp17/beta  reward  +53.558 +-17.404  worst   +2.690  wave  1.00  built  155.0  produced    281.2  solved 227/300  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 91% | first_turret 6%
            copper   machine   148.7  hand    30.1 ( 17% by hand) | drills   7.3  connected  76%  running  79%
            lead     machine     7.7  hand     4.8 ( 38% by hand) | drills   0.7  connected  47%  running  67%
            coal     machine     7.1  hand     0.0 (  0% by hand) | drills   0.6  connected  47%  running  65%
            sand     machine   117.7  hand    43.3 ( 27% by hand) | drills   3.9  connected  82%  running  86%

            seed       reward  solved      copper            lead             coal             sand
                                        machine drills   machine drills   machine drills   machine drills
            1           +64.0   10/10     193.6    6.7       0.0    0.0       1.2    0.1     244.5    7.1
            2           +67.6   10/10     198.2   10.5       5.2    0.5       0.0    0.0      51.6    3.4
            6           +63.9   10/10     187.1    7.6       0.0    0.0       0.1    0.0     135.5    5.9
            7           +55.5    9/10     161.3    6.6       9.6    1.0      13.6    0.9     155.1    4.3
            10          +47.7    5/10     123.1    8.9       0.0    0.0      22.4    0.7      45.6    1.7
            48          +32.4    1/10     102.3    3.9      21.7    1.7      12.1    1.1     367.4    7.1
            91          +57.2   10/10     166.9    6.4       8.0    0.6      22.4    1.0     168.6    6.1
            33          +64.8    9/10     187.1    7.0       1.6    0.3       0.0    0.0     180.5    5.6
            62          +58.7   10/10     168.8    6.3       0.0    0.0       7.9    0.5     229.9    7.0
            36          +67.9   10/10     198.3   11.2       0.0    0.2      10.7    0.7      27.0    1.9
            3           +54.1    7/10     138.3    6.8       0.0    0.0      32.0    2.3      97.7    2.0
            8           +62.6    8/10     166.1    6.9       0.0    0.0      22.0    1.4     101.1    3.8
            9           +24.7    1/10      53.6    7.5       4.4    2.8       6.5    0.5     102.9    2.4
            11          +65.8   10/10     200.4    9.2       0.0    0.0       0.6    0.4      80.7    4.0
            17          +53.5    9/10     157.5    6.7       0.0    0.2      16.3    1.1     108.3    4.8
            56          +57.9    9/10     154.1    5.9      24.1    1.3       1.8    0.3     173.0    5.7
            26          +45.9    7/10     130.7    7.9       8.1    2.2       0.0    0.1      19.7    0.9
            92          +50.0    8/10     155.4    6.3       3.5    0.4       5.1    0.3     203.1    4.9
            52          +58.5   10/10     179.2    6.9       7.0    0.5       1.1    0.1     140.2    4.4
            47          +56.2    7/10     178.7    4.7      20.2    1.2       0.0    0.0     366.5    7.4
            4           +59.1    8/10     143.4    8.4       0.0    0.5       0.8    0.2      53.4    2.1
            5           +60.8   10/10     154.1    8.0       3.0    0.5       0.0    0.1      38.4    2.8
            12          +64.7   10/10     174.2    8.4       4.3    0.3       0.0    0.0      52.8    3.8
            13          +28.3    3/10      66.5    5.0      18.2    1.4      16.0    1.6      97.6    2.2
            18          +50.0    5/10     123.2    8.9      18.9    1.0       0.0    0.1      54.3    3.5
            42          +25.5    1/10      39.0    4.9      15.0    1.0      10.9    2.0      11.2    1.2
            29          +25.8    2/10      57.7    7.0      11.1    0.7       1.2    1.3      27.3    1.6
            21          +55.8    9/10     155.5    9.0      16.8    1.7       0.0    0.1      20.7    2.6
            81          +65.1   10/10     179.8    8.0       6.4    0.5       7.2    0.7      57.5    3.2
            88          +63.0    9/10     168.0    8.0      23.7    1.6       0.0    0.0     120.2    3.6
```
用 exp18 的訓練種子對 exp18 和 17 測試，可以觀察到在沒有訓練的種子上exp17表現得略差，除此之外沒有明顯區別。

使用 exp18 表現很差的 10009 種子進行觀察(tools.watch)，發現 exp18 表現差的主因有二：
1.agent經常從右上角的一處較大但極遠的銅礦開始建築，忽略核心上方一處較近的銅礦，導致更容易因為沒有銅而蓋不了傳送帶
2.就算有預算排好傳送帶的藍圖，因為右上角的銅礦離核心很遠，導致連接核心和礦機的傳送帶很長，需要大量銅礦，而且有一段不在 agent 的建築範圍內。
這時因為 build 跟 place 不需要排預算，agent會繼續建造別的東西，使得資源提前耗盡，傳送帶無法建成，也就無法回收銅礦，導致該局失敗。

目前想到幾種辦法：
1.讓 place / build 也套用同樣的預算檢查，這樣可以避免預算衝突，但無法解決超出預算範圍的問題。
2.強制 agent 跟著 link 出來的傳送帶走一趟，大幅降低預算被先花完的風險，也更符合人類玩家的習慣，這樣如同原專案的 link ，演算法干預過大，AI 無法有效學習。
3.新增「飛到最近的藍圖」動作，由 agent 決定何時使用。干預比第二項小，但會多一個動作，exp18 的權重要擴充才能接續訓練。












exp19-control（exp18 + 1M 步，無 free_copper）兩次評估為 82、80，比 exp18（約 97）明顯退化。exp19-2（相同起點與步數，加入 free_copper）在 main 上四次評估為 104、105、97、104，兩次與 control 同場比較分別多 17、22 勝（合併 201/300 vs 162/300，約 3.4σ）。free_copper 能避免長時間訓練的退化，但與 exp15 仍無法區分（104 vs 103）。30 張地圖只是延後了退化的發生。

---

## 第七次測試 1000000步
 
**主要嘗試** 增加一個地圖通道 free-copper ，內容是核心剩下的銅 - 藍圖預定的銅，預計看到 agent 行為差異，從 exp18 接續實驗，與對照組訓練一百萬步測試成效。

**獎勵設計** 同上

 
**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,48,91,33,62,36,3,8,9,11,17,56,26,92,52,47,4,5,12,13,18,42,29,21,81,88 --steps 1000000 --out checkpoints/exp19
**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,48,91,33,62,36,3,8,9,11,17,56,26,92,52,47,4,5,12,13,18,42,29,21,81,88 --steps 1000000 --out checkpoints/exp19-control


**測試指令** python -m tools.evaluate checkpoints/exp19/beta.pt checkpoints/exp19-control/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4
```
    exp19/beta  reward  +50.976 +-20.416  worst   +0.048  wave  1.00  built  157.1  produced    199.6  solved 97/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 67%
            copper   machine   128.9  hand    26.0 ( 17% by hand) | drills   7.9  connected  69%  running  68%

            seed       reward  solved      copper
                                        machine drills
            10002       +66.8   10/10     200.2    7.8
            10003       +59.8    9/10     169.4    8.0
            10004       +66.5   10/10     197.6    8.3
            10005       +68.8    9/10     196.2   12.2
            10013       +68.1   10/10     200.6    7.9
            10006       +25.6    3/10      46.4    5.3
            10007       +65.9   10/10     181.0    8.0
            10008       +51.9    4/10      70.3   10.8
            10009       +31.3    1/10      16.2    7.5
            10010       +36.0    2/10     111.2    4.2
            10001       +48.8    7/10     121.5    8.0
            10011       +57.3    7/10     169.3    5.8
            10017       +31.7    3/10      46.0   11.7
            10024       +25.2    2/10      33.3    6.6
            10026       +60.9   10/10     173.7    6.1
    exp19-control/beta  reward  +45.797 +-22.863  worst   +0.036  wave  1.00  built  152.7  produced    232.3  solved 80/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 90% | first_turret 6%
            copper   machine   118.6  hand    22.2 ( 16% by hand) | drills   6.5  connected  64%  running  62%

            seed       reward  solved      copper
                                        machine drills
            10002       +64.9   10/10     197.0    5.8
            10003       +61.8   10/10     178.7    8.1
            10004       +68.0   10/10     197.8    6.9
            10005       +25.1    1/10      28.0   13.9
            10013       +68.1   10/10     198.2    8.3
            10006       +44.7    5/10     108.8    4.6
            10007       +65.5    9/10     159.1    8.1
            10008       +30.5    2/10      55.6    9.1
            10009       +36.2    3/10      63.4    5.0
            10010       +19.8    0/10      45.5    6.2
            10001       +54.6    5/10     157.0    4.6
            10011       +49.7    6/10     137.0    5.0
            10017       +26.5    2/10      55.3    4.7
            10024       +18.5    1/10      41.8    2.5
            10026       +53.1    6/10     155.1    5.2
```
exp19（相同起點與步數，加入 free_copper）評估為 97，與 control 同場比較多 17 勝，差距約 2.1 個標準差，表現相對穩定，但沒有高於先前的實驗。

**測試指令** python -m tools.evaluate checkpoints/exp19/beta.pt checkpoints/exp15/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4

```
    exp19/beta  reward  +52.916 +-21.169  worst   +0.002  wave  1.00  built  155.6  produced    208.0  solved 104/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 66%
            copper   machine   135.7  hand    27.5 ( 17% by hand) | drills   7.9  connected  70%  running  69%

            seed       reward  solved      copper
                                        machine drills
            10002       +68.1   10/10     200.6    7.6
            10003       +59.5   10/10     179.2    8.4
            10004       +65.4   10/10     197.7    8.3
            10005       +73.1    9/10     200.1   12.2
            10013       +70.0   10/10     200.3    7.8
            10006       +23.2    4/10      38.2    5.0
            10007       +62.1    9/10     173.0    7.7
            10008       +52.8    4/10     100.6    9.7
            10009       +32.4    3/10      45.4    7.4
            10010       +47.9    4/10     153.6    4.6
            10001       +46.3    5/10      97.6    8.4
            10011       +63.8   10/10     179.3    6.2
            10017       +46.2    5/10      74.8    9.7
            10024       +20.1    2/10      19.7    8.1
            10026       +62.8    9/10     176.0    6.7
    exp15/beta  reward  +50.505 +-19.956  worst   +5.127  wave  1.00  built  144.2  produced    197.8  solved 103/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 62% | first_turret 2%
            copper   machine   126.8  hand    44.1 ( 26% by hand) | drills   9.3  connected  62%  running  66%

            seed       reward  solved      copper
                                        machine drills
            10002       +61.6   10/10     177.0   10.0
            10003       +56.5   10/10     162.6    8.3
            10004       +63.2   10/10     179.8   10.3
            10005       +72.9   10/10     200.7   13.5
            10013       +58.9   10/10     163.7    9.6
            10006       +53.5    9/10     141.9    6.3
            10007       +53.9    9/10     143.7   10.5
            10008       +55.6    6/10     108.3   11.2
            10009       +33.7    2/10      62.7    7.9
            10010       +28.5    2/10      24.2   14.9
            10001       +28.5    2/10      59.7    8.5
            10011       +57.1    8/10     138.7    6.9
            10017       +39.5    3/10      92.2    8.1
            10024       +29.2    3/10      67.4    6.7
            10026       +65.0    9/10     179.7    7.1
```
**結論 ：** free_copper 能延長訓練的退化時間，但與 exp15 仍無法區分（104 vs 103）。30 張地圖只是延後了退化的發生。

---

## 第八次測試 300000步
 
**主要嘗試** 改變 connected 的判定時機，原本鑽頭要挖超過 10 個才算接通，現在每 step 都會檢查，只要鑽頭的礦有路線通到會消耗它的地方 (核心、工廠、砲塔) 就算接通。從 exp19 接續訓練三十萬步以測試成效，對照組使用 exp19。

**獎勵設計* 同上

**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,48,91,33,62,36,3,8,9,11,17,56,26,92,52,47,4,5,12,13,18,42,29,21,81,88 --steps 300000 --out checkpoints/exp20

**測試指令** python -m tools.evaluate checkpoints/exp19/beta.pt checkpoints/exp20/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026 --envs 4
```
    exp19/beta  reward  +52.915 +-19.057  worst   +0.007  wave  1.00  built  161.1  produced    205.1  solved 104/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 75% | first_turret 1%
            copper   machine   135.9  hand    33.6 ( 20% by hand) | drills   8.3  connected  67%  running  67%
            lead     machine     3.8  hand     8.1 ( 68% by hand) | drills   0.7  connected  34%  running  46%
            sand     machine    55.9  hand    39.3 ( 41% by hand) | drills   2.1  connected  75%  running  79%

            seed       reward  solved      copper            lead             sand      
                                        machine drills   machine drills   machine drills
            10002       +68.2    9/10     199.1    8.0       0.0    0.0     112.8    3.6
            10003       +64.6   10/10     190.0    7.9       1.6    0.1     138.0    4.3
            10004       +67.4   10/10     200.7    8.0       0.3    0.1      95.1    3.8
            10005       +65.3    8/10     180.3   12.5       1.1    0.2      11.1    0.9
            10013       +69.3   10/10     200.5    8.1       2.1    0.2      71.4    3.2
            10006       +33.0    6/10      73.8    5.1      15.6    1.8      50.4    1.5
            10007       +64.3   10/10     180.9    8.5       0.4    0.2      29.6    1.6
            10008       +38.7    2/10      55.5   12.9      11.4    0.9       0.0    0.5
            10009       +29.3    1/10      35.4    8.2      13.6    2.9       3.6    0.5
            10010       +52.8    7/10     159.0    5.1       0.0    0.0     117.6    2.4
            10001       +44.7    7/10     103.7    8.4       0.0    0.6     112.0    3.4
            10011       +64.1    8/10     183.1    6.3       0.0    0.0      55.3    1.6
            10017       +47.3    7/10     101.2   11.0       4.6    1.4       0.0    1.2
            10024       +29.1    1/10      19.2    7.4       6.0    0.7      21.9    1.5
            10026       +55.7    8/10     155.7    7.5       0.6    0.7      20.2    1.8
    exp20/beta  reward  +52.489 +-21.188  worst   -2.068  wave  1.00  built  166.4  produced    227.8  solved 98/150  core tenu 100%
        first_drill 100% | first_conveyor 100% | first_wall 73%
            copper   machine   137.3  hand    22.6 ( 14% by hand) | drills   6.6  connected  77%  running  76%
            lead     machine     4.1  hand     1.9 ( 32% by hand) | drills   0.5  connected  37%  running  48%
            sand     machine    77.6  hand    54.7 ( 41% by hand) | drills   3.1  connected  70%  running  67%

            seed       reward  solved      copper            lead             sand      
                                        machine drills   machine drills   machine drills
            10002       +66.8   10/10     200.6    7.0       0.0    0.0     124.4    4.0
            10003       +59.6    8/10     167.7    7.7       0.0    0.0     152.5    4.7
            10004       +66.9   10/10     196.3    6.7       4.6    0.7      97.6    4.3
            10005       +74.7   10/10     200.5    9.9       0.0    0.0       0.0    0.0
            10013       +68.3   10/10     200.0    7.0      36.8    1.6      48.6    1.7
            10006       +55.4    9/10     137.8    5.5       0.0    0.0     129.0    4.7
            10007       +57.4    9/10     140.9    8.0       0.0    0.0      38.3    1.7
            10008       +43.7    3/10     106.0    5.3       0.4    0.3      66.8    1.6
            10009       +40.1    0/10      51.7    7.9      14.9    0.5      12.2    0.2
            10010       +49.0    3/10     137.8    7.0       0.0    0.1      87.2    2.0
            10001       +57.8    7/10     154.0    5.3       0.0    0.0     234.5    6.4
            10011       +55.6    7/10     146.9    5.0       0.0    0.0      60.9    2.5
            10017        +2.4    0/10       0.0    2.2       0.0    2.6      25.9    8.4
            10024       +31.6    3/10      55.6    8.6       3.7    1.1      19.4    1.9
            10026       +58.0    9/10     163.9    6.0       1.7    0.2      67.3    2.8
```
**結論 ：** 沒有顯著差別，少的 6 勝全部來自 10017 (7/10 → 0/10)，這張圖上 AI 幾乎只蓋沙與鉛鑽頭，產銅為 0。每局 link 因 can't afford 被拒絕的次數仍有 23–30 次，訓練獎勵也沒有上升，先把銅花在鑽頭上、付不起線的問題沒有解決。

