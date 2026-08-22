"""第 4 章 4.1 示範：constant_pacing vs constant 的節奏差異。

兩個 User 類別都打同一個「慢端點」/report（約 0.5 秒），差別只在等待策略：
- ConstantUser：constant(1) —— 做完任務「之後」再等 1 秒，故週期 ≈ 1 + 任務耗時。
- PacingUser：  constant_pacing(1) —— 保證每「一輪」剛好 1 秒，任務耗時會被扣掉。

因此同樣 20 人，PacingUser 的 RPS 會明顯高於 ConstantUser——這就是 pacing
「扣除任務耗時、週期等長」的證據。

分別跑兩次（用類別名稱指定要跑哪一個）：
    locust -f locustfile_pacing.py ConstantUser --host http://127.0.0.1:8000 \
           --headless -u 20 -r 20 -t 20s
    locust -f locustfile_pacing.py PacingUser   --host http://127.0.0.1:8000 \
           --headless -u 20 -r 20 -t 20s
"""
from locust import HttpUser, task, constant, constant_pacing


class ConstantUser(HttpUser):
    """做完任務後固定再等 1 秒（週期會被任務耗時拉長）。"""
    wait_time = constant(1)

    @task
    def report(self):
        self.client.get("/report")


class PacingUser(HttpUser):
    """每一輪固定 1 秒，任務耗時自動從等待中扣除。"""
    wait_time = constant_pacing(1)

    @task
    def report(self):
        self.client.get("/report")
