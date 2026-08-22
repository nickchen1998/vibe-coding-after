"""第 4 章 4.3 示範：登入失敗時，用 StopUser 讓使用者退場。

on_start 登入時，靶場 /login 帶 30% 失敗率（回 401）。若登入失敗仍讓
使用者繼續攻擊，後續每個請求都會「帶病上陣」、污染錯誤率。正確做法是
在登入失敗時 raise StopUser，讓這位使用者立刻退場。

觀察重點：戰報中 /login 會出現一定比例的 401 失敗，但 /items 幾乎全是
200——因為登入失敗者已退場，不曾污染 /items 的數據。

啟動：
    locust -f locustfile_stopuser.py --host http://127.0.0.1:8000 \
           --headless -u 20 -r 5 -t 20s
"""
from locust import HttpUser, task, between
from locust.exception import StopUser


class GuardedUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        """登入；失敗就退場，絕不帶病上陣。"""
        resp = self.client.post("/login?fail_rate=0.3", name="/login")
        if resp.status_code != 200:
            raise StopUser()            # 登入失敗，讓這位使用者立刻退場

    @task
    def browse(self):
        self.client.get("/items/42", name="/items/[id]")
