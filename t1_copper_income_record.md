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
**結論**  exp14/beta.pt在收入 200 銅的目標上，成功率達到了 87/150（58%)，並且作為測試的 15 個種子均沒有參與過訓練。成敗主要看種子，而且分得很清楚：被標注為困難的種子，雖然都有蓋鑽頭，但是送入核心的量為0，被標注為容易的種子，有些能拿到10/10的成功率，且鑽頭數量沒有比失敗的種子多，問題很可能出在link動作。

---

## 第二次測試 100000步
 
**主要嘗試** 將link動作中的 CONNECT_BUDGET改至 256 ，可覆蓋大部分的地圖，以100000步測試學習傾向
 
**獎勵設計** 同上

**訓練指令** python -m tools.train_beta --task T1_copper_income --seed 1,2,6,7,10,3,8,9,11,17,4,5,12,13,18 --steps 100000 --out checkpoints/exp15



**測試指令** python -m tools.evaluate checkpoints/exp15/beta.pt --task T1_copper_income --seed 10002,10003,10004,10005,10013,10006,10007,10008,10009,10010,10001,10011,10017,10024,10026
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
**結論**  exp14/beta.pt在收入 200 銅的目標上，成功率達到了 87/150（58%)，並且作為測試的 15 個種子均沒有參與過訓練。成敗主要看種子，而且分得很清楚：被標注為困難的種子，雖然都有蓋鑽頭，但是送入核心的量為0，被標注為容易的種子，有些能拿到10/10的成功率，且鑽頭數量沒有比失敗的種子多，問題很可能出在link動作。