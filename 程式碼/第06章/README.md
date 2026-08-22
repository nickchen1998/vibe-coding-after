# 第 6 章程式碼：高併發寫入場景——秒殺搶購

本目錄是第 6 章的可執行靶場與壓測腳本。示範 AI 生成的「讀→判斷→扣」庫存邏輯
如何在高併發下釀成超賣，以及兩種原子化端點（程式內鎖、資料庫條件式更新）如何修正。

## 檔案角色

```text
程式碼/第06章/
├── target_app.py        ← 秒殺靶場（FastAPI）
│                          端點：/buy_naive（無鎖）、/buy_safe（asyncio.Lock）、
│                          /buy_db（SQLite 條件式更新）、/reset、/report
├── locustfile.py        ← 壓測腳本：集合點瞬間爆量，每位買家只搶一次
├── locustfile_catch.py  ← 進階腳本：用 catch_response 自訂三態成敗判定
├── verify.py            ← 自動化驗收：向 /report 斷言「零超賣」，PASS/FAIL 決定結束碼
└── README.md            ← 本說明
```

> `flash_sale.db` 是靶場啟動時自動建立的 SQLite 檔（供 `/buy_db` 使用），不需手動建立、也不進版控。

## 環境準備

```bash
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn locust
```

## 重現步驟

1. 啟動靶場（第一個終端機，保持執行）：

   ```bash
   uvicorn target_app:app --host 127.0.0.1 --port 8000
   ```

2. 攻擊錯誤版並驗收（第二個終端機）：

   ```bash
   curl -X POST "http://127.0.0.1:8000/reset?initial=100"
   TARGET=/buy_naive locust -f locustfile.py \
       --host http://127.0.0.1:8000 --headless -u 200 -r 200 -t 5s
   curl http://127.0.0.1:8000/report
   python verify.py                                                 # → FAIL（結束碼 1）
   ```

3. 攻擊兩種正確版（把 `TARGET` 換成 `/buy_safe` 或 `/buy_db`，各自 `reset` 後再打）：

   ```bash
   curl -X POST "http://127.0.0.1:8000/reset?initial=100"
   TARGET=/buy_db locust -f locustfile.py \
       --host http://127.0.0.1:8000 --headless -u 200 -r 200 -t 5s
   curl http://127.0.0.1:8000/report
   python verify.py                                                 # → PASS（結束碼 0）
   ```

4. catch_response 三態判定（攻擊 `/buy_safe`，售完不計入失敗）：

   ```bash
   curl -X POST "http://127.0.0.1:8000/reset?initial=100"
   TARGET=/buy_safe locust -f locustfile_catch.py \
       --host http://127.0.0.1:8000 --headless -u 200 -r 200 -t 5s
   ```

## 本機實測結果摘要（數據為本機實際執行之真實結果，重現時會略有差異）

以 200 位使用者在一秒內集合、搶購 100 件庫存：

| 端點 | 失敗率 | 售出 | 超賣 | 中位延遲 | RPS | verify.py |
| --- | --- | --- | --- | --- | --- | --- |
| `/buy_naive`（無鎖） | 0.00% | 200 | **100** | 41 ms | 2906 | FAIL |
| `/buy_safe`（程式內鎖） | 0.00% | 100 | **0** | 1266 ms | 154 | PASS |
| `/buy_db`（DB 條件式更新） | 0.00% | 100 | **0** | 93 ms | 883 | PASS |

三者在 HTTP 層都是「零失敗」，差別全在資料層：無鎖版超賣 100 件、計數器崩壞成 −100。
兩種正確版都零超賣；資料庫條件式更新的吞吐量是程式內鎖的五倍以上，主因是**臨界區較短**
（buy_safe 把 10ms 模擬耗時圈在鎖內，buy_db 的臨界區只有一句 UPDATE），且天生跨實例
安全——這是它成為業界預設解的原因（詳見 6.3 的解讀）。

敏感度實測（庫存 10 件，`/buy_naive`）：超賣數隨併發上升——50 人超賣 40、
100 人超賣 90、200 人超賣 120。

## 技術備忘：Locust 與執行緒同步原語

Locust 底層以 gevent 驅動，`import locust` 時會執行 gevent 的 monkey patch，
把標準庫 `threading` 的同步原語（含 `Barrier`）換成 gevent 協作版——行為已被
偷換、語義不可依賴。需要同步時請直接使用 gevent 原語（如 `gevent.event.Event`，
見 6.2 進階框），意圖最明確。
