"""第 3 章示範用的「被壓測目標系統」。

一個刻意設計的最小 FastAPI 服務，提供三種特性不同的端點，
讓我們在壓力測試時能觀察到有意義的 KPI（RPS、延遲分佈、錯誤率）：

- GET /            首頁，幾乎無延遲，代表輕量請求。
- GET /items/{id}  模擬一次資料庫查詢，帶有隨機延遲。
- GET /checkout    模擬較重的結帳流程，延遲更高，且有少量失敗率。

啟動方式（於本章 venv 中）：
    uvicorn target_app:app --host 127.0.0.1 --port 8000
"""
import asyncio
import random

from fastapi import FastAPI, HTTPException

app = FastAPI(title="第一幕示範靶場")


@app.get("/")
async def index():
    """首頁：代表最輕量、幾乎瞬間回應的請求。"""
    return {"message": "歡迎光臨示範靶場"}


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    """模擬一次資料庫查詢：帶有 10–60 毫秒的隨機延遲。"""
    await asyncio.sleep(random.uniform(0.01, 0.06))
    return {"item_id": item_id, "name": f"商品-{item_id}", "price": item_id * 10}


@app.get("/checkout")
async def checkout():
    """模擬較重的結帳流程：延遲較高（50–200 毫秒），且約 5% 機率失敗。

    這個失敗率是刻意加入的，用來示範 Error Rate 這項關鍵指標。
    """
    await asyncio.sleep(random.uniform(0.05, 0.20))
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="結帳服務暫時無法使用")
    return {"status": "ok", "order_id": random.randint(10000, 99999)}
