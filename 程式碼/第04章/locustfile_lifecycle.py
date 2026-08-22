"""第 4 章 4.3 示範：兩層生命週期——測試級 vs 使用者級。

- 測試級（@events.test_start / test_stop）：整場測試只觸發「一次」。
  適合放「全場只需做一次」的事——例如預熱資料庫、建立測試資料、
  測試結束後清理。這裡在 test_start 呼叫 /admin/seed 建 100 筆商品，
  在 test_stop 呼叫 /admin/reset 清空。

- 使用者級（on_start / on_stop）：每位虛擬使用者「各觸發一次」。
  適合放「每人都要做一次」的事——例如登入、登出。

預熱閉環：使用者的瀏覽任務會隨機造訪 /items/1 ～ /items/100，正是
test_start 預熱建立的那 100 筆商品——先有貨、再開店，預熱的資料真的
被用上，而非建了卻沒人看。

執行後觀察終端機輸出：
- 「預熱」訊息只會印 1 次（測試級）。
- 「登入」動作會發生 N 次（N＝使用者數，使用者級）——可由 /login 的
  請求數驗證：它應等於 --users 的數目。

啟動：
    locust -f locustfile_lifecycle.py --host http://127.0.0.1:8000 \
           --headless --users 15 --spawn-rate 15 --run-time 15s
"""
import random

from locust import HttpUser, task, between, events


# ── 測試級生命週期：整場測試各觸發一次 ──

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """整場測試開始前，預熱一次：向靶場建立 100 筆測試商品。"""
    print(">>> [測試級] 預熱：建立測試商品（整場只執行一次）")
    import requests
    host = environment.host or "http://127.0.0.1:8000"
    resp = requests.post(f"{host}/admin/seed?n=100", timeout=5)
    print(f">>> [測試級] 預熱完成，商品庫現有 {resp.json()['seeded']} 筆")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """整場測試結束後，清理一次：清空測試商品，避免污染。"""
    import requests
    host = environment.host or "http://127.0.0.1:8000"
    resp = requests.post(f"{host}/admin/reset", timeout=5)
    print(f">>> [測試級] 清理完成，清除了 {resp.json()['cleared']} 筆測試商品")


# ── 使用者級生命週期：每位使用者各觸發一次 ──

class LifecycleUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """每位使用者上線時各登入一次。"""
        self.client.post("/login")

    def on_stop(self):
        """每位使用者下線時各登出一次。"""
        self.client.post("/logout")

    @task
    def browse(self):
        """隨機瀏覽預熱建立的 100 筆商品之一。"""
        item_id = random.randint(1, 100)
        self.client.get(f"/items/{item_id}", name="/items/[id]")
