"""第 12 章｜品質門壓測腳本

前面各章的腳本跑完只會印一份戰報；這一支多做一件事——**在收工時依實測結果
決定結束碼**。結束碼是 0 就是綠燈、非 0 就是紅燈，於是這支腳本本身就成了
一道「過不了就擋下」的品質門，可以直接掛進任何一套 CI。

門檻由環境變數帶入，方便同一支腳本示範兩種結局：
    MAX_AVG_MS      平均回應時間上限（毫秒），預設 300
    MAX_FAIL_RATIO  失敗率上限（比例，0.05 即 5%），預設 0.05
    MAX_P95_MS      P95 延遲上限（毫秒），預設 800

執行：
    locust -f locustfile.py --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 30s
"""

import logging
import os
import random

from locust import HttpUser, between, events, task

MAX_AVG_MS = float(os.getenv("MAX_AVG_MS", 300))
MAX_FAIL_RATIO = float(os.getenv("MAX_FAIL_RATIO", 0.05))
MAX_P95_MS = float(os.getenv("MAX_P95_MS", 800))


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


@events.quitting.add_listener
def _(environment, **kw):
    """收工時的守門員：逐條檢查門檻，任一條不過就把結束碼設成 1。"""
    stats = environment.stats.total
    if stats.fail_ratio > MAX_FAIL_RATIO:
        logging.error(f"品質門未通過：失敗率 {stats.fail_ratio:.2%} 高於門檻 {MAX_FAIL_RATIO:.2%}")
        environment.process_exit_code = 1
    elif stats.avg_response_time > MAX_AVG_MS:
        logging.error(f"品質門未通過：平均回應時間 {stats.avg_response_time:.0f}ms 高於門檻 {MAX_AVG_MS:.0f}ms")
        environment.process_exit_code = 1
    elif stats.get_response_time_percentile(0.95) > MAX_P95_MS:
        logging.error(f"品質門未通過：P95 延遲 {stats.get_response_time_percentile(0.95):.0f}ms 高於門檻 {MAX_P95_MS:.0f}ms")
        environment.process_exit_code = 1
    else:
        logging.info(f"品質門通過：平均 {stats.avg_response_time:.0f}ms、"
                     f"P95 {stats.get_response_time_percentile(0.95):.0f}ms、"
                     f"失敗率 {stats.fail_ratio:.2%}")
        environment.process_exit_code = 0
