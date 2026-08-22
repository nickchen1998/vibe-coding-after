"""第 11 章｜對鐵人商城發動一場階梯式攻擊

兵力每 60 秒往上跳一階（10 → 30 → 60 → 100 人），模擬流量逐步湧入。
儀表板上因此會看到「流量爬升 → 連線池排隊 → 延遲惡化」的完整因果鏈。

啟動（靶場需先跑在 8000）：
    locust -f locustfile.py --host http://127.0.0.1:8000 --headless \
           --csv attack --csv-full-history
"""

import random

from locust import HttpUser, LoadTestShape, between, task


class ShopUser(HttpUser):
    wait_time = between(0.2, 0.6)

    @task(6)
    def browse_list(self):
        self.client.get("/products")

    @task(3)
    def view_product(self):
        sku = f"IRON-{random.randint(1, 20):03d}"
        self.client.get(f"/products/{sku}", name="/products/[sku]")

    @task(2)
    def checkout(self):
        with self.client.post("/checkout", catch_response=True) as resp:
            if resp.status_code == 500:
                resp.success()      # 那 5% 的金流失敗是刻意設計，不計入 Locust 失敗數


class StepLoadShape(LoadTestShape):
    """階梯式加壓：每 60 秒往上跳一階，讓連線池從游刃有餘走到不堪負荷。"""

    steps = [
        (60, 10),    # 0–60s：10 人，池子綽綽有餘
        (120, 30),   # 60–120s：30 人，開始有人排隊
        (180, 60),   # 120–180s：60 人，隊伍拉長
        (240, 100),  # 180–240s：100 人，池子徹底飽和
    ]

    def tick(self):
        run_time = self.get_run_time()
        for end_time, users in self.steps:
            if run_time < end_time:
                return (users, users)
        return None
