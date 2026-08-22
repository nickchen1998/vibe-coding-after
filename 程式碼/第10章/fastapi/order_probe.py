"""第 10 章 10.1｜兩層中介層的出場順序實證（洋蔥城牆）

驗證兩件事：
  一、add_middleware 的疊放方向——先加入的在內層，還是後加入的在外層？
  二、contextvars 在 BaseHTTPMiddleware 上的方向性——中介層放進背包的值，
      端點取不取得到？端點放進去的值，回到中介層又取不取得到？

執行：python order_probe.py
"""

import asyncio
from contextvars import ContextVar

import httpx
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

probe_var: ContextVar[str] = ContextVar("probe", default="（預設值）")


class OrderProbe(BaseHTTPMiddleware):
    """一位只會喊口令的守衛：進城喊一聲、離城喊一聲。"""

    def __init__(self, app, name: str):
        super().__init__(app)
        self.name = name

    async def dispatch(self, request: Request, call_next):
        print(f"守衛 {self.name}：進入")
        probe_var.set(f"由守衛 {self.name} 放入")
        response = await call_next(request)
        print(f"守衛 {self.name}：離開，此時背包裡是 {probe_var.get()!r}")
        return response


app = FastAPI()
app.add_middleware(OrderProbe, name="A")   # 先加入
app.add_middleware(OrderProbe, name="B")   # 後加入


@app.get("/")
async def root():
    print(f"  端點：讀到背包裡是 {probe_var.get()!r}")
    probe_var.set("由端點放入")
    return {"ok": True}


async def main() -> None:
    print("app.user_middleware 的順序（由外而內）：")
    for mw in app.user_middleware:
        print("   ", mw.kwargs.get("name"))
    print("---- 發出一次請求 ----")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://probe") as client:
        await client.get("/")


if __name__ == "__main__":
    asyncio.run(main())
