"""第 5 章實驗二：Cookie 與 Session 管理。

示範 HttpUser 內建的 client 會自動保存 cookie：
- on_start 先 POST /login，伺服器回應中的 session cookie 會被 client 自動記住。
- 之後 GET /account 時，client 會自動帶上該 cookie，因此能通過驗證。

作為對照，unauth_check 故意用一個「全新、未登入」的請求去打 /account，
證明沒有 cookie 就會被擋（401）。
"""
from locust import HttpUser, task, between


class AuthedUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        # 登入一次；回應的 Set-Cookie 會被 self.client 自動保存。
        self.client.post("/login")

    @task
    def view_account(self):
        # client 自動帶上先前保存的 session cookie，因此應回傳 200。
        with self.client.get("/account", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"預期 200，實際 {resp.status_code}")
