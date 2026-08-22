"""5.1 唯一性資料撞號示範：證明多 Worker 各自讀同一份 CSV 會重複領用。

每個行程（Master 或 Worker）各自執行本檔：各自開檔、各自從第一列讀起。
以「Master + 2 Worker、4 位使用者」執行，觀察兩個 Worker 的輸出——
兩邊都會印出 user001、user002（撞號），而 user003、user004 沒人用到。

用法（三個終端機）：
    locust -f locustfile_csv_split_demo.py --master --expect-workers 2 \
        --headless -u 4 -r 4 -t 6s
    locust -f locustfile_csv_split_demo.py --worker   # 開兩個
"""
import csv
from itertools import cycle

from locust import HttpUser, task, constant
from locust.exception import StopUser

with open("users.csv", newline="") as f:
    ROWS = list(csv.reader(f))
POOL = cycle(ROWS)          # 依序輪替發放帳號


class Reg(HttpUser):
    wait_time = constant(0)
    host = "http://127.0.0.1:9999"   # 不真的發請求，僅示範資料分發

    @task
    def take(self):
        row = next(POOL)
        print(f"[取得帳號] {row[0]}", flush=True)
        raise StopUser()     # 每位使用者只領一次
