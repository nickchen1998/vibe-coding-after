"""第 12 章 12.2｜反哺實驗的病人：鐵人商城的商品搜尋

這支端點由 AI 代筆，語法完全正確、功能也對——但它在每一筆結果上
又各查了一次分類名稱。資料一多，它就會慢得莫名其妙。
我們要把它的真實表現餵給 AI，看它能不能自己診斷出來。

啟動：uvicorn slow_search:app --host 127.0.0.1 --port 8000
"""

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

DB_PATH = Path(__file__).resolve().parent / "shop.db"
LOG_PATH = Path(__file__).resolve().parent / "logs" / "api.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def write_log(entry: dict) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class MonitoringMiddleware(BaseHTTPMiddleware):
    """欄位與第 10、11 章一致，另加 db_query_count（10.2 教過的那一欄）。"""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.db_query_count = 0
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            route = request.scope.get("route")
            write_log({
                "level": "ERROR" if status >= 500 else "INFO",
                "request_id": rid,
                "method": request.method,
                "endpoint": getattr(route, "path", None) or "<unmatched>",
                "status": status,
                "latency_ms": latency_ms,
                "db_query_count": request.state.db_query_count,
                "service": "shop-api",
            })


app = FastAPI(title="鐵人商城搜尋")
app.add_middleware(MonitoringMiddleware)


# 本機 SQLite 就在同一顆硬碟上，一次往返幾乎不花時間；但真實系統的資料庫
# 通常在網路的另一端，每一次往返都要付出網路延遲。這裡刻意補上 1 毫秒，
# 讓「往返次數」這個成本在本機也看得見——這是模擬，不是 SQLite 的真實開銷。
DB_ROUND_TRIP_MS = 1.0


def query(request: Request, sql: str, args=()):
    """每跑一句 SQL 就記一筆帳——db_query_count 這一欄就是這樣長出來的。"""
    request.state.db_query_count += 1
    time.sleep(DB_ROUND_TRIP_MS / 1000)      # 模擬跨網路往返
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


@app.get("/search", summary="商品搜尋")
async def search(request: Request, q: str = "鐵"):
    """由 AI 代筆的搜尋端點：先撈商品，再逐筆補上分類名稱。"""
    rows = query(request, "SELECT id, name, category_id FROM products WHERE name LIKE ? LIMIT 50",
                 (f"%{q}%",))
    results = []
    for pid, name, cat_id in rows:
        cat = query(request, "SELECT name FROM categories WHERE id = ?", (cat_id,))
        results.append({"id": pid, "name": name, "category": cat[0][0] if cat else None})
    return {"count": len(results), "items": results}
