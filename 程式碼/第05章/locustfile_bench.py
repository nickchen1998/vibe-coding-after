"""5.3 分散式實測腳本：零思考時間打 /search，讓攻擊端 CPU 成為瓶頸。

用途：對照「1 個 Worker vs 4 個 Worker」的吞吐與延遲，觀察瓶頸的轉移。
用法（Master + N 個 Worker，各開一個終端機）：
    locust -f locustfile_bench.py --master --expect-workers 4 \
        --host http://127.0.0.1:8000 --headless -u 1200 -r 400 -t 25s
    locust -f locustfile_bench.py --worker   # 重複 N 次
"""
from locust import HttpUser, task, constant


class Bencher(HttpUser):
    wait_time = constant(0)   # 零思考時間：火力全開，逼出攻擊端的極限

    @task
    def hit(self):
        self.client.get("/search?q=sword", name="/search")
