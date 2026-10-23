# 實驗紀錄
 
## 第一次測試 300000步
 
**主要嘗試：** 專案原始參數
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after) + _carrying(0.002)(before, after)
),
```
 
**對訓練完的模型25次測試結果：**
 
```
beta  reward   +2.891 +- 2.984  worst   +1.508  wave  1.00  built    1.7  produced      0.0  solved 3/25  core tenu 100%  over 1 unseen sectors
              first_drill 4% | first_conveyor 96%
```
 
**結論：**  AI只會手動挖礦，並且挖的多是沙子 因為沙子比銅礦常見許多
 
---
 
## 第二次測試 300000步
 
**主要嘗試：** 降低沙子的價值 0.3 > 0.1
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after) + _carrying(0.002)(before, after)
),
```
 
**對訓練完的模型5次測試結果：**
 
```
beta  reward   +0.440 +- 0.129  worst   +0.328  wave  1.00  built    1.2  produced      0.2  solved 0/5  core tenu 100%  over 1 unseen sectors
              first_drill 20% | first_conveyor 100% | first_wall 40% | first_turret 40%
```
 
**結論：**  沒有變化
 
---
 
## 第三次測試 300000步
 
**主要嘗試：** 增加放置鑽頭的獎勵，鑽頭獲得礦物就加分(drilled)，鑽頭放對位置就加分(drill_tile)
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after)
    + _carrying(0.002)(before, after)
    + _drilled("copper", 0.1)(before, after)
    + _drill_tiles("copper", 0.25)(before, after)
),
```
 
**對訓練完的模型25次測試結果：**
```
beta  reward   +7.245 +- 9.393  worst   -1.904  wave  1.00  built   43.5  produced     69.1  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 68% | first_turret 8% 
```
**結論：** 出現有趣的現象：對於AI來說建鑽頭的收益現為正，因此可以看到大量的鑽頭，但AI對傳送帶非常吝嗇 會為了運送一個銅，反覆建傳送帶到核心，然後刪除傳送帶。獎勵高的回合主要原因是核心旁有大量銅礦，廣建鑽頭以後能輕易送回核心，獎勵大約能到50，附近沒有銅礦的回合則在0徘徊(附近沒有方便取得的銅礦)。壞消息是，因為AI反覆刪除傳送帶和蓋一堆鑽頭的行為，核心庫存的200銅礦幾乎歸零，無法達成勝利條件。
 
**衍生問題：**
 
1. 是否應該固定世界種子，使礦藏資源固定?
2. 實際在遊玩遊戲時，人類玩家獲取資源是為了花費資源，而強化學習幾乎無法理解這個過程，只能往囤積和花光兩個極端

 ---

 ## 第四次測試 300000步
 
**主要嘗試：** 增加專案中設定好的torn (拆除自己建造的建築) 和 churn (蓋完馬上拆除) 懲罰
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after)
    + _carrying(0.002)(before, after)
    + _drilled("copper", 0.1)(before, after)
    + _drill_tiles("copper", 0.25)(before, after)
    + _torn(-0.1)(before, after)
    + _churn(-2.0)(before, after)
),
 ```
**對訓練完的模型25次測試結果：**
```
    beta  reward  +14.469 +-17.054  worst   -1.988  wave  1.00  built   92.4  produced    267.4  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 28%
              
```
**結論：** 刪除傳送帶的情形經過確認，是原先專案的顯示問題，實際上並沒有這回事。沒有solve的情形，主要是因為AI不喜歡囤積資源，這也跟第三次測試的衍伸問題對應到：希望AI囤積，就會導致行為消極，鼓勵AI花費，就無法累積存量。

---

 ## 第五次測試 300000步
 
**主要嘗試：** 增加以傳送帶運送資源至核心的獎勵(produced_gain)
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after)
    + _carrying(0.002)(before, after)
    + _drilled("copper", 0.1)(before, after)
    + _drill_tiles("copper", 0.25)(before, after)
    + _torn(-0.1)(before, after)
    + _churn(-2.0)(before, after)
    + _produced_gain("copper", 0.1)(before, after)
),
```
**對訓練完的模型25次測試結果：**
```
    beta  reward  +28.788 +-37.158  worst   -2.000  wave  1.00  built  106.2  produced    338.2  solved 1/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 36%        
```
**結論：** 沒有改善花光錢的問題，目測有更多連接中的傳送帶，沒有經過驗證，但這是好現象。另外觀察到建造傳送帶的演算法中，有些路徑會被深水所阻擋，會在下一次實驗前修改，預期實驗結果會變好一些，但不會太多。


---

 ## 第六次測試 300000步
 
**主要嘗試：** 修正connect跨越深水的判定，增加有傳送帶鑽頭的獎勵。修正了換局時鑽頭追蹤沒清空的 bug。當鑽頭產出第11個礦時，視同鑽頭有接通，並給予_connected_drill_tiles獎勵
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after)
    + _carrying(0.002)(before, after)
    + _drilled("copper", 0.1)(before, after)
    + _drill_tiles("copper", 0.25)(before, after)
    + _torn(-0.1)(before, after)
    + _churn(-2.0)(before, after)
    + _produced_gain("copper", 0.1)(before, after)
    + _connected_drill_tiles("copper", 0.25)(before, after)
),
```
**對訓練完的模型25次測試結果：**
```
    beta  reward  +43.648 +-39.625  worst   -2.048  wave  1.00  built  172.2  produced    473.3  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 40% | first_turret 4%      
```
**結論：** 沒有改善花光錢的問題，感覺方向有點問題，目前獎勵也過高了。檢查訓練過程以後，發現在原版的 connect method 中有更多問題，演算法最多會挑中六個鑽頭，卻只會蓋一條離核心最近的傳送帶，而AI很難意是到這樣有什麼問題，這也同時反映出巨集動作對訓練的缺點：資料顯示AI極少使用 place 擺放單個方塊，總是使用 connect 巨集來挖礦。下一步會先改善演算法，使其回歸一個鑽頭對一傳送帶的模式，與之同時，會加入累進制獎勵，對鑽頭的持續產出給予越來越多的獎勵。目前的獎勵途徑太多而缺少懲罰，第八次開始會考慮使用消融或增加懲罰。

---

 ## 第七次測試 300000步
 
**主要嘗試：** 獎勵鑽頭持續產出礦物的行為，隨生產數量逐漸增加獎勵，前5個礦物 0.05點/個 第6~10個 給0.1點/個 第11~15個 給0.15點/個(_drilled_tiered)。同時，改進evaluate腳本，現在會顯示各個礦物的獲取量，以及鑽頭接通和持續產出的比例。
 
**成功獎勵：** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
        _throughput("copper", 0.01)(before, after)
        + _carrying(0.002)(before, after)
        + _drilled("copper", 0.1)(before, after)
        + _drill_tiles("copper", 0.25)(before, after)
        + _connected_drill_tiles("copper", 0.25)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _produced_gain("copper", 0.1)(before, after)
        + _drilled_tiered("copper", [(1, 0.05), (6, 0.1), (11, 0.15)])(before, after)
    ),
```
**對訓練完的模型25次測試結果：**
```
    beta  reward  +50.890 +-42.581  worst   -1.970  wave  1.00  built  175.7  produced    398.5  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 84% | first_turret 8%
              copper   machine   125.4  hand    12.1 (  9% by hand) | drills   2.7  connected  90%  running  79%
              lead     machine    57.4  hand    10.6 ( 16% by hand) | drills   1.0  connected  96%  running  84%
              sand     machine   166.7  hand   228.6 ( 58% by hand) | drills   3.2  connected  84%  running  78%
      random  reward  +11.828 +-20.309  worst  -12.662  wave  1.00  built  102.2  produced    182.9  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 92% | first_turret 84%
              copper   machine    35.0  hand     2.9 (  8% by hand) | drills   1.2  connected  83%  running  53%
              lead     machine    39.4  hand     3.2 (  8% by hand) | drills   1.0  connected  96%  running  64%
              sand     machine    95.1  hand    21.0 ( 18% by hand) | drills   2.1  connected  81%  running  60%
```
**結論：** 沒有改善花光錢的問題。







