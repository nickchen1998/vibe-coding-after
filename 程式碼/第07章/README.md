# 第 7 章程式碼：鐵人商城高負載讀取（N+1 與深層分頁）

以真實 PostgreSQL 16（1,000 賣家、100,000 商品、約 300,000 評價）重現 N+1 查詢與深層分頁。

## 檔案

```text
程式碼/第07章/
├── docker-compose.yml  ← 【你新增】起 PostgreSQL 容器（ch7pg，對外 55432）
├── seed.py             ← 【你新增】建表並灌入賣家/商品/評價、建索引
├── target_app.py       ← 【你新增】讀取靶場：/products_naive、/products_join、
│                          /search、/search_keyset
├── locustfile.py       ← 【你新增】以 SCENARIO 切換 naive/join/shallow/deep/keyset
└── README.md           ← 本說明
```

## 環境準備與重現

```bash
pip install asyncpg fastapi "uvicorn[standard]" locust
docker compose up -d          # 1. 起 PostgreSQL（首次啟動需初始化，請稍候數秒）
python seed.py                # 2. 建表灌資料（約 5 秒；若遇 connection refused 表示資料庫尚未就緒，稍候重試）
uvicorn target_app:app --host 127.0.0.1 --port 8000   # 3. 起靶場
```

進資料庫下 EXPLAIN：`docker exec -it ch7pg psql -U postgres -d shop`

## 壓測（五情境）

```bash
SCENARIO=naive   locust -f locustfile.py --host http://127.0.0.1:8000 --headless -u 50 -r 50 -t 15s
SCENARIO=join    ...   # 其餘把 SCENARIO 換成 join / shallow / deep / keyset
```

## 本機實測結果（數據為本機實際執行之真實結果，重現時會略有差異）

併發 50 人、15 秒：

| 情境 | 中位 | P95 | P99 | RPS |
| --- | --- | --- | --- | --- |
| `/products_naive`（N+1，31 查詢） | 6 ms | 10 ms | **250 ms** | 161 |
| `/products_join`（JOIN，1 查詢） | 5 ms | 10 ms | 16 ms | 166 |
| `/search`（深層 page 5000，OFFSET 99980） | 9 ms | 13 ms | 85 ms | 162 |
| `/search_keyset`（鍵集，接近尾端） | 5 ms | 11 ms | 19 ms | 165 |

單請求延遲趨勢：N+1 隨每頁商品數線性攀升（N=150 時 25.4 ms），JOIN 恆定約 1 ms；
OFFSET 隨頁深增長（page 5000＝8.2 ms），鍵集分頁恆定約 1~2 ms。

EXPLAIN ANALYZE 佐證：OFFSET 99980 掃描 rows=100000（14.1 ms）；鍵集 WHERE id>99980
只讀 rows=20（0.025 ms）。
