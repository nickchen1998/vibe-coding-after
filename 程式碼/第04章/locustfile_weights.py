"""第 4 章 4.2 示範：三任務權重分配 5:3:2。

用來驗證「權重即機率」——瀏覽:搜尋:結帳＝5:3:2，
實測各端點的請求佔比應趨近 50% / 30% / 20%。

為了快速累積大樣本以觀察分佈，這裡刻意用 constant(0)（零思考時間），
純粹是為了「統計權重比例」，而非模擬真實負載——兩者目的不同。

三個任務另貼了 @tag 標籤，可用 --tags／--exclude-tags 單獨挑任務跑（4.2）：
    locust -f locustfile_weights.py --host http://127.0.0.1:8000 \
           --headless --users 20 --spawn-rate 20 --run-time 20s
    # 只跑結帳：
    locust -f locustfile_weights.py --tags checkout ...（其餘參數同上）
"""
from locust import HttpUser, task, tag, constant


class ShopperUser(HttpUser):
    """有三種行為的購物者，權重 5:3:2。"""

    wait_time = constant(0)  # 僅為快速累積樣本，非真實負載模型

    @tag("browse")
    @task(5)
    def browse(self):
        """瀏覽商品：權重 5，理論佔比 50%。"""
        self.client.get("/items/42", name="/items/[id]")

    @tag("search")
    @task(3)
    def search(self):
        """搜尋：權重 3，理論佔比 30%。"""
        self.client.get("/search?q=locust", name="/search")

    @tag("checkout")
    @task(2)
    def do_checkout(self):
        """結帳：權重 2，理論佔比 20%。"""
        self.client.get("/checkout")
