"""第 4 章對照組：完全沒有思考時間的「無效壓測」示範。

與 locustfile.py 唯一的差別，是這裡把 wait_time 設為 constant(0)，
使用者做完一個請求就毫不停頓地立刻發下一個。這會製造出遠超真實
情境的畸形流量，是初學者最常犯的錯誤。用來與有思考時間的版本對照。
"""
from locust import HttpUser, task, constant


class MachineGunUser(HttpUser):
    """毫無停頓、像機關槍一樣狂打的使用者（反面教材）。"""

    wait_time = constant(0)  # 零思考時間

    @task(8)
    def browse(self):
        self.client.get("/items/42", name="/items/[id]")

    @task(2)
    def do_checkout(self):
        self.client.get("/checkout")
