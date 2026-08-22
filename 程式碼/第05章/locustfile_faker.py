"""第 5 章 5.1 示範：用 Faker 生成擬真測試資料（參數化的第三種軍糧補給）。

註冊、下單這類測試，需要大量「長得像真的、但彼此不同」的資料——姓名、
email、地址。手寫幾筆不夠、寫死一筆又會撞號。Faker 正是為此而生：一行
就能生成擬真的繁體中文姓名與地址。

安裝：poetry add faker   （或 pip install faker）

啟動（先讓 target_app 跑在 8000）：
    locust -f locustfile_faker.py --host http://127.0.0.1:8000 \
           --headless -u 10 -r 10 -t 10s
"""
from faker import Faker
from locust import HttpUser, task, between

# 指定繁體中文（台灣）語系，生成的姓名、地址都會是在地化的。
fake = Faker("zh_TW")


class RegisterUser(HttpUser):
    wait_time = between(0.3, 0.8)

    @task
    def register(self):
        # 每次都生成一組全新的擬真使用者資料，絕不撞號。
        payload = {
            "name": fake.name(),
            "email": fake.email(),
            "address": fake.address(),
        }
        self.client.post("/register", json=payload, name="/register")
