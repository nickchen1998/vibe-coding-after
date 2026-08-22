# 第 4 章程式碼：擬真模擬

示範思考時間、權重與生命週期，讓虛擬使用者的行為貼近真人。

## 檔案

- `target_app.py`：第 4 章擴充靶場——在第 3 章基礎上加入 `/login`（可帶 `fail_rate` 參數模擬登入失敗）、`/logout`、`/search`、刻意較慢的 `/report`（約 0.5 秒），以及 `/admin/seed`、`/admin/reset`、`/admin/count`（有狀態商品庫，示範測試級預熱／清理）。
- `locustfile.py`：主腳本，整合思考時間 `between(1,3)`、80/20 權重、`on_start`／`on_stop` 生命週期。
- `locustfile_nowait.py`：對照組，`wait_time = constant(0)`，示範零思考時間的失真測試（4.1）。
- `locustfile_twohits.py`：一個 task 內連發兩請求＋時間戳，證明 `wait_time` 等在「task 之間」而非「請求之間」（4.1）。
- `locustfile_throughput.py`：`constant_throughput(1)`，示範以固定吞吐量鎖定 RPS（4.1）。
- `locustfile_pacing.py`：`constant_pacing(1)` vs `constant(1)` 打慢端點 `/report`，證明 pacing 扣除任務耗時（4.1）。
- `locustfile_weights.py`：三任務 5:3:2 並各貼 `@tag`，驗證「權重即機率」與 `--tags` 點名（4.2）。
- `locustfile_mixed.py`：多兵種混編 BrowserUser（weight 8）＋ ApiUser（weight 2），實測族群 16:4（4.2）。
- `locustfile_lifecycle.py`：兩層生命週期——`@events.test_start`／`test_stop` 預熱清理（全場一次）＋ `on_start` 登入（每人一次），瀏覽任務隨機造訪預熱的 100 筆商品形成閉環（4.3）。
- `locustfile_stopuser.py`：`on_start` 登入失敗時 `raise StopUser` 退場，避免帶病上陣污染數據（4.3）。

### 目錄結構

```text
第04章/
├── target_app.py               ← 靶場（先跑這個）
├── locustfile.py               ← 主腳本：思考時間＋權重＋生命週期
├── locustfile_nowait.py        ← 對照：零思考時間（4.1）
├── locustfile_twohits.py       ← wait_time 等在 task 之間的時序證明（4.1）
├── locustfile_throughput.py    ← 固定吞吐量 constant_throughput（4.1）
├── locustfile_pacing.py        ← constant_pacing vs constant 對照（4.1）
├── locustfile_weights.py       ← 三任務 5:3:2 權重＋@tag（4.2）
├── locustfile_mixed.py         ← 多兵種混編 8:2（4.2）
├── locustfile_lifecycle.py     ← 兩層生命週期＋預熱閉環（4.3）
├── locustfile_stopuser.py      ← StopUser 登入失敗退場（4.3）
└── README.md                   ← 本檔
```

## 執行步驟

```bash
# 終端機 A：啟動靶場（保持運行）
uvicorn target_app:app --host 127.0.0.1 --port 8000

# 終端機 B：挑一支腳本發動攻擊，例如「有思考時間」的主腳本
locust -f locustfile.py --host http://127.0.0.1:8000 \
       --headless --users 20 --spawn-rate 20 --run-time 20s

# 其餘對照場景：
locust -f locustfile_nowait.py      --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_twohits.py     --host http://127.0.0.1:8000 --headless -u 1  -r 1  -t 12s
locust -f locustfile_throughput.py  --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_pacing.py ConstantUser --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_pacing.py PacingUser   --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_weights.py     --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_weights.py --tags checkout --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 8s
locust -f locustfile_mixed.py       --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 20s
locust -f locustfile_lifecycle.py   --host http://127.0.0.1:8000 --headless -u 15 -r 15 -t 15s
locust -f locustfile_stopuser.py    --host http://127.0.0.1:8000 --headless -u 20 -r 5  -t 20s
```

## 本章實測結果摘要

| 觀察 | 數據 |
| --- | --- |
| 思考時間影響（同 20 users / 20s） | 有：220 reqs（約 11.6 RPS）｜無：6,742 reqs（約 354 RPS），相差逾 30 倍 |
| `wait_time` 等在 task 之間 | 同一 task 兩請求間隔僅 0.06s，兩輪 task 之間才隔 2.8s（between 2,3） |
| `constant_throughput(1)`（20 users） | 385 reqs、RPS 20.21 ≈ 20（吞吐量鎖定成功） |
| `constant_pacing(1)` vs `constant(1)`（打 0.5s 的 /report） | pacing 380 reqs／RPS 20.42｜constant 260 reqs／RPS 13.63 |
| 80/20 兩任務權重實際佔比 | 瀏覽 78.8%、結帳 21.2% |
| 5:3:2 三任務權重實際佔比 | 瀏覽 50.6%、搜尋 29.9%、結帳 19.5%（誤差 <1.5%） |
| 多兵種混編 weight 8:2（20 users） | 實際生成 BrowserUser 16、ApiUser 4 |
| `--tags checkout` | 戰報只剩 `/checkout` 一行，其餘任務零請求 |
| 生命週期閉環 | `/login` 15 次 == 15 位使用者；`/items` 108 次隨機瀏覽預熱的 100 筆；預熱／清理各 1 次，結束後歸零 |
| StopUser 退場 | `/login` 24 次含 5 次失敗（30% 登入失敗退場）；`/items` 221 次、**0 失敗**（未帶病上陣） |

> 數據為本機實際執行 Locust 2.45 之真實結果，含隨機延遲，重現時會略有差異。
