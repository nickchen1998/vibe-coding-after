"""第 3 章：第一支 locustfile。

本檔示範 Locust 最核心的兩個概念：
- User：一個虛擬使用者。HttpUser 內建了一個會自動記錄統計數據的 HTTP client。
- task：使用者會執行的行為。以 @task 裝飾的方法會被 Locust 隨機挑選執行。

啟動方式（先讓 target_app 在 127.0.0.1:8000 運行）：
    互動式（開 Web UI）：
        locust -f locustfile.py --host http://127.0.0.1:8000
    無介面（headless，直接在終端機看結果）：
        locust -f locustfile.py --host http://127.0.0.1:8000 \
               --headless --users 50 --spawn-rate 10 --run-time 30s
"""
from locust import HttpUser, task, between


class ShopUser(HttpUser):
    """模擬一位逛示範商店的使用者。"""

    # 每執行完一個 task，隨機停頓 1–3 秒，模擬人類閱讀頁面的思考時間。
    wait_time = between(1, 3)

    @task(3)
    def view_item(self):
        """瀏覽商品：最常見的行為，權重設為 3。"""
        item_id = 42
        # name 參數把不同 item_id 的請求歸併成同一條統計，避免報表被灌爆。
        self.client.get(f"/items/{item_id}", name="/items/[id]")

    @task(1)
    def do_checkout(self):
        """結帳：較少發生的行為，權重設為 1。"""
        self.client.get("/checkout")

    def on_start(self):
        """每位虛擬使用者誕生時，先造訪一次首頁。"""
        self.client.get("/")
