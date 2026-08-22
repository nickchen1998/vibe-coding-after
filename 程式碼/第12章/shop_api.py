"""第 11 章｜鐵人商城 API 靶場（本章自備，不依賴其他章節目錄）

與第 10 章那支靶場的差別只有一處，但很關鍵：這一版的結帳要向
「金流連線池」借一條連線才能辦事，而連線池的容量是有限的。
兵力一多，隊伍就會在池子外排起來——那正是第 3 章講的飽和度。

啟動：uvicorn shop_api:app --host 127.0.0.1 --port 8000
"""

import asyncio
import json
import random
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_PATH = Path(__file__).resolve().parent / "logs" / "api.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# 金流連線池：同一時間最多 6 條連線在跟外部金流說話。
# 第 7 位顧客得在池子外等，等待的時間就是他的痛苦。
PAYMENT_POOL_SIZE = 6
payment_pool = asyncio.Semaphore(PAYMENT_POOL_SIZE)

# 城內人數：此刻同時在處理中的請求數
_in_flight = 0


def write_log(entry: dict) -> None:
    """把一筆日誌寫成一行 JSON，附上 UTC 時間戳。理由已於 10.1 詳述。"""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_endpoint(request: Request) -> str:
    """取出路由模板而非原始路徑，避免這一欄炸出無限多的值（詳見 10.1）。"""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "<unmatched>"


class MonitoringMiddleware(BaseHTTPMiddleware):
    """城門上的守衛：計時、登記、蓋通行證。欄位與第 10 章一致。"""

    async def dispatch(self, request: Request, call_next):
        global _in_flight
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request_id_var.set(rid)
        request.state.pool_wait_ms = 0.0

        _in_flight += 1
        in_flight_now = _in_flight
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            _in_flight -= 1
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            write_log({
                "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
                "request_id": rid,
                "method": request.method,
                "endpoint": resolve_endpoint(request),
                "status": status,
                "latency_ms": latency_ms,
                "pool_wait_ms": round(request.state.pool_wait_ms, 1),
                "in_flight": in_flight_now,
                "service": "shop-api",
            })


app = FastAPI(title="鐵人商城 API")
app.add_middleware(MonitoringMiddleware)

PRODUCTS = {
    f"IRON-{i:03d}": {"sku": f"IRON-{i:03d}", "name": f"鐵人商城商品 {i:03d}", "price": 100 + i}
    for i in range(1, 21)
}
ORDERS = {f"A{i:05d}": {"order_id": f"A{i:05d}", "status": "shipped"} for i in range(1, 51)}


@app.get("/products", summary="商品列表")
async def list_products():
    return {"items": list(PRODUCTS.values())}


@app.get("/products/{sku}", summary="單品頁")
async def get_product(sku: str):
    await asyncio.sleep(random.uniform(0.03, 0.05))
    if sku not in PRODUCTS:
        raise HTTPException(status_code=404, detail="查無此商品")
    return PRODUCTS[sku]


@app.post("/checkout", summary="結帳")
async def checkout(request: Request):
    """結帳：要先向金流連線池借一條連線，借不到就得排隊。"""
    queued_at = time.perf_counter()
    async with payment_pool:                       # ← 池子滿了就在這裡排隊
        request.state.pool_wait_ms = (time.perf_counter() - queued_at) * 1000
        await asyncio.sleep(random.uniform(0.15, 0.25))   # 與金流往返
        if random.random() < 0.05:
            raise RuntimeError("金流閘道無回應")
    return {"ok": True, "order_id": f"A{random.randint(1, 50):05d}"}


@app.get("/orders/{order_id}", summary="訂單查詢")
async def get_order(order_id: str):
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail="查無此訂單")
    return ORDERS[order_id]


@app.get("/health", summary="健康檢查")
async def health():
    return {"status": "ok"}
