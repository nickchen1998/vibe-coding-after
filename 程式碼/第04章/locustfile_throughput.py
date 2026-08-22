"""第 4 章 4.1 示範：constant_throughput 從「產出」反推等待時間。

constant_throughput(1) 保證「每位使用者每秒最多執行 1 次任務」。
因此 20 位使用者的總吞吐量，會被穩定地壓在約 20 RPS——
無論伺服器多快，Locust 都會自動補上等待時間，把節奏鎖在目標水位。

這與 between／constant 的思路相反：後者是「先定等待、再看產出」，
前者是「先定產出、再回推等待」。適合要把系統穩定壓在某個 RPS 的測試。

啟動：
    locust -f locustfile_throughput.py --host http://127.0.0.1:8000 \
           --headless --users 20 --spawn-rate 20 --run-time 20s
"""
from locust import HttpUser, task, constant_throughput


class PacedUser(HttpUser):
    """以固定吞吐量發送請求的使用者。"""

    # 每位使用者每秒最多 1 次任務；20 人 → 總量鎖定約 20 RPS。
    wait_time = constant_throughput(1)

    @task
    def browse(self):
        self.client.get("/items/42", name="/items/[id]")
