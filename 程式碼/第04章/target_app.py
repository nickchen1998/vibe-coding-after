"""第 4 章示範靶場：在第 3 章基礎上擴充，用以示範本章三大主題。

相較第 3 章，本靶場多了：
- /login、/logout：示範 on_start / on_stop 生命週期。/login 可帶 fail_rate
  參數模擬登入失敗（供 4.3 的 StopUser 退場示範）。
- /search：作為第三個行為端點，示範三任務權重分配（4.2）。
- /report：刻意較慢（約 0.5 秒）的端點，用以凸顯 constant_pacing 與
  constant 的節奏差異（4.1）。
- /admin/seed、/admin/reset、/admin/count：一個「有狀態」的商品庫，
  示範測試級生命週期（test_start 預熱建資料、test_stop 清理，見 4.3）。

啟動：
    uvicorn target_app:app --host 127.0.0.1 --port 8000
"""
import asyncio
import random

from fastapi import FastAPI, HTTPException

app = FastAPI(title="第 4 章示範靶場")

# 一個記憶體中的「商品庫」。它是有狀態的：測試前可預熱、測試後可清理。
# 僅供學習示範，勿用於生產（真實系統會用資料庫）。
_catalog: dict[int, str] = {}


@app.get("/")
async def index():
    return {"message": "首頁"}


@app.post("/login")
async def login(fail_rate: float = 0.0):
    """模擬登入：回傳一個假的 session token。

    fail_rate（0～1）：以此機率回傳 401 登入失敗，供示範 StopUser 退場。
    預設 0（永遠成功），不影響其他測試。
    """
    await asyncio.sleep(random.uniform(0.02, 0.05))
    if random.random() < fail_rate:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    return {"token": f"tok-{random.randint(100000, 999999)}"}


@app.post("/logout")
async def logout():
    """模擬登出。"""
    return {"status": "logged_out"}


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    await asyncio.sleep(random.uniform(0.01, 0.06))
    return {"item_id": item_id, "name": f"商品-{item_id}"}


@app.get("/search")
async def search(q: str = ""):
    """搜尋：通常比單筆查詢重一些（要掃描、排序），延遲刻意設高。"""
    await asyncio.sleep(random.uniform(0.03, 0.12))
    return {"query": q, "hits": random.randint(0, 50)}


@app.get("/checkout")
async def checkout():
    await asyncio.sleep(random.uniform(0.05, 0.20))
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="結帳服務暫時無法使用")
    return {"status": "ok"}


@app.get("/report")
async def report():
    """報表：刻意較慢（約 0.5 秒）的端點。當任務本身耗時可觀時，
    constant_pacing（扣除耗時、週期等長）與 constant（做完再等）的
    節奏差異才會明顯浮現。"""
    await asyncio.sleep(random.uniform(0.4, 0.6))
    return {"status": "報表已產生"}


# ── 以下三個 /admin 端點，供示範「測試級生命週期」的預熱與清理 ──

@app.post("/admin/seed")
async def seed(n: int = 100):
    """預熱：一次建立 n 筆測試商品。整場測試只需在 test_start 呼叫一次。"""
    for i in range(1, n + 1):
        _catalog[i] = f"測試商品-{i}"
    return {"seeded": len(_catalog)}


@app.post("/admin/reset")
async def reset():
    """清理：清空商品庫。整場測試結束後於 test_stop 呼叫一次。"""
    count = len(_catalog)
    _catalog.clear()
    return {"cleared": count}


@app.get("/admin/count")
async def count():
    """查詢目前商品庫的筆數，用來驗證預熱／清理是否生效。"""
    return {"count": len(_catalog)}
