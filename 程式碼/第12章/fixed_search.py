"""第 12 章 12.2｜反哺實驗的成果：依 AI 建議修正後的商品搜尋

把 50 次「一次問一個分類」折成 1 次「一次問完所有分類」，
db_query_count 從 51 降到 2。這一版是把觀測數據餵給 AI 之後，
依它的診斷改出來的。

啟動：uvicorn fixed_search:app --host 127.0.0.1 --port 8000
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
    """先撈商品，再用一句 IN 查詢一次補齊所有分類名稱（原本是逐筆查，N+1）。"""
    rows = query(request, "SELECT id, name, category_id FROM products WHERE name LIKE ? LIMIT 50",
                 (f"%{q}%",))
    if not rows:
        return {"count": 0, "items": []}

    # 去重後一次問完：50 件商品最多只會用到 20 個分類，SQL 也只發一句。
    # 注意 IN () 是空集合語法錯誤，所以上面必須先擋掉沒有結果的情況。
    cat_ids = sorted({cat_id for _, _, cat_id in rows if cat_id is not None})
    cat_map = {}
    if cat_ids:
        placeholders = ",".join("?" * len(cat_ids))
        cat_map = dict(query(request,
                             f"SELECT id, name FROM categories WHERE id IN ({placeholders})",
                             tuple(cat_ids)))

    # 依原本的商品順序組裝，查無分類一樣給 None，回應格式與修正前完全相同。
    items = [{"id": pid, "name": name, "category": cat_map.get(cat_id)}
             for pid, name, cat_id in rows]
    return {"count": len(items), "items": items}
