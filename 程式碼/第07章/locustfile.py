"""第 7 章：鐵人商城高負載讀取壓測。

以環境變數 SCENARIO 切換讀取情境，方便對照：
- naive   ：N+1 查詢的熱門商品列表
- join    ：JOIN 優化的熱門商品列表
- shallow ：搜尋第 1 頁（淺層分頁）
- deep    ：搜尋第 5000 頁（深層分頁，OFFSET 99980）
- keyset  ：鍵集分頁跳到接近尾端（after_id=99980）
"""
import os

from locust import HttpUser, task, between

SCENARIO = os.getenv("SCENARIO", "naive")

_PATHS = {
    "naive":   "/products_naive?limit=30",
    "join":    "/products_join?limit=30",
    "shallow": "/search?page=1",
    "deep":    "/search?page=5000",
    "keyset":  "/search_keyset?after_id=99980",
}
_NAMES = {
    "naive":   "/products_naive",
    "join":    "/products_join",
    "shallow": "/search(淺層 p1)",
    "deep":    "/search(深層 p5000)",
    "keyset":  "/search_keyset(接近尾端)",
}


class Reader(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def read(self):
        self.client.get(_PATHS[SCENARIO], name=_NAMES[SCENARIO])
