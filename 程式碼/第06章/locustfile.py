"""第 6 章壓測腳本：以「集合點」製造瞬間爆量的秒殺搶購。

秒殺最凶險的特徵是「所有人在同一瞬間湧入」。我們用壓測領域「集合點
（Rendezvous Point）」的概念來近似：讓每位虛擬使用者零思考時間、一誕生就
全力搶購，並把生成速率（--spawn-rate）調到與使用者總數相同，使所有人在一秒
內全數到齊、同時開搶。每位買家只搶一次（送出一筆請求後 raise StopUser 退場），
如此「售出數」就直接等於「搶到的人數」，超賣與否一目了然。

以環境變數切換攻擊目標：
    TARGET=/buy_naive ：打錯誤版（讀→判斷→扣，非原子）
    TARGET=/buy_safe  ：打正確版（用鎖鎖住判斷＋扣減）
    TARGET=/buy_db    ：打資料庫版正解（條件式更新，6.3 登場）

啟動（先讓 target_app 跑在 8000，並先 POST /reset）：
    TARGET=/buy_naive locust -f locustfile.py --host http://127.0.0.1:8000 \
        --headless -u 200 -r 200 -t 5s
"""
import os

from locust import HttpUser, task, constant
from locust.exception import StopUser

TARGET = os.getenv("TARGET", "/buy_naive")   # /buy_naive、/buy_safe 或 /buy_db


class Shopper(HttpUser):
    wait_time = constant(0)          # 零思考時間：搶購場景就是要瞬間爆量

    @task
    def grab(self):
        # 每位買家只搶一次：送出一筆下單請求後立刻退場
        self.client.post(TARGET, name=TARGET)
        raise StopUser()
