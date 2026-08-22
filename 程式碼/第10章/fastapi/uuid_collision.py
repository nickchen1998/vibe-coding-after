"""第 10 章 10.1｜截短 UUID 的碰撞機率實算

我們把 32 碼的 UUID 截成 12 碼（48 位元）當作 Context ID。
這一刀省下了日誌的體積與肉眼的負擔，代價是「兩枚腰牌撞號」的可能性。
這支腳本用生日問題的近似公式，把那份代價算成具體數字。

執行：python uuid_collision.py
"""

import math

BITS = 48                      # 12 個十六進位字元 = 48 位元
SPACE = 2 ** BITS              # 可用號碼的總數


def collision_probability(n: int) -> float:
    """n 枚腰牌之中，至少有兩枚撞號的機率（生日問題近似式）。"""
    return 1 - math.exp(-(n * (n - 1)) / (2 * SPACE))


if __name__ == "__main__":
    print(f"12 碼十六進位 = {BITS} 位元，號碼空間 = {SPACE:,}")
    print(f"50% 碰撞門檻約 = {math.sqrt(2 * SPACE * math.log(2)):,.0f} 枚\n")
    print(f"{'發出的腰牌數':>14}{'至少一次撞號的機率':>22}")
    for n in (10_000, 100_000, 1_000_000, 10_000_000, 100_000_000):
        print(f"{n:>14,}{collision_probability(n):>21.4%}")
