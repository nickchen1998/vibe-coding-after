# 第 5 章程式碼：進階攻防

參數化（拒絕快取作弊）、Cookie/Session 與 Bearer Token 管理、分散式壓測。

## 檔案

- `target_app.py`：靶場——含記憶體快取的商品查詢（`/products/{id}`）、Cookie 驗證（`/login`、`/account`）、Bearer Token 驗證（`/api/login`、`/api/account`）、以及供參數化示範的 `/search`、`/register`。
- `locustfile_cache.py`：以環境變數 `MODE=fixed|random` 切換「快取作弊」與「真實參數化」（5.1，也用於分散式）。
- `locustfile_csv.py`：從 `keywords.csv` 讀入關鍵字輪替（`csv.DictReader` ＋ `itertools.cycle`）（5.1）。
- `locustfile_faker.py`：用 Faker 生成擬真繁中姓名／email／地址（5.1，需 `poetry add faker`）。
- `keywords.csv`：20 個搜尋關鍵字，CSV 參數化的資料來源。
- `locustfile_auth.py`：Cookie 攻法——`on_start` 登入 + client 自動帶 Cookie（5.2）。
- `locustfile_bearer.py`：Bearer Token 攻法——登入取 token、掛進 `Authorization` 標頭（5.2）。
- `docker-compose.yml`：用官方映像一鍵拉起「Master ＋ N Worker」蟲群（5.3）。

### 目錄結構

```text
第05章/
├── target_app.py              ← 靶場（先跑這個）
├── locustfile_cache.py        ← 快取作弊 vs 參數化（5.1）
├── locustfile_csv.py          ← CSV 參數化（5.1）
├── locustfile_faker.py        ← Faker 生成（5.1）
├── keywords.csv               ← CSV 關鍵字資料
├── locustfile_auth.py         ← Cookie 攻法（5.2）
├── locustfile_bearer.py       ← Bearer Token 攻法（5.2）
├── docker-compose.yml         ← 分散式蟲群（5.3）
└── README.md                  ← 本檔
```

## 執行步驟

```bash
# 終端機 A：啟動靶場（保持運行）
uvicorn target_app:app --host 127.0.0.1 --port 8000

# 5.1 參數化：快取作弊 vs 真實參數化（各 30 users / 15s）
MODE=fixed  locust -f locustfile_cache.py --host http://127.0.0.1:8000 --headless -u 30 -r 30 -t 15s
MODE=random locust -f locustfile_cache.py --host http://127.0.0.1:8000 --headless -u 30 -r 30 -t 15s
locust -f locustfile_csv.py   --host http://127.0.0.1:8000 --headless -u 10 -r 10 -t 10s
locust -f locustfile_faker.py --host http://127.0.0.1:8000 --headless -u 10 -r 10 -t 10s

# 5.2 認證：Cookie 與 Bearer Token
locust -f locustfile_auth.py   --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 10s
locust -f locustfile_bearer.py --host http://127.0.0.1:8000 --headless -u 20 -r 20 -t 10s
```

### 5.3 分散式：Docker Compose 蟲群

```bash
# 靶場仍在主機上跑（port 8000）；一鍵拉起 Master ＋ 4 Worker
docker compose up --scale worker=4
# 瀏覽器開 http://localhost:8089，發起測試，切到 Workers 分頁觀察
docker compose ps          # 看四個 worker 一字排開
docker compose down        # 收工
```

（不用 Docker 也可用本機多行程：`locust ... --master --expect-workers 3` 搭配數個 `locust ... --worker`。）

## 本章實測結果摘要

| 觀察 | 數據 |
| --- | --- |
| 快取作弊 vs 真實參數化（中位延遲） | fixed 2ms / random 110ms（相差逾 50 倍） |
| CSV 參數化 | `/search` 360 次、0 失敗，20 個關鍵字輪替 |
| Faker 生成 | `/register` 146 次、0 失敗，每筆姓名／email／地址皆不同 |
| Cookie 自動管理 | `/account` 190 次、0 失敗（手測未登入為 401） |
| Bearer Token | `/api/account` 196 次、0 失敗（手測未帶 token 為 401） |
| 分散式（Docker Compose） | 4 workers × 15 users = 60，RPS ~220，0 失敗 |

> 數據為本機實際執行 Locust 2.45 之真實結果，含隨機延遲，重現時會略有差異。

## 新增實測（2026-07-21）

- **登入風暴**（5.2）：`locustfile_auth.py`，100 位使用者、spawn-rate 100、跑 10 秒。
  實測：`POST /login` 100 筆全數擠在開場一秒內（中位 28 ms），`GET /account` 950 筆（中位 3 ms）。
- **CSV 撞號示範**（5.1）：`locustfile_csv_split_demo.py` ＋ `users.csv`，Master + 2 Worker、4 位使用者。
  實測：兩個 Worker 都發出 user001、user002（重複領用），user003/004 未被使用。
- **分散式對照**（5.3）：`locustfile_bench.py`，1,200 位使用者、零思考時間、25 秒。
  實測：1 Worker → RPS 3,865、中位 72 ms、P95 100 ms（Locust 發出 CPU>90% 警告）；
  4 Worker → RPS 5,149、中位 230 ms、P95 270 ms——攻擊端瓶頸解除後，瓶頸轉移到單行程靶場。

（以上數據為本機實際執行之真實結果，重現時會略有差異。）
