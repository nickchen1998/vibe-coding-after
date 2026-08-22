"""第 10 章 10.4｜隱形背包的兩種實作：contextvars vs threading.local

同樣是「讓每個請求有自己的一份資料」，在非同步的世界裡，
舊時代的 threading.local 會全員共享，contextvars 才是對的那一個。

執行：python backpack_demo.py
"""

import asyncio
import threading
from contextvars import ContextVar

ctx_bag: ContextVar[str] = ContextVar("bag", default="（空）")
thread_bag = threading.local()


async def handle(name: str, delay: float) -> None:
    """模擬一次請求：放東西進背包 → 等一下（await）→ 再拿出來看。"""
    ctx_bag.set(name)
    thread_bag.value = name

    await asyncio.sleep(delay)          # ← 讓出控制權，其他請求趁機插隊

    print(f"  請求 {name} 醒來後："
          f"contextvars 背包 = {ctx_bag.get():<8}"
          f"threading.local 背包 = {getattr(thread_bag, 'value', '（空）')}")


async def main() -> None:
    print("三個請求交錯執行（全都跑在同一條執行緒上）：\n")
    await asyncio.gather(
        handle("甲", 0.03),
        handle("乙", 0.02),
        handle("丙", 0.01),
    )
    print("\n  contextvars：每個請求都拿回自己的東西。")
    print("  threading.local：三個請求共用同一個背包，最後寫入的人蓋掉了所有人。")


if __name__ == "__main__":
    asyncio.run(main())
