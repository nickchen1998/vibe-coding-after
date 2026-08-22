"""第 4 章：擬真模擬——思考時間、權重、生命週期。

本檔整合三個主題，示範如何讓虛擬使用者更像真人：
- wait_time：思考時間，模擬人類閱讀頁面的停頓。
- @task(權重)：以 80/20 法則分配行為比例。
- on_start / on_stop：使用者生命週期的開場與收尾（登入／登出）。

啟動（先讓 target_app 跑在 8000）：
    locust -f locustfile.py --host http://127.0.0.1:8000 \
           --headless --users 50 --spawn-rate 10 --run-time 30s
"""
from locust import HttpUser, task, between


class RealisticUser(HttpUser):
    """一位行為貼近真人的虛擬使用者。"""

    # 思考時間：每個動作之間隨機停頓 1–3 秒，模擬人類閱讀頁面。
    wait_time = between(1, 3)

    def on_start(self):
        """使用者「上線」時執行一次：登入並保存 token。"""
        response = self.client.post("/login")
        self.token = response.json().get("token")

    def on_stop(self):
        """使用者「下線」時執行一次：登出。"""
        self.client.post("/logout")

    # ── 以下用 80/20 法則分配行為權重 ──

    @task(8)
    def browse(self):
        """瀏覽商品：最常見的行為，佔約八成流量。"""
        self.client.get("/items/42", name="/items/[id]")

    @task(2)
    def do_checkout(self):
        """結帳：較少見的行為，佔約兩成流量。"""
        self.client.get("/checkout")
