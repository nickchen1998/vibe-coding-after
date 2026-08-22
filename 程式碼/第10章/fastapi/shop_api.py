"""第 10 章 10.1｜鐵人商城 FastAPI 靶場（本節自備，不依賴任何前章目錄）

一支五個端點的示範商城 API，掛上監控中介層 MonitoringMiddleware：
每一個請求進出城門時，都會被計時、登記，並在 logs/api.log 留下一行結構化 JSON 日誌。

啟動：
    uvicorn shop_api:app --host 127.0.0.1 --port 8000

環境變數：
    SHOP_MIDDLEWARE=off   不掛監控中介層（供「掛／不掛」的延遲對照實驗使用）
"""

import asyncio
import json
import os
import random
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# 請求專屬的「隱形背包」：中介層放進去，同一條請求鏈路的任何深處都取得出來。
# 完整原理與跨服務傳遞留待 10.4，此處先讓它就位。
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# 日誌檔的落腳處。本章自備 logs 目錄，由本章共用的收集管線 tail 走。
LOG_PATH = Path(__file__).resolve().parent / "logs" / "api.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def write_log(entry: dict) -> None:
    """把一筆日誌寫成一行 JSON，附上 UTC 時間戳。

    三個決定各自解決一個問題：
      "a"              附加模式，不覆蓋既有內容——史官只添筆，不塗改。
      buffering=1      行緩衝，每寫完一行就落盤，收集器才能即時 tail 到。
      ensure_ascii=False  中文原樣寫出，不被轉成 \\uXXXX 逃逸序列。
    """
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_endpoint(request: Request) -> str:
    """取出「路由模板」而非原始路徑。

    /products/IRON-001 與 /products/IRON-042 是兩個不同的路徑，
    卻是同一支端點。記模板 /products/{sku}，這一欄的值域才收得住。
    路徑沒有匹配到任何路由時（例如掃描器亂打），回傳固定字串，
    避免無限多的亂打路徑炸出無限基數。
    """
    route = request.scope.get("route")
    return getattr(route, "path", None) or "<unmatched>"


class MonitoringMiddleware(BaseHTTPMiddleware):
    """城門上的守衛：為每一位通過的訪客計時、登記、蓋上通行證。"""

    async def dispatch(self, request: Request, call_next):
        # 蓋通行證：上游帶來就沿用，沒有就當場鑄一枚。
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request_id_var.set(rid)

        start = time.perf_counter()
        status = 500  # 預設值。未捕捉例外時，這一行就是唯一的真相來源。
        try:
            response = await call_next(request)  # ← 交給真正的端點處理
            status = response.status_code
            return response
        finally:
            # 無論成功、被擋下、或當場倒地，都在此留下一筆紀錄。
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            write_log(
                {
                    "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
                    "request_id": rid,
                    "method": request.method,
                    "endpoint": resolve_endpoint(request),
                    "status": status,
                    "latency_ms": latency_ms,
                    "service": "shop-api",
                }
            )


app = FastAPI(title="鐵人商城 API")

if os.getenv("SHOP_MIDDLEWARE", "on") != "off":
    app.add_middleware(MonitoringMiddleware)


# ---------------------------------------------------------------------------
# 鐵人商城的五支端點
# ---------------------------------------------------------------------------

PRODUCTS = {
    f"IRON-{i:03d}": {"sku": f"IRON-{i:03d}", "name": f"鐵人商城商品 {i:03d}", "price": 100 + i}
    for i in range(1, 21)
}
ORDERS = {f"A{i:05d}": {"order_id": f"A{i:05d}", "status": "shipped"} for i in range(1, 51)}


@app.get("/products", summary="商品列表")
async def list_products():
    """商品列表：記憶體內取值，個位數毫秒——城中最輕快的一條人流。"""
    return {"items": list(PRODUCTS.values())}


@app.get("/products/{sku}", summary="單品頁")
async def get_product(sku: str):
    """單品頁：模擬一次資料庫查詢的耗時。"""
    await asyncio.sleep(random.uniform(0.03, 0.05))
    if sku not in PRODUCTS:
        raise HTTPException(status_code=404, detail="查無此商品")
    return PRODUCTS[sku]


@app.post("/checkout", summary="結帳")
async def checkout():
    """結帳：大部分時間在乾等外部金流閘道回話，並有約 5% 的機率等不到。"""
    await asyncio.sleep(random.uniform(0.15, 0.25))
    if random.random() < 0.05:
        raise RuntimeError("金流閘道無回應")  # 未捕捉例外：城門口倒下的訪客
    return {"ok": True, "order_id": f"A{random.randint(1, 50):05d}"}


@app.get("/orders/{order_id}", summary="訂單查詢")
async def get_order(order_id: str):
    """訂單查詢：查無此單時明白地回 404——這是預期中的錯誤，不是故障。"""
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail="查無此訂單")
    return ORDERS[order_id]


@app.get("/health", summary="健康檢查")
async def health():
    """健康檢查：給維運巡邏用的一支極輕端點。"""
    return {"status": "ok"}
