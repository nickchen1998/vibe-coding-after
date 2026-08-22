"""第 4 章 4.1 示範：證明 wait_time 等在「task 之間」，而非「請求之間」。

一個 task（journey）內連發兩個請求（/items 與 /checkout），wait_time 設
between(2, 3)。若等待發生在「請求之間」，兩個請求會被 2～3 秒拉開；若發生
在「task 之間」，兩個請求會緊接著發生、只有兩輪 journey 之間才停頓。

我們用 request 事件記錄每個請求的時間戳，跑「1 位使用者」12 秒，印出前
幾個請求的相對時間——會清楚看到「兩兩成對、對內間隔僅數十毫秒、對與對
之間才間隔 2～3 秒」，證明等待落在 task 之間。

啟動：
    locust -f locustfile_twohits.py --host http://127.0.0.1:8000 \
           --headless -u 1 -r 1 -t 12s
"""
import time

from locust import HttpUser, task, between, events

_timeline = []   # 記錄 (時間戳, 端點名)


@events.request.add_listener
def on_request(name, **kwargs):
    _timeline.append((time.time(), name))


@events.test_stop.add_listener
def dump_timeline(**kwargs):
    if not _timeline:
        return
    t0 = _timeline[0][0]
    print("\n>>> 單一使用者的請求時間軸（相對於第一個請求）：")
    for t, name in _timeline[:12]:
        print(f"    +{t - t0:5.2f}s   {name}")


class TwoHitUser(HttpUser):
    wait_time = between(2, 3)

    @task
    def journey(self):
        """一趟旅程連發兩個請求，中間不寫任何等待。"""
        self.client.get("/items/42", name="/items/[id]")
        self.client.get("/checkout")
