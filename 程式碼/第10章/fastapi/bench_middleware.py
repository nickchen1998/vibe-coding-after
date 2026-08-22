"""第 10 章 10.1｜中介層成本的三組對照量測

在同一個行程內、以最輕的端點（/health）量出掛上守衛的真實代價，並把它拆成兩段：
  一、BaseHTTPMiddleware 這層「包裝」本身要多少錢？
  二、我們自己寫的記帳邏輯（計時、鑄號、寫檔）又要多少錢？

執行：python bench_middleware.py
"""
import asyncio, statistics, sys, time

import httpx
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
import shop_api


class EmptyMiddleware(BaseHTTPMiddleware):
    """什麼都不做的中介層：用來分離「包裝成本」與「記帳成本」。"""
    async def dispatch(self, request, call_next):
        return await call_next(request)


def build(kind: str) -> FastAPI:
    app = FastAPI()
    if kind == "full":
        app.add_middleware(shop_api.MonitoringMiddleware)
    elif kind == "empty":
        app.add_middleware(EmptyMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}
    return app


async def measure(kind: str, n: int = 3000):
    app = build(kind)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://bench") as c:
        for _ in range(200):          # 暖機
            await c.get("/health")
        s = []
        for _ in range(n):
            t0 = time.perf_counter()
            await c.get("/health")
            s.append((time.perf_counter() - t0) * 1000)
    s.sort()
    return statistics.mean(s), s[n // 2], s[int(n * 0.95)]


async def main():
    print(f"{'組別':<28}{'平均':>10}{'中位數':>10}{'P95':>10}")
    rows = {}
    for kind, label in [("none", "不掛任何中介層"), ("empty", "掛一個空的中介層"), ("full", "掛監控中介層")]:
        avg, med, p95 = await measure(kind)
        rows[kind] = avg
        print(f"{label:<24}{avg:>10.4f}{med:>10.4f}{p95:>10.4f}  (ms)")
    print()
    print(f"  BaseHTTPMiddleware 的包裝成本：{rows['empty'] - rows['none']:.4f} ms")
    print(f"  監控邏輯本身的成本：          {rows['full'] - rows['empty']:.4f} ms")
    print(f"  合計（掛守衛的總代價）：      {rows['full'] - rows['none']:.4f} ms")

asyncio.run(main())
