"""第 6 章示範靶場：鐵人商城「限量秒殺」搶購。

用來對照三種扣庫存的寫法在高併發下的差異：

- POST /buy_naive：AI 最常交出的「讀庫存 → 判斷 → 扣庫存」三步分離、非原子的
  寫法。高併發下多個請求會同時讀到同一個舊庫存值、各自判斷通過、各自扣減，
  把商品賣超過庫存——這就是「超賣（Oversell）」。
- POST /buy_safe：用一把鎖（asyncio.Lock）把「判斷 ＋ 扣減」綁成不可分割的
  原子操作，同一時間只放行一個請求，徹底杜絕超賣（程式內鎖，單機限定）。
- POST /buy_db ：把原子性交給資料庫——用一句條件式更新
  `UPDATE ... WHERE stock > 0`，讓「判斷＋扣減」在資料庫內一步完成（6.3 登場，
  這裡以 SQLite 示範；SQLite 以資料庫層級的寫入鎖序列化並發，觀念與
  PostgreSQL／MySQL 的列級鎖相同）。

輔助端點：
- POST /reset?initial=100：把記憶體與資料庫的庫存都重置為 initial 件（每場壓測前呼叫）。
- GET  /report：回報這場搶購的戰果——初始庫存、售出數、超賣數，以及那個被競爭
  條件寫壞的庫存計數器，一眼看穿資料層有沒有崩壞。

啟動：
    uvicorn target_app:app --host 127.0.0.1 --port 8000

僅供學習示範：記憶體版庫存最能純粹呈現競爭條件；真實系統會放在資料庫或 Redis。
"""
import asyncio
import os
import sqlite3

from fastapi import FastAPI

app = FastAPI(title="第 6 章 秒殺搶購靶場")

# 行程記憶體中的搶購狀態（示範用，勿用於生產）
state = {
    "stock": 100,     # 庫存計數器（會被競爭條件寫壞，本身就是證據）
    "sold": 0,        # 累計「回報搶購成功」的次數
    "initial": 100,   # 這場搶購的初始庫存，供 /report 計算超賣
}
_lock = asyncio.Lock()   # 原子版 /buy_safe 專用的鎖

# --- /buy_db 用的 SQLite 資料庫（示範「把原子性交給資料庫」）---
DB_PATH = os.path.join(os.path.dirname(__file__), "flash_sale.db")


def _db_init(initial: int = 100):
    """建立（或重置）商品表，庫存設為 initial。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, stock INTEGER)")
    conn.execute("INSERT OR REPLACE INTO products (id, stock) VALUES (1, ?)", (initial,))
    conn.commit()
    conn.close()


# 每個執行緒各開自己的連線；SQLite 以資料庫層級的寫入鎖序列化並發寫入，
# 而「判斷＋扣減」在資料庫內是一個原子步驟，因此不會超賣。
def _db_buy():
    """對資料庫送出一句條件式更新，回傳受影響的列數（1＝扣到、0＝售罄）。"""
    conn = sqlite3.connect(DB_PATH, timeout=5)
    try:
        cur = conn.execute(
            "UPDATE products SET stock = stock - 1 WHERE id = 1 AND stock > 0"
        )
        conn.commit()
        return cur.rowcount        # 1：成功扣到一件；0：庫存已為 0，條件不成立
    finally:
        conn.close()


_db_init(state["initial"])


@app.post("/reset")
async def reset(initial: int = 100):
    """把記憶體與資料庫的庫存都重置為 initial 件、售出歸零。每場壓測前先呼叫它。"""
    state.update(stock=initial, sold=0, initial=initial)
    _db_init(initial)
    return {"stock": initial, "sold": 0}


@app.get("/report")
async def report():
    """回報戰果：初始庫存、售出、超賣數，以及被寫壞的庫存計數器。"""
    oversold = max(0, state["sold"] - state["initial"])
    return {
        "initial": state["initial"],       # 這場搶購的初始庫存
        "sold": state["sold"],             # 實際回報「搶購成功」的件數
        "remaining": state["initial"] - state["sold"],  # 應剩：負數即超賣
        "oversold": oversold,              # 超賣件數（賣超過庫存的部分）
        "stock_counter": state["stock"],   # 被競爭條件寫壞的庫存計數器（旁證）
    }


@app.post("/buy_naive")
async def buy_naive():
    """錯誤示範：讀、判斷、扣三步分離，非原子——高併發下會超賣。"""
    if state["stock"] > 0:            # 第一步：讀取並判斷「還有沒有庫存」
        await asyncio.sleep(0.01)     # 中間夾著處理（查資料庫、寫入…），放大空檔
        state["stock"] -= 1           # 第二步：扣減庫存
        state["sold"] += 1
        return {"result": "success"}
    return {"result": "sold_out"}


@app.post("/buy_safe")
async def buy_safe():
    """正確示範：用鎖把「判斷 ＋ 扣減」變成原子操作——杜絕超賣。"""
    async with _lock:                # 上鎖：同一時間只有一個請求能進入
        if state["stock"] > 0:
            await asyncio.sleep(0.01)
            state["stock"] -= 1
            state["sold"] += 1
            return {"result": "success"}
        return {"result": "sold_out"}


@app.post("/buy_db")
async def buy_db():
    """正確示範（資料庫版）：一句條件式更新，讓「判斷＋扣減」在庫內一步完成。"""
    loop = asyncio.get_event_loop()
    # 把阻塞的資料庫呼叫丟到執行緒池，讓多個請求得以真正並發地打向資料庫
    changed = await loop.run_in_executor(None, _db_buy)
    if changed == 1:                 # 資料庫回報「這一列被成功扣減」
        state["sold"] += 1
        state["stock"] = state["initial"] - state["sold"]
        return {"result": "success"}
    return {"result": "sold_out"}    # rowcount==0：庫存已見底，條件不成立
