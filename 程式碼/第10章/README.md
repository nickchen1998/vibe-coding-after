# 第 10 章程式碼：三大框架監控 Middleware

FastAPI / Django / Flask 的監控中介層，與 Context ID 全鏈路追蹤。
**每一節的靶場都自成一格，可獨立跑起來，不依賴本書其他章節的目錄。**

## 目錄結構

```text
第10章/
├── docker-compose.yml       ← 本章共用的收集管線（Loki + Alloy + Grafana）
├── config.alloy             ← 本章共用的 Alloy 設定，萬用字元收走四節的 logs/
├── loki-config.yaml         ← Loki 設定（改編自第 8 章）
├── grafana-datasources.yaml ← Grafana 資料源設定（改編自第 8 章）
├── fastapi/                 ← 10.1 的靶場與實驗腳本
│   ├── shop_api.py          ← 鐵人商城 API：五支端點 ＋ MonitoringMiddleware
│   ├── order_probe.py       ← 兩層中介層的出場順序與 contextvars 方向性實證
│   ├── bench_middleware.py  ← 中介層成本的三組對照量測
│   ├── uuid_collision.py    ← 截短 UUID 的碰撞機率實算
│   ├── locustfile.py        ← 掛／不掛中介層的延遲對照壓測
│   └── logs/api.log         ← 程式自動建立
├── django-backoffice/       ← 10.2 的靶場：後台訂單管理
│   ├── manage.py            ← Django 專案入口
│   ├── backoffice/          ← 專案設定（settings.py、urls.py）
│   ├── orders/              ← 訂單 app
│   │   ├── models.py        ← Customer / Shipment / Order 三張表
│   │   ├── views.py         ← 天真版與 select_related 正解版
│   │   ├── admin.py         ← 管理後台登記
│   │   └── monitoring.py    ← MonitoringMiddleware ＋ QueryCounter ＋ 訊號接收器
│   ├── seed.py              ← 灌入 50 買家／50 物流／50 訂單
│   ├── debug_trap.py        ← connection.queries 的 DEBUG 陷阱實證
│   ├── middleware_order.py  ← Django 中介層的出場順序實證
│   └── logs/backoffice.log  ← 程式自動建立
├── flask-coupon/            ← 10.3 的靶場：優惠券核銷服務
│   ├── coupon_service.py    ← 雙鉤子方案 ＋ 券碼解析
│   ├── hook_probe.py        ← 三個鉤子在兩種模式下的出場序列
│   ├── error_rate_matrix.py ← 2×2 錯誤率對照
│   └── logs/coupon.log      ← 程式自動建立
└── tracing/                 ← 10.4 的靶場：雙城下單
    ├── tracing.py           ← 雙城共用的追蹤工具箱
    ├── gateway.py           ← 商城閘道，8001
    ├── order_service.py     ← 訂單服務，8002
    ├── backpack_demo.py     ← contextvars vs threading.local
    └── logs/                ← 程式自動建立（gateway.log、order-service.log）
```

## 收集管線：本章共用，啟動一次即可

```bash
docker compose up -d      # 拉起 Loki + Alloy + Grafana
docker compose down       # 收工
```

Grafana 在 <http://localhost:3000>（已開匿名登入，**僅供學習，勿用於生產**），
Loki 在 <http://localhost:3100>，Alloy 的管線視覺化介面在 <http://localhost:12345>。

`config.alloy` 的 `path_targets` 使用 `/var/log/app/*/logs/*.log` 萬用字元，
一次收走本章四節各自 `logs/` 目錄下的日誌，四節共用同一條管線。
只有 `level` 會被提升為 Loki 標籤（值只有 INFO／WARN／ERROR 三種，低基數），
其餘欄位留在日誌內文，查詢時以 `| json` 即時抽取——理由詳見第 8、9 章。

> **注意**：本堆疊與第 8 章那份使用同一組埠（3000／3100／12345）。
> 若第 8 章的堆疊還開著，請先到該目錄執行 `docker compose down`。

## 10.1 FastAPI：執行步驟

```bash
cd fastapi
poetry run uvicorn shop_api:app --host 127.0.0.1 --port 8000
```

看到 `Application startup complete.` 即代表啟動成功。
瀏覽器打開 <http://127.0.0.1:8000/docs> 可看到自動產生的 Swagger UI。

三道驗收指令：

```bash
curl http://127.0.0.1:8000/products
curl -H "X-Request-ID: iron-trace-0001" http://127.0.0.1:8000/products/IRON-001
curl http://127.0.0.1:8000/orders/A99999
curl -X POST http://127.0.0.1:8000/checkout      # 重複幾次直到撞上那 5%
tail -4 logs/api.log
```

驗收標準：`logs/api.log` 出現四筆日誌，第二筆的 `request_id` 為 `iron-trace-0001`、
第三筆為 `WARN`／404 且 `endpoint` 是 `/orders/{order_id}` 模板形式、
第四筆為 `ERROR`／500。

### 三支驗證腳本

```bash
python order_probe.py        # 兩層中介層的出場順序與 contextvars 方向性
python bench_middleware.py   # 中介層成本的三組對照量測
python uuid_collision.py     # 截短 UUID 的碰撞機率
```

## 10.2 Django：執行步驟

```bash
cd django-backoffice
poetry run python manage.py makemigrations orders
poetry run python manage.py migrate
poetry run python seed.py                      # 灌入示範資料
poetry run python manage.py createsuperuser    # 建立後台管理員
poetry run python manage.py runserver 127.0.0.1:8100
```

看到 `Starting development server at http://127.0.0.1:8100/` 即代表啟動成功。
瀏覽器打開 <http://127.0.0.1:8100/admin/> 可登入管理後台、翻閱訂單點名冊。

四道驗收指令：

```bash
curl http://127.0.0.1:8100/orders/               # 天真版：db_query_count = 101
curl http://127.0.0.1:8100/orders/fast/          # 正解版：db_query_count = 1
curl http://127.0.0.1:8100/orders/A99999/        # 查無此單：WARN / 404
curl http://127.0.0.1:8100/orders/A00001/refund/ # 刻意爆炸：兩筆 ERROR，同一個 request_id
tail -5 logs/backoffice.log
```

### 兩支驗證腳本

```bash
python debug_trap.py         # connection.queries 在 DEBUG=False 時靜默歸零
python middleware_order.py   # Django 的中介層順序（清單最上面站最外層）
```

## 10.3 Flask：執行步驟

```bash
cd flask-coupon
poetry run flask --app coupon_service run --port 8200
```

看到 `Running on http://127.0.0.1:8200` 即代表啟動成功；務必確認第二行是 `Debug mode: off`。

```bash
curl http://127.0.0.1:8200/coupons/IRON-1001          # accepted
curl http://127.0.0.1:8200/coupons/IRON-1003          # expired（400）
curl http://127.0.0.1:8200/coupons/1111SALE-IRON-1001 # 新格式券碼 → 500
tail -3 logs/coupon.log
```

### 兩支驗證腳本

```bash
python hook_probe.py           # 三個鉤子在兩種模式下的出場序列
python error_rate_matrix.py    # 2×2 錯誤率對照
```

## 10.4 雙城追蹤：執行步驟

需要兩個終端機視窗。

```bash
cd tracing
poetry run uvicorn order_service:app --host 127.0.0.1 --port 8002   # 視窗一
poetry run uvicorn gateway:app --host 127.0.0.1 --port 8001        # 視窗二
```

```bash
curl -X POST -H "X-Request-ID: ironman-order-7788" http://127.0.0.1:8001/orders
grep ironman-order-7788 logs/*.log        # 兩座城各一筆，同一個 request_id
python backpack_demo.py                   # contextvars vs threading.local
FORWARD_RID=off uvicorn gateway:app --port 8001   # 重現斷鏈
```

## 實測結果摘要

**數據為本機實際執行之真實結果，重現時會略有差異。**
查核環境：macOS、Python 3.13.5、fastapi 0.141.1、starlette 1.3.1、uvicorn 0.52.0、
locust 2.46.2、httpx 0.28.1，查核日期 2026-08-01。

### 中介層成本（`bench_middleware.py`，`/health` 各 3,000 次）

| 組別 | 平均 | 中位數 | P95 |
| --- | --- | --- | --- |
| 不掛任何中介層 | 0.1352 ms | 0.1321 ms | 0.1376 ms |
| 掛一個什麼都不做的中介層 | 0.2982 ms | 0.2823 ms | 0.3282 ms |
| 掛監控中介層 | 0.3653 ms | 0.3553 ms | 0.4068 ms |

拆解：`BaseHTTPMiddleware` 的包裝成本 0.1631 ms、監控邏輯本身 0.0671 ms、合計 0.2301 ms。
單獨量測 `write_log`（20,000 次）：平均 0.0313 ms、中位數 0.0298 ms、P95 0.0388 ms。
**成本的大頭是中介層這層包裝，不是同步寫檔。**

### 端到端延遲對照（`locustfile.py`，各 60 秒、20 位使用者、條件對等）

| 指標 | 掛守衛 | 不掛守衛 |
| --- | --- | --- |
| 總請求數 | 4,795 | 5,017 |
| 每秒請求數 | 84.69 | 83.74 |
| `/products` 中位延遲 | 3 ms | 2 ms |
| `/products` P95 | 6 ms | 4 ms |
| `/products/[sku]` 中位延遲 | 45 ms | 44 ms |
| `/checkout` 中位延遲 | 210 ms | 210 ms |

差距只在最輕的端點上看得見；吞吐量的差異小於場次之間的自然浮動
（掛守衛那組反而略高，代表差異已被隨機性蓋過）。另註：Locust 報表 RPS 欄
的計時窗不等於總請求數 ÷ 總秒數（4,795 ÷ 60 ≈ 79.9 ≠ 84.69），屬口徑差異。

### 中介層出場順序（`order_probe.py`）

先 `add_middleware(A)` 再 `add_middleware(B)`，實際輸出為
`B 進入 → A 進入 → 端點 → A 離開 → B 離開`，`app.user_middleware` 順序為 `[B, A]`——
**最後加入者站在最外層**。同一份輸出並證實 contextvars 只往下傳不往上傳：
端點讀得到中介層放入的值，中介層讀不到端點放入的值。

### 截短 UUID 碰撞率（`uuid_collision.py`）

12 碼十六進位 = 48 位元，號碼空間 281,474,976,710,656 枚，50% 碰撞門檻約 19,753,662 枚。
1 萬筆 0.0000%、10 萬筆 0.0018%、100 萬筆 0.1775%、1,000 萬筆 16.2753%。

### 日誌與 Loki 的對帳

一場 45 秒壓測後，`logs/api.log` 共 2,855 行，Loki 以
`sum by (level) (count_over_time({job="shop-api"}[10m]))` 查得 INFO 2,840、
ERROR 14、WARN 1，合計 2,855——**完全吻合，沒有漏收也沒有重複**。

### 10.2 Django：N+1 與 DEBUG 陷阱

查核環境追加：Django 6.0.7，資料庫為 SQLite（Django 預設）。

同一頁五十列訂單，兩種寫法的實測：

| 視圖 | `db_query_count` | `db_time_ms` | `latency_ms` |
| --- | --- | --- | --- |
| `order_list_naive`（天真版） | 101 | 1.4 | 19.4 |
| `order_list_optimized`（`select_related`） | 1 | 0.1 | 1.6 |

SQLite 省去了網路往返，因此 101 次查詢也只花 1.4 毫秒；換成跨網路的
PostgreSQL 或 MySQL，兩者差距會被網路延遲放大到肉眼可見。

`connection.queries` 的 DEBUG 陷阱（`debug_trap.py`）：

```text
  DEBUG = True ｜翻了 50 列｜connection.queries 說 101 次｜execute_wrapper 說 101 次
  DEBUG = False｜翻了 50 列｜connection.queries 說   0 次｜execute_wrapper 說 101 次
```

**靜默失效**：不拋任何錯誤，只是不再說實話。`execute_wrapper` 與 DEBUG 無關，兩種情況都算得準。

中介層順序（`middleware_order.py`）：清單由上而下為 A、B，實際輸出為
`A 進入 → B 進入 → B 離開 → A 離開`——**清單最上面的站最外層**，
與 10.1 FastAPI 的「最後加入者站最外層」方向相反，這是本章刻意對照的一組差異。

未捕捉例外的雙筆日誌：同一個 `request_id`，先由 `got_request_exception` 訊號
記下 `exc_type` 與 `exc_message`（為什麼倒下），再由中介層記下 `latency_ms`
與最終狀態碼（如何收場）。

### 10.3 Flask：那面說謊的儀表板

送出 8 次請求，其中真實的系統故障 3 次（真實錯誤率 37.5%）：

| 寫法 | 模式 | 記到幾筆 | 其中 5xx | 儀表板錯誤率 |
| --- | --- | --- | --- | --- |
| 只有 `after_request` | 正式模式 | 8 | 3 | 37.5% |
| 只有 `after_request` | 除錯模式 | 5 | 0 | **0.0%** |
| 雙鉤子方案 | 正式模式 | 8 | 3 | 37.5% |
| 雙鉤子方案 | 除錯模式 | 8 | 3 | 37.5% |

鉤子出場序列（`hook_probe.py`，Flask 3.1.3）：

```text
正式模式：before_request → after_request（狀態碼 500）→ teardown_request
除錯模式：before_request → teardown_request（after_request 完全消失）
```

官方變更紀錄佐證：Flask 0.7（2011-06-28）新增 `teardown_request` 並讓
`after_request` 在例外時不執行；Flask 1.1.0（2019-07-04）又改回會執行。
**那條網路教條在八年間為真，如今已失效。**

### 10.4 雙城追蹤

一次帶自訂腰牌的下單，兩座城各記一筆、`request_id` 完全相同：

```text
gateway       request_id=ironman-order-7788 rid_source=inherited latency_ms=96.4 downstream_ms=95.8
order-service request_id=ironman-order-7788 rid_source=inherited latency_ms=87.7
```

閘道自己的開銷只有 0.6 毫秒；96.4 減 95.8 的差額即為此。

斷鏈實測（`FORWARD_RID=off`）：訂單服務收不到腰牌，自己鑄了一枚新的，
`rid_source` 從 `inherited` 變成 `minted`——**而這次請求的狀態碼是漂亮的 200**。

`contextvars` vs `threading.local`（`backpack_demo.py`）：三個交錯執行的請求中，
contextvars 各自拿回自己的值，threading.local 三者全拿到最後寫入的那一個。

## 授權

本目錄程式碼為本書原創。`loki-config.yaml` 與 `grafana-datasources.yaml` 沿自
第 8 章的部署設定；其單機設定與資料源佈建方式改編自 Grafana 官方文件
（Loki 部署：<https://grafana.com/docs/loki/latest/setup/install/docker/>；
Grafana 資料源佈建：<https://grafana.com/docs/grafana/latest/administration/provisioning/>）。
所用工具的授權清單見專案根目錄的 `NOTICE.md`。
