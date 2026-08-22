"""第 10 章 10.3｜鐵人商城優惠券核銷服務（Flask 靶場）

一座只做一件事的輕量哨所：查驗訪客手上那張券是真是假、是否過期、面額多少。
本節的重點不是它做什麼，而是「它的監控在什麼情況下會失效」。

啟動：
    flask --app coupon_service run --port 8200
"""

import json
import os
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_PATH = Path(__file__).resolve().parent / "logs" / "coupon.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

# 城內人數計數器：此刻同時在處理中的請求數（應用層的飽和度量測）
_in_flight = 0
_in_flight_lock = threading.Lock()

# 券庫：舊格式券碼是「IRON-數字」，行銷部門後來發出的新格式多了活動前綴
COUPONS = {
    "IRON-1001": {"amount": 100, "used": False, "expired": False},
    "IRON-1002": {"amount": 200, "used": True, "expired": False},
    "IRON-1003": {"amount": 300, "used": False, "expired": True},
}


def write_log(entry: dict) -> None:
    """把一筆日誌寫成一行 JSON，附上 UTC 時間戳。理由已於 10.1 詳述。"""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_coupon_code(code: str) -> None:
    """由 AI 代筆的券碼解析：它假設券碼一律是「IRON-數字」。

    行銷部門發出帶活動前綴的新格式（如 1111SALE-IRON-1001）時，
    這一行會當場拋出 ValueError——一個沒有人預期、也沒有人處理的例外。
    """
    int(code.split("-")[1])


@app.before_request
def start_timer():
    """訪客進城：發背包、計時起點、在城裡的人數加一。"""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    g.request_id = rid
    g.start = time.perf_counter()
    g.logged = False              # 去重旗標：這次請求還沒有人記過帳
    global _in_flight
    with _in_flight_lock:
        _in_flight += 1
        g.in_flight = _in_flight  # 記下「包含自己在內」此刻城裡有幾個人


@app.after_request
def log_request(response):
    """回應要出城了：由這位守衛記帳。

    注意：他有一個致命的前提——回應真的走到了出城這一步。
    """
    _write("after_request", response.status_code, coupon_result=g.get("coupon_result"))
    return response


# 環境變數 COUPON_TEARDOWN=off 可拆掉這位壓艙石守衛，
# 用來重現「絕大多數教學文章停下來的地方」那個天真版。
TEARDOWN_ENABLED = os.getenv("COUPON_TEARDOWN", "on") != "off"


@app.teardown_request
def count_out(exc):
    """歸還城內人數。放這裡而不是 after_request，因為只有它保證無條件執行。"""
    global _in_flight
    with _in_flight_lock:
        _in_flight -= 1


@app.teardown_request
def log_teardown(exc):
    """壓艙石：無論如何都會執行的終場鉤子。

    只在 after_request 沒記到的時候補記一筆，因此需要 g.logged 這個旗標。
    它拿不到 response 物件，所以狀態碼只能依「有沒有例外」推定。
    """
    if not TEARDOWN_ENABLED or g.get("logged"):
        return
    _write("teardown_request", 500 if exc else 0,
           exc_type=type(exc).__name__ if exc else None,
           coupon_result=g.get("coupon_result"))


def _write(source: str, status: int, exc_type: str | None = None,
           coupon_result: str | None = None) -> None:
    """兩位守衛共用的記帳動作。"""
    g.logged = True
    latency_ms = round((time.perf_counter() - g.start) * 1000, 1)
    write_log({
        "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
        "request_id": g.request_id,
        "method": request.method,
        "endpoint": str(request.url_rule) if request.url_rule else "<unmatched>",
        "status": status,
        "latency_ms": latency_ms,
        "source": source,
        "exc_type": exc_type,
        "coupon_result": coupon_result,
        "in_flight": g.get("in_flight"),
        "service": "coupon-service",
    })


@app.get("/coupons/<code>")
def check_coupon(code: str):
    """查驗一張券：是真是假、是否過期、面額多少。"""
    parse_coupon_code(code)              # ← 新格式券碼會在這裡當場僵住
    coupon = COUPONS.get(code)
    if coupon is None:
        g.coupon_result = "unknown"
        return jsonify({"detail": "查無此券"}), 400
    if coupon["used"]:
        g.coupon_result = "used"
        return jsonify({"detail": "此券已使用"}), 400
    if coupon["expired"]:
        g.coupon_result = "expired"
        return jsonify({"detail": "此券已過期"}), 400
    g.coupon_result = "accepted"
    return jsonify({"code": code, "amount": coupon["amount"]})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})
