#!/usr/bin/env bash
# 第 9 章：量出「撈錯誤的三種寫法」各自的查詢成本
#
# Loki 每回應一次查詢，都會在回應的 stats 區塊附上一份帳單：
# 處理了多少行、掃了多少位元組、花了多少時間。
# 這支腳本對同一段時間的日誌，把三種寫法各跑五輪，把帳單印成表。
#
# 前置：本目錄的堆疊已啟動（docker compose up -d），
#       且 log_generator.py 已灌了一段時間的日誌（建議至少 30 分鐘）。
#
# 用法： ./query_cost.sh          # 預設查詢最近一小時
#        ./query_cost.sh 7200     # 查詢最近兩小時

set -euo pipefail

WINDOW="${1:-3600}"                 # 查詢時間窗（秒），預設一小時
ROUNDS=5                            # 每種寫法跑幾輪
LOKI="http://localhost:3100"

NOW=$(date +%s)
FROM=$((NOW - WINDOW))

QUERIES=(
  '{job="shop-api", level="ERROR"}'
  '{job="shop-api"} |= "ERROR"'
  '{job="shop-api"} | json | level_extracted="ERROR"'
)

echo "查詢時間窗：最近 $((WINDOW / 60)) 分鐘，每種寫法各跑 ${ROUNDS} 輪"
echo

for q in "${QUERIES[@]}"; do
  echo "── ${q}"
  for ((i = 1; i <= ROUNDS; i++)); do
    curl -s -G "${LOKI}/loki/api/v1/query_range" \
      --data-urlencode "query=${q}" \
      --data-urlencode "start=${FROM}000000000" \
      --data-urlencode "end=${NOW}000000000" \
      --data-urlencode "limit=5000" |
      python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('status') != 'success':
    print('   查詢失敗：', str(d)[:150]); raise SystemExit(1)
s = d['data']['stats']['summary']
print(f\"   第 ${i} 輪  回傳 {s['totalEntriesReturned']:>5} 筆 ｜ \"
      f\"處理 {s['totalLinesProcessed']:>7,} 行 ｜ \"
      f\"{s['totalBytesProcessed']:>11,} 位元組 ｜ \"
      f\"耗時 {s['execTime'] * 1000:6.1f} ms\")
"
  done
  echo
done

cat <<'NOTE'
判讀重點：
  1. 三種寫法回傳的筆數應完全相同——差的只有代價，不是結果。
  2. 走標籤索引那一條，「處理行數」會遠低於另外兩條；這個倍率
     才是會隨著資料量等比放大的數字。
  3. 在這種示範規模下，前兩條的「耗時」區間會彼此重疊，分不出快慢——
     那是量測雜訊，不是它們一樣快。看掃描量，別看毫秒數。
  4. 第三條（解析器）的掃描量與第二條相同，耗時卻明顯較高；
     多出來的成本全花在逐行拆解 JSON 上。
NOTE
