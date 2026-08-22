"""第 5 章實驗一：參數化 vs 快取作弊。

同一支邏輯，切換兩種取 id 的方式：
- FIXED 模式：永遠查同一個 product_id，第二次起全部命中快取（作弊）。
- RANDOM 模式：每次隨機一個 product_id，逼近真實的快取未命中率。

以環境變數 MODE 切換（fixed / random），預設 random。
"""
import os
import random

from locust import HttpUser, task, between

MODE = os.getenv("MODE", "random")

# 事先準備一批可用的商品 id（參數化的資料來源）。
PRODUCT_IDS = list(range(1, 5001))


class ProductUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def view_product(self):
        if MODE == "fixed":
            pid = 42                          # 永遠打同一個，命中快取
        else:
            pid = random.choice(PRODUCT_IDS)  # 隨機參數化，逼出快取未命中
        self.client.get(f"/products/{pid}", name="/products/[id]")
