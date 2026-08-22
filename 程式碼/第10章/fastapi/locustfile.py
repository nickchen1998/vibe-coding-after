"""第 10 章 10.1｜掛／不掛監控中介層的延遲對照壓測

兩組實驗除了「城門上有沒有守衛」之外，條件完全對等：
同一支 shop_api.py、同樣的端點權重、同樣的併發人數、同一台機器、緊接著跑。

執行（先起靶場，再開這一支）：
    # A 組：掛上守衛
    SHOP_MIDDLEWARE=on  uvicorn shop_api:app --host 127.0.0.1 --port 8000
    locust -f locustfile.py --headless -u 20 -r 20 -t 60s -H http://127.0.0.1:8000

    # B 組：拆掉守衛
    SHOP_MIDDLEWARE=off uvicorn shop_api:app --host 127.0.0.1 --port 8000
    locust -f locustfile.py --headless -u 20 -r 20 -t 60s -H http://127.0.0.1:8000
"""

import random

from locust import HttpUser, between, task


class ShopUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task(6)
    def browse_list(self):
        """逛商品列表：最常見的行為。"""
        self.client.get("/products")

    @task(3)
    def view_product(self):
        """看單品頁：路徑帶 SKU，統一歸到 /products/[sku] 這個名稱下統計。"""
        sku = f"IRON-{random.randint(1, 20):03d}"
        self.client.get(f"/products/{sku}", name="/products/[sku]")

    @task(1)
    def checkout(self):
        """結帳：最沉重、也最可能失敗的一條路。"""
        with self.client.post("/checkout", catch_response=True) as resp:
            if resp.status_code == 500:
                resp.success()   # 5% 的金流失敗是刻意設計，不計入 Locust 的失敗數
