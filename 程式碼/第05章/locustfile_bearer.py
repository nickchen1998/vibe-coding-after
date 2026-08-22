"""第 5 章 5.2 示範：Bearer Token 攻法（攻破以 Token 保護的 API）。

與 Cookie 攻法（locustfile_auth.py）並列的另一種門禁。現代 API 常不用
cookie，而是要求每個請求帶一個 Authorization: Bearer <token> 標頭。做法：
- on_start 先 POST /api/login 取得 token。
- 把 token 設進 self.client.headers，之後每個請求都會自動帶上。

啟動（先讓 target_app 跑在 8000）：
    locust -f locustfile_bearer.py --host http://127.0.0.1:8000 \
           --headless -u 20 -r 20 -t 10s
"""
from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        # 登入取得 Bearer token。
        resp = self.client.post("/api/login")
        token = resp.json()["token"]
        # 把 token 掛進 client 的預設標頭；此後每個請求都會自動帶上。
        self.client.headers["Authorization"] = f"Bearer {token}"

    @task
    def view_account(self):
        with self.client.get("/api/account", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"預期 200，實際 {resp.status_code}")
