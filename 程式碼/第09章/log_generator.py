"""第 9 章：模擬「鐵人商城 API」持續產生結構化 JSON 日誌。

本章自備一份日誌產生器（內容與第 8 章相同），讓 LogQL 的每一句查詢
都有真實的日誌可打，不必回頭啟動他章的目錄。

把日誌寫到 ./logs/app.log，交由 Alloy 收集後推送至 Loki。
日誌刻意混入：多數正常 200、少量 4xx、以及每隔一段時間（約兩分多鐘）湧起的
500 錯誤突波（模擬系統承壓時的行為），好讓 9.1～9.3 的過濾、聚合與
Logs to Metrics 查詢都有戲可唱。

執行： python log_generator.py
"""
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent / "logs" / "app.log"
LOG_PATH.parent.mkdir(exist_ok=True)

ENDPOINTS = ["/", "/items/[id]", "/checkout", "/search", "/account"]
rng = random.Random()


def make_entry(now: float) -> dict:
    endpoint = rng.choices(ENDPOINTS, weights=[3, 8, 2, 2, 1])[0]

    # 基準延遲依端點而異
    base = {"/": 5, "/items/[id]": 35, "/checkout": 130, "/search": 40, "/account": 20}[endpoint]
    latency = max(1, int(rng.gauss(base, base * 0.3)))

    # 錯誤率：checkout 較高；偶爾整體突波
    spike = (int(now) // 20) % 7 == 0          # 每隔一段時間製造一次 500 突波
    err_p = 0.15 if endpoint == "/checkout" else 0.02
    if spike:
        err_p += 0.25

    r = rng.random()
    if r < err_p:
        status, level = 500, "ERROR"
        latency = int(latency * rng.uniform(1.5, 3))   # 錯誤通常更慢
    elif r < err_p + 0.05:
        status, level = 404, "WARN"
    else:
        status, level = 200, "INFO"

    return {
        "ts": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "level": level,
        "endpoint": endpoint,
        "method": "GET" if endpoint != "/checkout" else "POST",
        "status": status,
        "latency_ms": latency,
        "msg": f"{'POST' if endpoint == '/checkout' else 'GET'} {endpoint} -> {status}",
    }


def main():
    print(f"寫入日誌到 {LOG_PATH}（Ctrl+C 停止）")
    with LOG_PATH.open("a", buffering=1) as f:
        while True:
            now = time.time()
            # 每輪寫入數筆，模擬真實流量密度
            for _ in range(rng.randint(3, 12)):
                f.write(json.dumps(make_entry(now), ensure_ascii=False) + "\n")
            time.sleep(1)


if __name__ == "__main__":
    main()
