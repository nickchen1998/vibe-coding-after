"""第 10 章 10.4｜商城閘道（gateway，8001）

全城唯一對外的城門：驗身、放行，再把令牌轉交給內城的訂單服務。

啟動：uvicorn gateway:app --host 127.0.0.1 --port 8001
"""

import logging
import os
import time

import httpx
from fastapi import FastAPI, Request

from tracing import RequestIdFilter, TracingMiddleware, request_id_var

ORDER_SERVICE = "http://127.0.0.1:8002"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(request_id)s] %(levelname)s %(message)s",
)
logging.getLogger().handlers[0].addFilter(RequestIdFilter())
logger = logging.getLogger("gateway")

app = FastAPI(title="鐵人商城閘道")
app.add_middleware(TracingMiddleware, service="gateway")


@app.post("/orders", summary="下單")
async def create_order(request: Request):
    """接住顧客的下單請求，轉交給內城的訂單服務。"""
    # 注意這一行：把腰牌塞進下游請求的標頭。
    # 傳遞是手動的——忘了這一行，鏈路就在這裡斷掉。
    # 環境變數 FORWARD_RID=off 可拆掉這一行，用來重現「斷鏈」的現場。
    if os.getenv("FORWARD_RID", "on") == "off":
        headers = {}
    else:
        headers = {"X-Request-ID": request_id_var.get()}

    logger.info("收到下單請求，準備轉交訂單服務")
    start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ORDER_SERVICE}/orders", headers=headers, timeout=5.0)
    request.state.downstream_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info("訂單服務已回話")

    return resp.json()
