"""第 11 章｜把攻擊方也請上儀表板

Locust 用 --csv 會持續寫出一份歷史紀錄，裡面有每個取樣時刻的發側 RPS。
這支橋接器把那些數字改寫成日誌行、寫進靶場同一個 logs/ 目錄，
於是 Alloy 會一併收走——攻擊強度與系統反應，從此在同一根時間軸上。

（正規做法是架 locust-exporter 加 Prometheus，那是另一套堆疊；
  本書用這條「把數字寫成日誌」的簡易路，因為燈塔已經蓋好了。）

執行（與 Locust 同時跑）：python locust_bridge.py attack_stats_history.csv
"""

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "logs" / "attack.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def num(value: str) -> float:
    """Locust 的 CSV 在還沒有樣本時會填 N/A，直接轉 float 會炸。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def emit(row: dict) -> None:
    """把一列 Locust 取樣改寫成一行日誌。"""
    entry = {
        "ts": datetime.fromtimestamp(int(row["Timestamp"]), timezone.utc).isoformat(),
        "level": "INFO",
        "service": "locust",              # ← 與靶場的 shop-api 區分開
        "attack_rps": num(row.get("Requests/s")),
        "attack_fail_rps": num(row.get("Failures/s")),
        "attack_users": int(num(row.get("User Count"))),
        "attack_p95_ms": num(row.get("95%")),
    }
    with LOG_PATH.open("a", buffering=1, encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(csv_path: str) -> None:
    seen = 0
    print(f"橋接器待命：{csv_path} → {LOG_PATH.name}（Ctrl+C 結束）")
    while True:
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = [r for r in csv.DictReader(f) if r.get("Name") == "Aggregated"]
        except FileNotFoundError:
            time.sleep(1)
            continue
        for row in rows[seen:]:
            emit(row)
        if len(rows) > seen:
            print(f"  已推送 {len(rows) - seen} 筆取樣（累計 {len(rows)}）")
            seen = len(rows)
        time.sleep(2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "attack_stats_history.csv")
