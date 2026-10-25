# 實驗紀錄(T1_Copper)
**勝利條件** 從本局開始450次step內，有一步核心擁有250個copper即為勝利。
 
## 第一次測試 300000步
 
**主要嘗試** 專案原始參數
 
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after) + _carrying(0.002)(before, after)
),
```
 
**對訓練完的模型25次測試結果**
 
```
beta  reward   +2.891 +- 2.984  worst   +1.508  wave  1.00  built    1.7  produced      0.0  solved 3/25  core tenu 100%  over 1 unseen sectors
              first_drill 4% | first_conveyor 96%
```
 
**結論**  AI只會手動挖礦，並且挖的多是沙子 因為沙子比銅礦常見許多
 
---
 
## 第二次測試 300000步
 
**主要嘗試** 降低沙子的價值 0.3 > 0.1
 
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after) + _carrying(0.002)(before, after)
),
```
 
**對訓練完的模型5次測試結果**
 
```
beta  reward   +0.440 +- 0.129  worst   +0.328  wave  1.00  built    1.2  produced      0.2  solved 0/5  core tenu 100%  over 1 unseen sectors
              first_drill 20% | first_conveyor 100% | first_wall 40% | first_turret 40%
```
 
**結論**  沒有變化
 
---
 
## 第三次測試 300000步
 
**主要嘗試** 增加放置鑽頭的獎勵，鑽頭獲得礦物就加分(drilled)，鑽頭放對位置就加分(drill_tile)
 
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
    _throughput("copper", 0.01)(before, after)
    + _carrying(0.002)(before, after)
    + _drilled("copper", 0.1)(before, after)
    + _drill_tiles("copper", 0.25)(before, after)
),
```
 
**對訓練完的模型25次測試結果**
```
beta  reward   +7.245 +- 9.393  worst   -1.904  wave  1.00  built   43.5  produced     69.1  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 68% | first_turret 8% 
```
**結論** 出現有趣的現象：對於AI來說建鑽頭的收益現為正，因此可以看到大量的鑽頭，但AI對傳送帶非常吝嗇 會為了運送一個銅，反覆建傳送帶到核心，然後刪除傳送帶。獎勵高的回合主要原因是核心旁有大量銅礦，廣建鑽頭以後能輕易送回核心，獎勵大約能到50，附近沒有銅礦的回合則在0徘徊(附近沒有方便取得的銅礦)。壞消息是，因為AI反覆刪除傳送帶和蓋一堆鑽頭的行為，核心庫存的200銅礦幾乎歸零，無法達成勝利條件。
 
**衍生問題**
 
1. 是否應該固定世界種子，使礦藏資源固定?
2. 實際在遊玩遊戲時，人類玩家獲取資源是為了花費資源，而強化學習幾乎無法理解這個過程，只能往囤積和花光兩個極端

 ---

 ## 第四次測試 300000步
 
**主要嘗試** 增加專案中設定好的torn (拆除自己建造的建築) 和 churn (蓋完馬上拆除) 懲罰
 
**成功獎勵** 10.0
 
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
**對訓練完的模型25次測試結果**
```
    beta  reward  +14.469 +-17.054  worst   -1.988  wave  1.00  built   92.4  produced    267.4  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 28%
              
```
**結論** 刪除傳送帶的情形經過確認，是原先專案的顯示問題，實際上並沒有這回事。沒有solve的情形，主要是因為AI不喜歡囤積資源，這也跟第三次測試的衍伸問題對應到：希望AI囤積，就會導致行為消極，鼓勵AI花費，就無法累積存量。

---

 ## 第五次測試 300000步
 
**主要嘗試** 增加以傳送帶運送資源至核心的獎勵(produced_gain)
 
**成功獎勵** 10.0
 
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
**結論** 沒有改善花光錢的問題，目測有更多連接中的傳送帶，沒有經過驗證，但這是好現象。另外觀察到建造傳送帶的演算法中，有些路徑會被深水所阻擋，會在下一次實驗前修改，預期實驗結果會變好一些，但不會太多。


---

 ## 第六次測試 300000步
 
**主要嘗試** 修正connect跨越深水的判定，增加有傳送帶鑽頭的獎勵。修正了換局時鑽頭追蹤沒清空的 bug。當鑽頭產出第11個礦時，視同鑽頭有接通，並給予_connected_drill_tiles獎勵
 
**成功獎勵** 10.0
 
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
**對訓練完的模型25次測試結果**
```
    beta  reward  +43.648 +-39.625  worst   -2.048  wave  1.00  built  172.2  produced    473.3  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 40% | first_turret 4%      
```
**結論：** 沒有改善花光錢的問題，感覺方向有點問題，目前獎勵也過高了。檢查訓練過程以後，發現在原版的 connect method 中有更多問題，演算法最多會挑中六個鑽頭，卻只會蓋一條離核心最近的傳送帶，而AI很難意是到這樣有什麼問題，這也同時反映出巨集動作對訓練的缺點：資料顯示AI極少使用 place 擺放單個方塊，總是使用 connect 巨集來挖礦。下一步會先改善演算法，使其回歸一個鑽頭對一傳送帶的模式，與之同時，會加入累進制獎勵，對鑽頭的持續產出給予越來越多的獎勵。目前的獎勵途徑太多而缺少懲罰，第八次開始會考慮使用消融或增加懲罰。

---

 ## 第七次測試 300000步
 
**主要嘗試** 獎勵鑽頭持續產出礦物的行為，隨生產數量逐漸增加獎勵，前5個礦物 0.05點/個 第6~10個 給0.1點/個 第11~15個 給0.15點/個(_drilled_tiered)。同時，改進evaluate腳本，現在會顯示各個礦物的獲取量，以及鑽頭接通和持續產出的比例。
 
**成功獎勵** 10.0
 
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
**對訓練完的模型25次測試結果**
測試指令：.venv\Scripts\python -m tools.evaluate checkpoints/exp07/beta.pt --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp07/eval.json
```
    beta  reward  +32.068 +-37.745  worst   -2.040  wave  1.00  built  142.1  produced    440.2  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 88% | first_turret 16%
              copper   machine    82.3  hand    11.2 ( 12% by hand) | drills   1.8  connected  93%  running  84%
              lead     machine    74.8  hand     9.0 ( 11% by hand) | drills   1.7  connected  91%  running  79%
              sand     machine   245.9  hand   141.2 ( 36% by hand) | drills   4.8  connected  87%  running  74%
              coal     machine    37.3  hand     0.0 (  0% by hand) | drills   1.2  connected  86%  running  79%
      random  reward  +14.978 +-27.641  worst  -19.186  wave  1.00  built  109.6  produced    253.6  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 96% | first_conveyor 100% | first_wall 88% | first_turret 84%
              copper   machine    42.2  hand     8.4 ( 17% by hand) | drills   1.2  connected  90%  running  70%
              lead     machine    48.9  hand     5.1 (  9% by hand) | drills   1.0  connected  92%  running  72%
              sand     machine   118.3  hand    21.7 ( 16% by hand) | drills   1.9  connected  83%  running  79%
              coal     machine    44.2  hand     0.0 (  0% by hand) | drills   1.0  connected  92%  running  71%
```
**結論** 沒有改善花光錢的問題。

---

 ## 第八次測試 300000步
 
**主要嘗試** 刪除_produced_gain _connected_drill_tiles 兩個獎勵，因為這些獎勵的性質跟_drilled_tiered很像，在先前的實驗中也沒有獲得明顯好處。
 
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
        _throughput("copper", 0.01)(before, after)
        + _carrying(0.002)(before, after)
        + _drilled("copper", 0.1)(before, after)
        + _drill_tiles("copper", 0.25)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.05), (6, 0.1), (11, 0.15)])(before, after)
    ),
```
**對訓練完的模型25次測試結果** 
測試指令：.venv\Scripts\python -m tools.evaluate checkpoints/exp08/beta.pt checkpoints/exp07/beta.pt --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp08/compareto07.json
```
    exp08/beta  reward  +24.463 +-28.717  worst   -1.944  wave  1.00  built  147.5  produced    382.4  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 48%
              copper   machine    54.7  hand     9.9 ( 15% by hand) | drills   1.7  connected  86%  running  69%
              lead     machine    76.3  hand    17.6 ( 19% by hand) | drills   1.7  connected  86%  running  77%
              sand     machine   210.4  hand   110.7 ( 34% by hand) | drills   3.9  connected  84%  running  76%
              coal     machine    41.0  hand     0.0 (  0% by hand) | drills   0.9  connected  96%  running  86%
    exp07/beta  reward  +39.639 +-41.345  worst   -2.082  wave  1.00  built  151.5  produced    365.1  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 76% | first_turret 40%
              copper   machine    95.4  hand     6.3 (  6% by hand) | drills   2.3  connected  95%  running  82%
              lead     machine    59.2  hand     4.8 (  8% by hand) | drills   1.4  connected  94%  running  77%
              sand     machine   153.2  hand   136.5 ( 47% by hand) | drills   3.5  connected  84%  running  73%
              coal     machine    57.3  hand     0.0 (  0% by hand) | drills   1.4  connected  91%  running  77%
    random  reward  +13.564 +-29.919  worst  -10.900  wave  1.00  built  114.2  produced    207.5  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 88% | first_turret 92%
              copper   machine    43.6  hand     5.1 ( 10% by hand) | drills   0.9  connected  91%  running  74%
              lead     machine    38.0  hand     6.1 ( 14% by hand) | drills   0.9  connected  91%  running  61%
              sand     machine    95.5  hand    22.8 ( 19% by hand) | drills   2.0  connected  82%  running  67%
              coal     machine    30.4  hand     0.0 (  0% by hand) | drills   1.0  connected  88%  running  60%
```
**結論** 沒有改善花光錢的問題，經檢查發現在訓練過程中entropy始終降不下來，代表實際上AI一直在隨機決策，少有學習成果，整個訓練需要有大方向的改革。

---

 ## 第九次測試
**主要嘗試** 原先的connect是在AI選定了一個位置後，以那為中心的大塊正方形範圍內，選擇一個價值最高的2*2礦脈，蓋下鑽頭，並在鄰接格接上傳送帶通到核心，大部分過程皆由演算法處理，AI沒有介入。改動後將由AI自行選擇放置的位置，再由Astar演算法接上傳送帶。預期看到獎勵降低或銅礦產量降低。
**結果** 觀察到AI開始使用place擺放單個鑽頭，但不用connect擺放連接到核心的鑽頭，訓練中途暫停，沒有evaluate數據。

**主要嘗試** 將connect拆解為drill(代替place和connect裡擺放鑽頭的部分) 和link(連接尚未接上傳送帶的鑽頭)動作
**結果** AI行為退化，在整局過程中只會使用mine 和 move，訓練中途暫停，沒有evaluate數據。

**主要嘗試** 刪除thoughput，儘管thoughput與最終目標相關，但thoughput對於放置傳送帶的懲罰非常直觀，可能導致上述行為。減少carrying獎勵。增加tiered獎勵。增加copper lead 的drill_tile獎勵
**結果** 沒有改善AI的行為退化，推測是隨機種子，導致AI無法在行為崩潰前，學到在銅礦上擺放鑽頭，但固定種子會加劇AI過擬合的情況，會先進行測試。

**主要嘗試** 修改訓練程序，固定世界種子為10000，這樣一來一局內的所有資訊都會是固定的，預期看到獎勵增加，但無法在其他世界種子中維持同樣的表現。
**結果** 獎勵回升，AI開始學習如何擺放鑽頭，跟連接哪一個鑽頭至核心。


**主要嘗試** 接續訓練，總計 1000000 step ， 預計看到獎勵進一步提升。
 
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
        _carrying(0.001)(before, after)
        + _drill_tiles("copper", 0.25)(before, after)
        + _drill_tiles("lead", 0.05)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.1), (6, 0.15), (11, 0.3)])(before, after)
    ),
```

 **對訓練完的模型25次測試結果** 
```
測試指令：.venv\Scripts\python -m tools.evaluate checkpoints/exp09/beta.pt --seed 10000 --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp09/eval.json                
    beta  reward  +83.172 +-24.929  worst  +43.355  wave  1.00  built  213.0  produced    708.0  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 88% | first_turret 8%
              copper   machine   259.0  hand    19.1 (  7% by hand) | drills   7.5  connected  62%  running  80%
              lead     machine    47.3  hand    17.5 ( 27% by hand) | drills   3.6  connected  42%  running  70%
              sand     machine   399.4  hand    25.0 (  6% by hand) | drills   6.4  connected  97%  running  98%
              coal     machine     2.3  hand     0.0 (  0% by hand) | drills   0.6  connected  13%  running  60%
    random  reward   -0.672 +- 2.690  worst   -8.954  wave  1.00  built   29.8  produced      5.6  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 100% | first_turret 96%
              copper   machine     0.0  hand     3.4 (100% by hand) | drills   0.4  connected  18%  running   0%
              lead     machine     0.0  hand     4.6 (100% by hand) | drills   0.9  connected   4%  running   4%
              sand     machine     5.6  hand    36.1 ( 86% by hand) | drills   2.9  connected  11%  running   6%
              coal     machine     0.0  hand     0.0 (  0% by hand) | drills   0.0  connected   0%  running   0%
```
**測試指令** .venv\Scripts\python -m tools.evaluate checkpoints/exp09/beta.pt --seed 1 --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp09/eval.
```
json                
    beta  reward   +9.650 +-11.793  worst   +0.008  wave  1.00  built  123.0  produced    533.1  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 24%
              copper   machine    31.1  hand     8.2 ( 21% by hand) | drills   0.8  connected  90%  running  90%
              lead     machine     4.6  hand    18.9 ( 80% by hand) | drills   0.4  connected  70%  running  60%
              sand     machine   493.8  hand    26.2 (  5% by hand) | drills   8.3  connected  98%  running  97%
              coal     machine     3.6  hand     0.0 (  0% by hand) | drills   0.1  connected 100%  running 100%
    random  reward   -0.434 +- 1.600  worst   -4.185  wave  1.00  built   27.4  produced      0.0  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 96% | first_conveyor 100% | first_wall 100% | first_turret 100%
              copper   machine     0.0  hand     9.6 (100% by hand) | drills   0.2  connected   0%  running   0%
              lead     machine     0.0  hand     5.6 (100% by hand) | drills   0.5  connected   8%  running   0%
              sand     machine     0.0  hand    28.9 (100% by hand) | drills   3.6  connected   3%  running   2%
              coal     machine     0.0  hand     0.0 (  0% by hand) | drills   0.3  connected   0%  running  14%
```
**結論** 如同預期的發生過擬合，AI依舊沒有學會到看到銅礦擺磚頭，而是去哪一個位置挖礦。

---

## 第十次測試 300000步
**主要嘗試** 接續exp09繼續訓練，更換世界種子為1，預期看到1的獎勵從低點攀升，即災難性遺忘現象。

  
**成功獎勵** 10.0
 
```python
succeeded=_delivered("copper", 250),
reward=lambda before, after: (
        _carrying(0.001)(before, after)
        + _drill_tiles("copper", 0.25)(before, after)
        + _drill_tiles("lead", 0.05)(before, after)
        + _torn(-0.1)(before, after)
        + _churn(-2.0)(before, after)
        + _drilled_tiered("copper", [(1, 0.1), (6, 0.15), (11, 0.3)])(before, after)
    ),
```
**對訓練完的模型25次測試結果** 
```
測試指令：.venv\Scripts\python -m tools.evaluate checkpoints/exp10/beta.pt --seed 1 --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp10/eval.json                
    beta  reward  +87.601 +-34.975  worst  +11.619  wave  1.00  built  215.0  produced    827.6  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 68% | first_turret 4%
              copper   machine   288.1  hand    14.6 (  5% by hand) | drills   7.0  connected  82%  running  82%
              lead     machine    14.2  hand    13.6 ( 49% by hand) | drills   1.7  connected  46%  running  51%
              sand     machine   513.2  hand    49.1 (  9% by hand) | drills   9.4  connected  93%  running  92%
              coal     machine    12.1  hand     0.0 (  0% by hand) | drills   1.0  connected  33%  running  67%
    random  reward   -0.434 +- 1.600  worst   -4.185  wave  1.00  built   27.4  produced      0.0  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 96% | first_conveyor 100% | first_wall 100% | first_turret 100%
              copper   machine     0.0  hand     9.6 (100% by hand) | drills   0.2  connected   0%  running   0%
              lead     machine     0.0  hand     5.6 (100% by hand) | drills   0.5  connected   8%  running   0%
              sand     machine     0.0  hand    28.9 (100% by hand) | drills   3.6  connected   3%  running   2%
              coal     machine     0.0  hand     0.0 (  0% by hand) | drills   0.3  connected   0%  running  14%
```
```
測試指令：.venv\Scripts\python -m tools.evaluate checkpoints/exp10/beta.pt --seed 10000 --task T1_copper --episodes 25 --items copper,lead,sand,coal --designs= --out checkpoints/exp10/eval.json                
    beta  reward   +6.323 +-10.147  worst   -1.789  wave  1.00  built   66.6  produced    586.8  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 16%
              copper   machine    16.8  hand    12.0 ( 42% by hand) | drills   0.9  connected  55%  running  59%
              lead     machine    22.5  hand    15.4 ( 41% by hand) | drills   1.6  connected  45%  running  48%
              sand     machine   547.5  hand    25.6 (  4% by hand) | drills  11.8  connected  70%  running  67%
              coal     machine     0.0  hand     0.0 (  0% by hand) | drills   0.0  connected   0%  running   0%
    random  reward   -0.672 +- 2.690  worst   -8.954  wave  1.00  built   29.8  produced      5.6  solved 0/25  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 100% | first_turret 96%
              copper   machine     0.0  hand     3.4 (100% by hand) | drills   0.4  connected  18%  running   0%
              lead     machine     0.0  hand     4.6 (100% by hand) | drills   0.9  connected   4%  running   4%
              sand     machine     5.6  hand    36.1 ( 86% by hand) | drills   2.9  connected  11%  running   6%
              coal     machine     0.0  hand     0.0 (  0% by hand) | drills   0.0  connected   0%  running   0%
```
**結論** 如同預期的發生遺忘現象。此時若是換回隨機種子，預期會發生像exp09的退化現象，從下次開始會改變--seed參數設定，重複輪流使用十幾個種子進行訓練。

## 第十一次測試 1500000步

**主要嘗試** 從exp09接續，使用9個種子隨機訓練。
  ┌──────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                   分組                   │                                  種子（括號是 24 格內的全銅位置數）                                   │
  ├──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 近（≥ 10，站在核心就看得到）             │ 1(11)、2(45)、6(20)、7(15)、10(12)、14(16)、15(21)、16(14)、19(14)、22(22)、25(10)、30(15)、10000(12) │
  ├──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 中（1～9，近處有一點，要蓋多就得往外走） │ 3(7)、8(8)、9(2)、11(9)、17(6)、24(4)、26(3)、28(7)                                                   │
  ├──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 遠（0，非出門不可）                      │ 4、5、12、13、18、20、21、23、27、29、42                                                              │
  └──────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────┘
  選出1,2,6,7,3,8,9,4,5做為種子清單

**訓練指令** python -m tools.train_beta --task T1_copper --seed 1,2,6,7,3,8,9,4,5 --envs 4 --steps 300000 --designs= --no-watch --out checkpoints/exp11

**結果** 沒有發生崩潰，平均獎勵維持在20左右

**主要嘗試** 接續，訓練120萬步。
**訓練指令** python -m tools.train_beta --task T1_copper --seed 1,2,6,7,3,8,9,4,5 --envs 4 --steps 1200000 --designs= --no-watch --save-every 100 --out checkpoints/exp12



**測試指令** python -m tools.evaluate checkpoints/exp12/beta.pt --task T1_copper --seed 10,15,19,17,24,28,12,18,42 --designs= --episodes 90 --out checkpoints/exp12/eval-test.json
```
    beta  reward  +17.503 +-21.231  worst   +0.000  wave  1.00  built   78.6  produced    181.4  solved 0/90  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 22% | first_turret 3%
              copper   machine    28.5  hand    11.9 ( 30% by hand) | drills   3.6  connected  42%  running  30%
              seed 10       reward  +60.356 (10 ep)  solved 0/10  copper machine   96.4 drills  9.5
              seed 15       reward  +34.543 (10 ep)  solved 0/10  copper machine   76.1 drills  4.8
              seed 19       reward   +3.642 (10 ep)  solved 0/10  copper machine    9.9 drills  0.4
              seed 17       reward  +21.759 (10 ep)  solved 0/10  copper machine   52.5 drills  3.4
              seed 24       reward  +13.627 (10 ep)  solved 0/10  copper machine   11.6 drills  4.2
              seed 28       reward   +3.872 (10 ep)  solved 0/10  copper machine    0.0 drills  1.4
              seed 12       reward   +8.422 (10 ep)  solved 0/10  copper machine    0.0 drills  4.5
              seed 18       reward   +7.655 (10 ep)  solved 0/10  copper machine    9.9 drills  2.8
              seed 42       reward   +3.650 (10 ep)  solved 0/10  copper machine    0.0 drills  1.1
    random  reward   +0.744 +- 3.716  worst   -4.244  wave  1.00  built   27.3  produced      6.1  solved 0/90  core tenu 100%  over 1 unseen sectors
              first_drill 99% | first_conveyor 100% | first_wall 96% | first_turret 99%
              copper   machine     1.7  hand     4.8 ( 74% by hand) | drills   0.6  connected   6%  running   6%
              seed 10       reward   +3.060 (10 ep)  solved 0/10  copper machine    7.8 drills  1.0
              seed 15       reward   +2.793 (10 ep)  solved 0/10  copper machine    7.8 drills  0.7
              seed 19       reward   -0.410 (10 ep)  solved 0/10  copper machine    0.0 drills  0.2
              seed 17       reward   +0.724 (10 ep)  solved 0/10  copper machine    0.0 drills  0.7
              seed 24       reward   -0.161 (10 ep)  solved 0/10  copper machine    0.0 drills  0.4
              seed 28       reward   -0.466 (10 ep)  solved 0/10  copper machine    0.0 drills  0.2
              seed 12       reward   +0.528 (10 ep)  solved 0/10  copper machine    0.0 drills  0.7
              seed 18       reward   +1.520 (10 ep)  solved 0/10  copper machine    0.0 drills  1.0
              seed 42       reward   -0.890 (10 ep)  solved 0/10  copper machine    0.0 drills  0.2
```
**測試指令** python -m tools.evaluate checkpoints/exp12/beta.pt --task T1_copper --seed 1,2,6,7,3,8,9,4,5 --designs= --episodes 90 --out checkpoints/exp12/eval-test.json
```
    beta  reward  +39.591 +-29.257  worst   +0.172  wave  1.00  built  107.1  produced    218.6  solved 0/90  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 34% | first_turret 4%
              copper   machine    73.6  hand    10.4 ( 12% by hand) | drills   6.8  connected  57%  running  37%
              seed 1        reward  +44.297 (10 ep)  solved 0/10  copper machine   65.2 drills  8.0
              seed 2        reward  +27.163 (10 ep)  solved 0/10  copper machine   70.2 drills  5.2
              seed 6        reward  +57.535 (10 ep)  solved 0/10  copper machine  154.5 drills  8.2
              seed 7        reward  +30.646 (10 ep)  solved 0/10  copper machine   42.1 drills  7.2
              seed 3        reward  +34.049 (10 ep)  solved 0/10  copper machine   69.8 drills  5.1
              seed 8        reward  +51.134 (10 ep)  solved 0/10  copper machine   88.1 drills  8.7
              seed 9        reward  +11.295 (10 ep)  solved 0/10  copper machine   18.9 drills  3.3
              seed 4        reward  +53.777 (10 ep)  solved 0/10  copper machine   84.3 drills  9.1
              seed 5        reward  +46.426 (10 ep)  solved 0/10  copper machine   69.7 drills  6.6
    random  reward   +0.036 +- 2.918  worst   -8.462  wave  1.00  built   28.3  produced     10.3  solved 0/90  core tenu 100%  over 1 unseen sectors
              first_drill 99% | first_conveyor 100% | first_wall 100% | first_turret 100%
              copper   machine     0.6  hand     7.1 ( 92% by hand) | drills   0.6  connected   4%  running   4%
              seed 1        reward   +1.137 (10 ep)  solved 0/10  copper machine    5.7 drills  0.9
              seed 2        reward   +0.350 (10 ep)  solved 0/10  copper machine    0.0 drills  0.8
              seed 6        reward   +0.473 (10 ep)  solved 0/10  copper machine    0.0 drills  1.0
              seed 7        reward   +0.503 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 3        reward   -0.299 (10 ep)  solved 0/10  copper machine    0.0 drills  0.4
              seed 8        reward   -1.140 (10 ep)  solved 0/10  copper machine    0.0 drills  0.1
              seed 9        reward   +0.024 (10 ep)  solved 0/10  copper machine    0.0 drills  0.5
              seed 4        reward   -0.883 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 5        reward   +0.161 (10 ep)  solved 0/10  copper machine    0.0 drills  1.0
```
**結論** 用訓練用的種子和沒有過的種子下場測試，比較兩者的表現，發現AI學習的成果有限，一到陌生的地圖表現就會下降，但比起下隨機指令的random來說還是有進步(random 和beta都使用同一套動作，差別只在選擇和時機)。

---

## 第十二次測試 1500000步

**主要嘗試** 從exp11繼續，增加為21個種子輪換，隨機訓練一百五十萬步。
**結果** AI行為退化，出現只蓋鑽頭賺取基本分的行為。訓練中途停止。


**主要嘗試** 從exp11繼續，增加為14個種子輪換(指令有誤，十五個參數中有一個數字重複，實際上只有14個不同的地圖)，隨機訓練一百五十萬步。

**訓練指令** python -m tools.train_beta --task T1_copper --seed 1,2,6,7,3,8,9,4,5,7,11,12,13,10,17 --envs 4 --steps 1500000 --designs= --no-watch --save-every 100 --out checkpoints/exp13         

**測試指令** python -m tools.evaluate checkpoints/exp13/beta.pt --task T1_copper --seed 1,2,6,7,3,8,9,4,5,11,12,13,10,17 --designs= --episodes 140 --out checkpoints/exp13/eval.json                                      
```
    beta  reward  +37.208 +-35.667  worst   -0.119  wave  1.00  built  126.8  produced    140.1  solved 5/140  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 4% | first_turret 1%
              copper   machine    68.2  hand    16.2 ( 19% by hand) | drills   5.7  connected  69%  running  44%
              seed 1        reward  +55.749 (10 ep)  solved 1/10  copper machine  114.7 drills  7.6
              seed 2        reward   +0.427 (10 ep)  solved 0/10  copper machine    0.0 drills  0.2
              seed 6        reward  +49.251 (10 ep)  solved 0/10  copper machine   54.5 drills  9.1
              seed 7        reward  +48.061 (10 ep)  solved 0/10  copper machine  101.3 drills  7.1
              seed 3        reward  +41.046 (10 ep)  solved 0/10  copper machine   95.6 drills  5.1
              seed 8        reward  +51.484 (10 ep)  solved 0/10  copper machine   91.7 drills  8.4
              seed 9        reward   +8.504 (10 ep)  solved 0/10  copper machine    3.9 drills  1.7
              seed 4        reward  +93.191 (10 ep)  solved 3/10  copper machine  183.6 drills 12.6
              seed 5        reward  +71.223 (10 ep)  solved 1/10  copper machine  182.7 drills  7.7
              seed 11       reward  +12.193 (10 ep)  solved 0/10  copper machine    0.0 drills  3.3
              seed 12       reward   +5.017 (10 ep)  solved 0/10  copper machine    0.0 drills  2.6
              seed 13       reward   +4.060 (10 ep)  solved 0/10  copper machine    1.4 drills  0.9
              seed 10       reward  +68.271 (10 ep)  solved 0/10  copper machine  124.1 drills  8.8
              seed 17       reward  +12.429 (10 ep)  solved 0/10  copper machine    1.5 drills  5.1
    random  reward   +0.234 +- 1.912  worst   -4.624  wave  1.00  built   27.4  produced      4.1  solved 1/140  core tenu 100%  over 1 unseen sectors
              first_drill 98% | first_conveyor 100% | first_wall 97% | first_turret 99%
              copper   machine     0.0  hand     6.2 (100% by hand) | drills   0.6  connected   5%  running   0%
              seed 1        reward   +0.390 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 2        reward   +0.920 (10 ep)  solved 0/10  copper machine    0.0 drills  1.0
              seed 6        reward   +1.052 (10 ep)  solved 0/10  copper machine    0.0 drills  0.9
              seed 7        reward   +0.628 (10 ep)  solved 0/10  copper machine    0.0 drills  0.7
              seed 3        reward   +0.201 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 8        reward   -0.419 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 9        reward   -0.672 (10 ep)  solved 0/10  copper machine    0.0 drills  0.1
              seed 4        reward   +0.794 (10 ep)  solved 1/10  copper machine    0.0 drills  0.1
              seed 5        reward   -0.068 (10 ep)  solved 0/10  copper machine    0.0 drills  0.5
              seed 11       reward   +0.367 (10 ep)  solved 0/10  copper machine    0.0 drills  0.9
              seed 12       reward   +0.463 (10 ep)  solved 0/10  copper machine    0.0 drills  0.8
              seed 13       reward   -0.115 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 10       reward   +0.248 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 17       reward   -0.507 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
```
**測試指令** python -m tools.evaluate checkpoints/exp13/beta.pt --task T1_copper --seed 10002,10003,10004,10013,10014,10006,10007,10008,10009,10010,10001,10011,10026,10042 --designs= --episodes 140 --out checkpoints/exp13/eval-test.json
```
    beta  reward  +20.747 +-24.981  worst   -0.100  wave  1.00  built  107.6  produced     97.8  solved 0/140  core tenu 100%  over 1 unseen sectors
              first_drill 100% | first_conveyor 100% | first_wall 6% | first_turret 1%
              copper   machine    27.4  hand     9.9 ( 27% by hand) | drills   3.7  connected  54%  running  33%
              seed 10002    reward   +3.938 (10 ep)  solved 0/10  copper machine    0.0 drills  1.2
              seed 10003    reward  +24.064 (10 ep)  solved 0/10  copper machine   32.0 drills  4.7
              seed 10004    reward  +52.456 (10 ep)  solved 0/10  copper machine   58.6 drills  6.9
              seed 10013    reward   +6.988 (10 ep)  solved 0/10  copper machine    0.0 drills  2.5
              seed 10014    reward  +14.221 (10 ep)  solved 0/10  copper machine   39.4 drills  1.8
              seed 10006    reward   +8.210 (10 ep)  solved 0/10  copper machine    0.0 drills  4.2
              seed 10007    reward  +40.476 (10 ep)  solved 0/10  copper machine   26.3 drills  8.9
              seed 10008    reward   -0.007 (10 ep)  solved 0/10  copper machine    0.0 drills  0.0
              seed 10009    reward  +36.919 (10 ep)  solved 0/10  copper machine   47.2 drills  4.3
              seed 10010    reward  +24.514 (10 ep)  solved 0/10  copper machine   44.2 drills  3.1
              seed 10001    reward  +10.471 (10 ep)  solved 0/10  copper machine    0.0 drills  5.7
              seed 10011    reward   +2.067 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 10026    reward   +4.039 (10 ep)  solved 0/10  copper machine    0.0 drills  1.2
              seed 10042    reward  +62.102 (10 ep)  solved 0/10  copper machine  135.3 drills  7.0
    random  reward   -0.064 +- 1.965  worst   -6.185  wave  1.00  built   26.4  produced      5.2  solved 0/140  core tenu 100%  over 1 unseen sectors
              first_drill 99% | first_conveyor 100% | first_wall 95% | first_turret 100%
              copper   machine     0.1  hand     4.7 ( 98% by hand) | drills   0.5  connected   4%  running   4%
              seed 10002    reward   -0.239 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 10003    reward   +1.970 (10 ep)  solved 0/10  copper machine    1.2 drills  1.2
              seed 10004    reward   -0.219 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 10013    reward   +0.154 (10 ep)  solved 0/10  copper machine    0.0 drills  0.4
              seed 10014    reward   -0.905 (10 ep)  solved 0/10  copper machine    0.0 drills  0.7
              seed 10006    reward   -0.262 (10 ep)  solved 0/10  copper machine    0.0 drills  0.4
              seed 10007    reward   +0.419 (10 ep)  solved 0/10  copper machine    0.0 drills  0.5
              seed 10008    reward   +0.407 (10 ep)  solved 0/10  copper machine    0.0 drills  0.7
              seed 10009    reward   -0.665 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 10010    reward   -0.607 (10 ep)  solved 0/10  copper machine    0.0 drills  0.5
              seed 10001    reward   -0.675 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
              seed 10011    reward   +0.160 (10 ep)  solved 0/10  copper machine    0.0 drills  0.4
              seed 10026    reward   -0.080 (10 ep)  solved 0/10  copper machine    0.0 drills  0.6
              seed 10042    reward   -0.347 (10 ep)  solved 0/10  copper machine    0.0 drills  0.3
```
**結論** AI在特定地圖上的表現幾乎為0，哪怕是一些銅礦較接近的地圖(10002、10013)，訓練種子中也有一些地圖，雖然被歸類在容易訓練，但實際表現很差(2)。

統計每個種子，AI在 reset 後的第一個 step：
  ┌──────┬─────────────┬─────────┬──────────┬───────────────┬───────────────────────┐
  │ 種子 │ eval reward │ P(move) │ P(drill) │ move 期望目標  │      視野內的銅        │ 
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 4    │ 93.2        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 75 格，平均 (−18, −13) │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┼
  │ 5    │ 71.2        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 沒有銅                 │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 10   │ 68.3        │ 0.800   │ 0.156    │ (+16.0, −2.2) │ 47 格，(+8, −6)        │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 1    │ 55.7        │ 0.801   │ 0.155    │ (+16.0, −2.2) │ 61 格，(−9, +6)        │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 8    │ 51.5        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 30 格，(−8, +5)        │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 6    │ 49.3        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 37 格，(−4, +7)        │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 7    │ 48.1        │ 0.797   │ 0.160    │ (+16.0, −2.2) │ 77 格，(−6, −2)        │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 3    │ 41.0        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 47 格，(+6, −14)       │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 17   │ 12.4        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 52 格，(−3, +10)       │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 11   │ 12.2        │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 67 格，(+11, −6)       │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 9    │ 8.5         │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 59 格，(+10, −17)      │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 12   │ 5.0         │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 45 格，(−7, +18)       │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 13   │ 4.1         │ 0.797   │ 0.160    │ (+16.0, −2.2) │ 93 格，(−2, −11)       │
  ├──────┼─────────────┼─────────┼──────────┼───────────────┼───────────────────────┤
  │ 2    │ 0.4         │ 0.796   │ 0.161    │ (+16.0, −2.2) │ 119 格，(−1, +3)       │
  └──────┴─────────────┴─────────┴──────────┴───────────────┴───────────────────────┘ 
  - 座標都是相對 unit 的 (dx, dy)，move 期望目標是在 move 遮罩內，對位置機率加權平均得到的落點。

  14 個種子 logit 最高的 5 格完全相同，依序是 (16,−2)、(16,−3)、(16,0)、(16,−1)、(15,0)。代表AI有一個固定開局：往同一個位置move，無視世界種子之間礦物位置的差別。

  檢查礦物的位置對於AI的決策差別有多大：
  
  - 拿種子 2 的開局當基準，其他種子和它比。
  - 每一層都算「相對差異」：‖該種子的矩陣 − 種子 2 的矩陣‖ ÷ ‖種子 2 的矩陣‖。例如 3% 代表這一層的數值整體變動了 3%。  - 不同種子的地形、核心、unit 位置都一樣，傳進 AI 的矩陣只差在礦物通道。另一個輸入 global 向量（14 個數：unit 座標、核心相對位置、身上和核心的物資等）在所有種子上完全相同。

  種子差異在網路裡怎麼傳遞（exp13，開局第一步）
  ┌──────┬──────────────────────┬─────────────────────┬─────────────┬───────────────────────┬───────────────┬────────────┬───────────────┬────────────────────┐
  │ 種子 │ 不同的格子（其中銅） │ ① 輸入地圖 14×48×48 │ ② global 14 │ ③ trunk 特徵圖 64×6×6 │ ④ 平均池化 64 │ ⑤ body 256 │ ⑥ type 機率 8 │ ⑦ 位置 logit 48×48 │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 1    │ 426（180）           │ 3.15%               │ 0%          │ 5.08%                 │ 5.01%         │ 1.25%      │ 0.96%         │ 0.59%              │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 7    │ 364（178）           │ 2.78%               │ 0%          │ 0.65%                 │ 0.68%         │ 0.18%      │ 0.16%         │ 0.086%             │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 13   │ 389（212）           │ 2.87%               │ 0%          │ 0.88%                 │ 0.90%         │ 0.23%      │ 0.22%         │ 0.12%              │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 12   │ 379（164）           │ 2.91%               │ 0%          │ 0.27%                 │ 0.26%         │ 0.042%     │ 0.020%        │ 0.019%             │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 4    │ 337（194）           │ 2.68%               │ 0%          │ 0.12%                 │ 0.097%        │ 0.010%     │ 0.004%        │ 0.012%             │
  ├──────┼──────────────────────┼─────────────────────┼─────────────┼───────────────────────┼───────────────┼────────────┼───────────────┼────────────────────┤
  │ 17   │ 360（171）           │ 2.76%               │ 0%          │ 0.12%                 │ 0.096%        │ 0.013%     │ 0.006%        │ 0.012%             │
  └──────┴──────────────────────┴─────────────────────┴─────────────┴───────────────────────┴───────────────┴────────────┴───────────────┴────────────────────┘

  深入了解發現一個BUG：大部分地圖通道在進網路前被縮小成 1/255
  bridge/src/mindustryai/net/ObservationEncoder.java:146-167 寫入各通道的值如下：
  ┌───────────────────────────────────────────┬────────┬─────────────────────────────┐
  │                   通道                    │ 存的值 │  net.py:144 除以 255 之後   │
  ├───────────────────────────────────────────┼────────┼─────────────────────────────┤
  │ solid、buildable、block、block_ally/enemy │ 1      │ 0.0039                      │
  ├───────────────────────────────────────────┼────────┼─────────────────────────────┤
  │ ore_copper 等礦物                         │ 1      │ 0.0039                      │
  ├───────────────────────────────────────────┼────────┼─────────────────────────────┤
  │ unit_ally/enemy                           │ 1～3   │ 0.004～0.012                │
  ├───────────────────────────────────────────┼────────┼─────────────────────────────┤
  │ block_health                              │ 0～255 │ 0～1.0                      │
  ├───────────────────────────────────────────┼────────┼─────────────────────────────┤
  │ global 的 14 個數                         │ —      │ 約 0～1（另外各自正規化過） │
  └───────────────────────────────────────────┴────────┴─────────────────────────────┘

  /255 原本是為了 0～255 的通道（例如 block_health）設計的，但地形、建築、礦物都只存 0 或 1。因此MAP轉換成spatial矩陣時，大部分數值的差異都減少255倍，導致地圖在AI的視角看起來都差不多，原始地圖其實相差 33～39%。

  **修正**
  
  只有 block_health 除以 255，其他通道維持 0/1。為了接續既有的訓練，載入舊 checkpoint 時，第一層卷積在旗標通道上的權重同時除以 255，讓輸出保持不變。實測 exp13 轉換前後，位置 logit 最大差 1.7e-5，type
  機率最大差 1.2e-7。

    以下是修正後的數值，剩下的權重要等待checkpoint的更新：
  ┌──────┬──────────────────────┬─────────┬────────┬────────┬─────────────┬──────────────┐
  │ 種子 │ 輸入地圖（新尺度）     │ ③ trunk │ ④ 池化 │ ⑤ body │ ⑥ type 機率  │ ⑦ 位置 logit │ 
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 1    │ 38.7%                │ 5.08%   │ 5.01%  │ 1.25%  │ 0.96%       │ 0.59%        │  
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 7    │ 34.1%                │ 0.65%   │ 0.68%  │ 0.18%  │ 0.16%       │ 0.086%       │
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 13   │ 35.2%                │ 0.88%   │ 0.90%  │ 0.23%  │ 0.22%       │ 0.12%        │
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 12   │ 35.7%                │ 0.27%   │ 0.26%  │ 0.042% │ 0.020%      │ 0.019%       │
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 4    │ 32.9%                │ 0.12%   │ 0.097% │ 0.010% │ 0.004%      │ 0.012%       │
  ├──────┼──────────────────────┼─────────┼────────┼────────┼─────────────┼──────────────┤
  │ 17   │ 33.9%                │ 0.12%   │ 0.096% │ 0.013% │ 0.006%      │ 0.012%       │
  └──────┴──────────────────────┴─────────┴────────┴────────┴─────────────┴──────────────┘

---

## 第十三次測試 1500000步

**主要嘗試** 從exp13繼續，15個種子輪換，訓練一百萬步。
