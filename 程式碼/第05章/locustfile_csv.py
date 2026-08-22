"""第 5 章 5.1 示範：從 CSV 檔讀入測試資料（參數化的第二種軍糧補給）。

把 20 個搜尋關鍵字寫在 keywords.csv，用 csv.DictReader 讀入，再用
itertools.cycle 讓所有虛擬使用者輪流取用——每次請求都帶不同的關鍵字，
逼近真實流量的離散程度，也順帶戳破搜尋結果的快取。

啟動（先讓 target_app 跑在 8000）：
    locust -f locustfile_csv.py --host http://127.0.0.1:8000 \
           --headless -u 10 -r 10 -t 10s
"""
import csv
import itertools

from locust import HttpUser, task, between

# 開檔讀入所有關鍵字（模組載入時執行一次，全體共用）。
with open("keywords.csv", newline="", encoding="utf-8") as f:
    KEYWORDS = [row["keyword"] for row in csv.DictReader(f)]

# itertools.cycle 產生一個「無限循環」的迭代器：取到最後一個後，
# 會自動繞回第一個，永不耗盡——正適合讓關鍵字反覆輪替。
_keyword_cycle = itertools.cycle(KEYWORDS)


class SearchUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def search(self):
        keyword = next(_keyword_cycle)   # 每次取下一個關鍵字
        self.client.get(f"/search?q={keyword}", name="/search?q=[keyword]")
