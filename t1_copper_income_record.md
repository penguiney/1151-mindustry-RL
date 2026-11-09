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

