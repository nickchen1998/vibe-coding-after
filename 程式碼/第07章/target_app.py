"""第 7 章示範靶場：鐵人商城的高負載讀取，重現 N+1 查詢與深層分頁。

使用真實的 PostgreSQL（1,000 賣家、100,000 商品），提供：
- GET /products_naive：N+1 查詢。先查一批熱門商品，再「逐件」查各自的賣家。
- GET /products_join ：以單一 JOIN 一次取回商品與賣家。
- GET /search?page=N ：以 OFFSET 分頁，示範「深層分頁」隨頁碼加深而變慢。
- GET /search_keyset?after_id=X：鍵集分頁，以 WHERE id > X 直接跳到目標，恆定快。

環境需求：PostgreSQL 跑在 127.0.0.1:55432（見本章 README 的 docker 指令）。

啟動：
    uvicorn target_app:app --host 127.0.0.1 --port 8000
"""
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

DSN = "postgresql://postgres:demo@127.0.0.1:55432/shop"
_pool: asyncpg.Pool | None = None

PAGE_SIZE = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(DSN, min_size=5, max_size=20)
    yield
    await _pool.close()


app = FastAPI(title="第 7 章鐵人商城讀取靶場", lifespan=lifespan)


@app.get("/products_naive")
async def products_naive(limit: int = 30):
    """N+1 查詢：1 次查熱門商品 + N 次逐件查賣家。ORM 預設行為最常見的陷阱。"""
    async with _pool.acquire() as conn:
        products = await conn.fetch(
            "SELECT id, seller_id, name FROM products ORDER BY sales DESC LIMIT $1",
            limit,
        )
        result = []
        for p in products:                    # ← 對每一件商品，再發一次查詢取賣家
            seller = await conn.fetchrow(
                "SELECT name FROM sellers WHERE id = $1", p["seller_id"]
            )
            result.append({"name": p["name"], "seller": seller["name"]})
    return {"count": len(result), "queries": 1 + len(products)}


@app.get("/products_join")
async def products_join(limit: int = 30):
    """優化寫法：單一 JOIN，一次查詢取回商品與賣家。"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT p.name, s.name AS seller
               FROM products p JOIN sellers s ON s.id = p.seller_id
               ORDER BY p.sales DESC LIMIT $1""",
            limit,
        )
    return {"count": len(rows), "queries": 1}


@app.get("/search")
async def search(page: int = 1):
    """深層分頁：OFFSET 隨頁碼線性增長，資料庫需掃描並跳過前面所有列。"""
    offset = (page - 1) * PAGE_SIZE
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name FROM products ORDER BY id LIMIT $1 OFFSET $2",
            PAGE_SIZE, offset,
        )
    return {"page": page, "offset": offset, "count": len(rows)}


@app.get("/search_keyset")
async def search_keyset(after_id: int = 0):
    """鍵集分頁：記住上一頁最後一筆的 id，直接 WHERE id > X 跳到下一頁，恆定快。"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name FROM products WHERE id > $1 ORDER BY id LIMIT $2",
            after_id, PAGE_SIZE,
        )
    last_id = rows[-1]["id"] if rows else after_id
    return {"after_id": after_id, "next_after_id": last_id, "count": len(rows)}
