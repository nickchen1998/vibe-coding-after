"""第 10 章 10.4｜雙城共用的追蹤工具箱

商城閘道與訂單服務都用這一份：同一支登記簿、同一位守衛、同一套腰牌規則。
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# 請求專屬的隱形背包。10.1 已用過它，這一節才要真正講清楚它為什麼非它不可。
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def take_or_mint(request: Request) -> tuple[str, str]:
    """接住上游的腰牌，或當場鑄一枚新的。

    回傳 (腰牌號碼, 來源)。來源只有兩種值：
      inherited：沿用上游帶來的——鏈路是通的。
      minted   ：本服務自己新鑄的——若這裡不是入口，就代表鏈斷了。
    （rid_source 這一欄是本書歸納的設計，非任何標準規定。）
    """
    incoming = request.headers.get("X-Request-ID")
    if incoming:
        return incoming, "inherited"
    return uuid.uuid4().hex[:12], "minted"


def make_write_log(service: str):
    """替某一座城做一支登記簿。"""
    path = LOG_DIR / f"{service}.log"

    def write_log(entry: dict) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "service": service, **entry}
        with path.open("a", buffering=1, encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return write_log


class RequestIdFilter(logging.Filter):
    """讓標準 logging 體系的每一筆紀錄，都自動帶上腰牌號碼。

    這樣你在業務程式碼裡照常寫 logger.info("...")，
    不必手動傳遞 request_id，它會自己出現在紀錄裡。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class TracingMiddleware(BaseHTTPMiddleware):
    """城門上的守衛。與 10.1 那位的差別只有一處：多記一欄 rid_source。"""

    def __init__(self, app, service: str):
        super().__init__(app)
        self.service = service
        self.write_log = make_write_log(service)

    async def dispatch(self, request: Request, call_next):
        rid, rid_source = take_or_mint(request)
        request_id_var.set(rid)

        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            entry = {
                "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
                "request_id": rid,
                "rid_source": rid_source,
                "method": request.method,
                "endpoint": getattr(request.scope.get("route"), "path", None) or "<unmatched>",
                "status": status,
                "latency_ms": latency_ms,
            }
            downstream = getattr(request.state, "downstream_ms", None)
            if downstream is not None:
                entry["downstream_ms"] = downstream
            self.write_log(entry)
