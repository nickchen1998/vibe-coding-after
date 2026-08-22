"""第 10 章 10.3｜2×2 錯誤率對照：兩種寫法 × 兩種模式

同一組請求打四次，看儀表板上的錯誤率各是多少——
其中一格會是 0.0%，而真實的錯誤率並不是 0。

執行：python error_rate_matrix.py
"""

import json
import os
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "logs" / "coupon.log"

# 八張券：三張正常受理、兩張被規則擋下、三張是新格式（會讓解析邏輯當場僵住）
CODES = [
    "IRON-1001", "IRON-1001", "IRON-1001",     # accepted
    "IRON-1002", "IRON-1003",                   # used / expired → 400
    "1111SALE-IRON-1001", "1111SALE-IRON-1002", "1111SALE-IRON-1003",  # → 500
]
TRUE_ERRORS = 3          # 真實的系統故障數
TOTAL = len(CODES)


def run_case(teardown: str, debug: bool) -> tuple[int, int]:
    os.environ["COUPON_TEARDOWN"] = teardown
    LOG_PATH.unlink(missing_ok=True)

    import importlib
    import coupon_service
    importlib.reload(coupon_service)
    coupon_service.app.debug = debug

    client = coupon_service.app.test_client()
    for code in CODES:
        try:
            client.get(f"/coupons/{code}")
        except Exception:
            pass          # 除錯模式下例外會被重新拋給伺服器，此處模擬伺服器接住

    logged = LOG_PATH.read_text(encoding="utf-8").splitlines() if LOG_PATH.exists() else []
    errors = sum(1 for line in logged if json.loads(line)["status"] >= 500)
    return len(logged), errors


if __name__ == "__main__":
    print(f"送出 {TOTAL} 次請求，其中真實的系統故障有 {TRUE_ERRORS} 次"
          f"（真實錯誤率 {TRUE_ERRORS / TOTAL:.1%}）\n")
    print(f"{'寫法':<16}{'模式':<20}{'記到幾筆':>10}{'其中 5xx':>10}{'儀表板錯誤率':>16}")
    print("-" * 74)
    for teardown, name in [("off", "只有 after_request"), ("on", "雙鉤子方案")]:
        for debug, mode in [(False, "正式模式"), (True, "除錯模式 --debug")]:
            n, e = run_case(teardown, debug)
            rate = f"{e / n:.1%}" if n else "無資料"
            print(f"{name:<14}{mode:<18}{n:>10}{e:>10}{rate:>16}")
