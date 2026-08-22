"""第 5 章示範靶場：加入「快取」與「Cookie 驗證」兩項機制，
以示範參數化測試與 Session 管理。

- GET /products/{id}：模擬一次昂貴的資料庫查詢，但帶有記憶體快取。
  同一個 id 第二次之後命中快取、極快；新的 id 未命中、較慢。
- POST /login：驗證成功後，於回應設定一個 session cookie（Cookie 攻法）。
- GET /account：受保護端點，必須帶有正確的 session cookie 才能存取，
  否則回傳 401。
- POST /api/login：驗證成功後，於 JSON 回傳一個 Bearer token（Token 攻法）。
- GET /api/account：受保護端點，必須帶 Authorization: Bearer <token> 標頭，
  否則回傳 401。

啟動：
    uvicorn target_app:app --host 127.0.0.1 --port 8000
"""
import asyncio
import random
import secrets

from fastapi import FastAPI, Header, HTTPException, Request, Response

app = FastAPI(title="第 5 章示範靶場")

# ── 記憶體快取：模擬「查過的商品會被快取」 ──
_cache: dict[int, dict] = {}

# ── 極簡 session 存放區：token -> 使用者名稱 ──
_sessions: dict[str, str] = {}

# ── Bearer token 存放區：token -> 使用者名稱 ──
_tokens: dict[str, str] = {}


@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """帶快取的商品查詢。未命中時模擬昂貴查詢（80–150ms），命中則極快。"""
    if product_id in _cache:
        return {"product_id": product_id, "cached": True, **_cache[product_id]}
    # 快取未命中：模擬一次昂貴的資料庫查詢
    await asyncio.sleep(random.uniform(0.08, 0.15))
    data = {"name": f"商品-{product_id}", "price": product_id * 10}
    _cache[product_id] = data
    return {"product_id": product_id, "cached": False, **data}


@app.post("/login")
async def login(response: Response):
    """驗證成功，發放 session cookie。"""
    token = secrets.token_hex(8)
    _sessions[token] = "demo_user"
    response.set_cookie(key="session", value=token, httponly=True)
    return {"status": "ok"}


@app.get("/account")
async def account(request: Request):
    """受保護端點：沒有有效 session cookie 就擋下。"""
    token = request.cookies.get("session")
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="未登入")
    return {"user": _sessions[token], "balance": 1000}


@app.get("/search")
async def search(q: str = ""):
    """搜尋端點：供 CSV 參數化示範（輪替不同關鍵字）。"""
    await asyncio.sleep(random.uniform(0.02, 0.08))
    return {"query": q, "hits": random.randint(0, 100)}


@app.post("/register")
async def register(payload: dict):
    """註冊端點：供 Faker 示範（每次送不同的擬真使用者資料）。"""
    await asyncio.sleep(random.uniform(0.03, 0.08))
    return {"registered": payload.get("email", "")}


@app.post("/api/login")
async def api_login():
    """驗證成功，於 JSON 回傳一個 Bearer token（不設 cookie）。"""
    token = secrets.token_hex(16)
    _tokens[token] = "demo_user"
    return {"token": token}


@app.get("/api/account")
async def api_account(authorization: str = Header(default="")):
    """受保護端點：必須帶 Authorization: Bearer <token> 標頭。"""
    # 標頭格式為 "Bearer <token>"，取出後半段
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token not in _tokens:
        raise HTTPException(status_code=401, detail="缺少或無效的 Bearer token")
    return {"user": _tokens[token], "balance": 1000}
