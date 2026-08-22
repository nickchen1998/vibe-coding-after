"""秒殺搶購的自動化驗收：向 /report 斷言「零超賣」，PASS/FAIL 決定結束碼。"""
import json
import sys
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/report") as resp:
    r = json.load(resp)

initial, sold, oversold = r["initial"], r["sold"], r["oversold"]
print(f"初始庫存 = {initial}　售出 = {sold}　超賣 = {oversold}　"
      f"庫存計數器 = {r['stock_counter']}")

# 業務不變量：售出數不得超過初始庫存
if oversold == 0 and sold <= initial:
    print("PASS：業務不變量成立——售出未超過庫存，零超賣。")
    sys.exit(0)      # 結束碼 0：CI 判定為通過
else:
    print(f"FAIL：業務不變量被打破——超賣 {oversold} 件，資料層已崩壞。")
    sys.exit(1)      # 結束碼 1：CI 判定為失敗
