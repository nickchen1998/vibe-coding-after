"""鐵人商城後台的守衛：Django 監控中介層與烽火台。

中介層（城牆）看的是每一個請求的「面」：誰來了、走了多久、跑了幾次資料庫。
訊號（烽火台）聽的是特定事件的「點」：城裡有人倒下了，立刻放狼煙。
"""

import json
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from django.core.signals import got_request_exception
from django.db import connection
from django.dispatch import receiver

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "backoffice.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def write_log(entry: dict) -> None:
    """把一筆日誌寫成一行 JSON，附上 UTC 時間戳。

    三個決定的理由已於 10.1 詳述：附加模式不覆蓋、行緩衝求即時、
    關掉 ensure_ascii 讓中文原樣寫出。
    """
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class QueryCounter:
    """資料庫層的守衛：每一句 SQL 進出，都在這裡過一次磅。

    這是 Django 官方文件所稱的「執行包裝器」，簽名固定為五個參數。
    它與 DEBUG 設定無關，因此正式環境也用得上——這正是它比
    connection.queries 可靠的地方。
    """

    def __init__(self) -> None:
        self.count = 0
        self.total_ms = 0.0

    def __call__(self, execute, sql, params, many, context):
        start = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.count += 1
            self.total_ms += (time.perf_counter() - start) * 1000


class MonitoringMiddleware:
    """城牆上的守衛：兩段式結構——工廠只跑一次，守衛每請求跑一次。"""

    def __init__(self, get_response):
        # 【工廠】伺服器啟動時只執行這一次，適合放昂貴的一次性準備。
        self.get_response = get_response

    def __call__(self, request):
        # 【守衛】每一個請求都會執行這一段。
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request_id_var.set(rid)
        request.monitor_rid = rid
        request.monitor_view = "<unmatched>"

        counter = QueryCounter()
        start = time.perf_counter()
        with connection.execute_wrapper(counter):
            response = self.get_response(request)   # ← 交給後續的中介層與視圖
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        status = response.status_code
        write_log({
            "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
            "request_id": rid,
            "method": request.method,
            "endpoint": request.path,
            "view_name": request.monitor_view,
            "status": status,
            "latency_ms": latency_ms,
            "db_query_count": counter.count,
            "db_time_ms": round(counter.total_ms, 1),
            "service": "backoffice",
        })
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """路由匹配完成、視圖執行之前：此刻才知道這次請求交給了哪一支視圖。

        回傳 None 代表「我沒意見，請繼續」。
        """
        request.monitor_view = view_func.__name__
        return None


@receiver(got_request_exception)
def log_unhandled_exception(sender, request, **kwargs):
    """烽火台：城裡只要有人倒下，立刻放一道狼煙。

    got_request_exception 是 Django 內建訊號，在視圖拋出未捕捉例外時發送。
    它與中介層的分工是：中介層記下「這次請求的結果是 500」，
    這裡則補上「倒下的原因是哪一種例外」。
    """
    import sys

    exc_type, exc_value, _ = sys.exc_info()
    write_log({
        "level": "ERROR",
        "request_id": getattr(request, "monitor_rid", "-"),
        "method": request.method,
        "endpoint": request.path,
        "view_name": getattr(request, "monitor_view", "<unmatched>"),
        "status": 500,
        "exc_type": exc_type.__name__ if exc_type else None,
        "exc_message": str(exc_value) if exc_value else None,
        "source": "got_request_exception",
        "service": "backoffice",
    })
