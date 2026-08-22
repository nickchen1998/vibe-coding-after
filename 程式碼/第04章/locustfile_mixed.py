"""第 4 章 4.2 示範：多兵種混編——不同族群的使用者並存。

定義兩種 User 類別，用「類別層級的 weight」決定各族群佔總人數的比例：
- BrowserUser（weight 8）：一般顧客，用瀏覽器逛街，思考時間長。
- ApiUser   （weight 2）：App／爬蟲，固定節奏呼叫 API。

開 20 位使用者時，應約分配為 16 位 BrowserUser、4 位 ApiUser（8:2）。
測試結束時印出各族群的實際生成數，作為證據。

啟動：
    locust -f locustfile_mixed.py --host http://127.0.0.1:8000 \
           --headless -u 20 -r 20 -t 20s
"""
from locust import HttpUser, task, between, constant, events


_state = {}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    _state["env"] = environment


@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    # 生成剛完成、使用者都還在線上，此刻讀各族群數量才準確。
    env = _state.get("env")
    counts = env.runner.user_classes_count if env else {}
    print(f"\n>>> 生成完畢，總數 {user_count}，各族群實際生成數：{counts}")


class BrowserUser(HttpUser):
    """一般顧客：思考時間長，佔多數。"""
    weight = 8
    wait_time = between(3, 8)

    @task
    def browse(self):
        self.client.get("/items/42", name="/items/[id]")


class ApiUser(HttpUser):
    """App／爬蟲：固定節奏呼叫 API，佔少數。"""
    weight = 2
    wait_time = constant(1)

    @task
    def call_api(self):
        self.client.get("/search?q=locust", name="/search")
