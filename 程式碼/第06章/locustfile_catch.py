"""第 6 章進階腳本：用 catch_response 自訂「成功／失敗」判定。

預設情況下 Locust 只看 HTTP 狀態碼：2xx 記為成功。但秒殺場景裡，伺服器回
HTTP 200、body 卻是 {"result":"sold_out"}，代表「商品售完、系統正常回應」，
業務上不算失敗。catch_response 讓我們接管判定，親自檢視回應內容後定奪成敗。

啟動：
    TARGET=/buy_safe locust -f locustfile_catch.py --host http://127.0.0.1:8000 \
        --headless -u 200 -r 200 -t 5s
"""
import os
from json import JSONDecodeError

from locust import HttpUser, task, constant
from locust.exception import StopUser

TARGET = os.getenv("TARGET", "/buy_safe")


class Shopper(HttpUser):
    wait_time = constant(0)

    @task
    def grab(self):
        with self.client.post(TARGET, name=TARGET, catch_response=True) as response:
            # 第一態：真失敗——500 系列，或連線失敗（Locust 以回應碼 0 表示）
            if response.status_code >= 500 or response.status_code == 0:
                response.failure(f"伺服器錯誤 {response.status_code}")
            else:
                try:
                    result = response.json()["result"]
                    if result == "success":
                        response.success()                       # 第二態：真正搶到
                    elif result == "sold_out":
                        response.success()                       # 第三態：售完＝業務正常，不計失敗
                    else:
                        response.failure(f"未預期結果：{result}")
                except (JSONDecodeError, KeyError):
                    response.failure("回應格式異常")
        raise StopUser()
