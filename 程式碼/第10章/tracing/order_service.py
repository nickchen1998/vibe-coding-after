"""第 10 章 10.4｜訂單服務（order-service，8002）

深居內城：真正扣庫存、寫訂單的地方。它只接受閘道轉來的請求。

啟動：uvicorn order_service:app --host 127.0.0.1 --port 8002
"""

import asyncio
import logging
import random

from fastapi import FastAPI

from tracing import RequestIdFilter, TracingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(request_id)s] %(levelname)s %(message)s",
)
logging.getLogger().handlers[0].addFilter(RequestIdFilter())
logger = logging.getLogger("order-service")

app = FastAPI(title="鐵人商城訂單服務")
app.add_middleware(TracingMiddleware, service="order-service")


@app.post("/orders", summary="建立訂單")
async def create_order():
    """扣庫存、寫訂單。"""
    logger.info("開始扣庫存")
    await asyncio.sleep(random.uniform(0.05, 0.12))
    order_id = f"A{random.randint(1, 99999):05d}"
    logger.info("訂單已成立")
    return {"ok": True, "order_id": order_id}
