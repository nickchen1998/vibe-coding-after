# 第 12 章程式碼：品質門、反哺實驗與 MCP 實測

終章的三項實作：把壓測變成擋得住人的品質門、跑一輪完整的「觀測數據反哺 AI」、
以及讓 AI 透過 MCP 自己讀懂 Grafana。

**本章靶場自成一格，不依賴本書其他章節的目錄。**

## 目錄結構

```text
第12章/
├── docker-compose.yml       ← Loki + Alloy + Grafana（12.2、12.3 需要）
├── config.alloy             ← Alloy 收集管線
├── loki-config.yaml         ← Loki 設定
├── grafana-datasources.yaml ← 資料源，uid 固定為 loki-ironman
├── shop_api.py              ← 12.1 的靶場：鐵人商城 API
├── locustfile.py            ← 12.1 的品質門壓測腳本（events.quitting 監聽器）
├── ci-reference/
│   └── load-test.yml        ← CI 參考範例，正文節錄展示、不實跑
├── seed_db.py               ← 12.2 反哺實驗的資料庫（20 分類、2000 商品）
├── slow_search.py           ← 12.2 的病人：含 N+1 的商品搜尋
├── fixed_search.py          ← 12.2 的成果：依 AI 診斷修正後的版本
└── logs/                    ← 程式自動建立
```

## 12.1 品質門：親眼看它擋一次

```bash
poetry run uvicorn shop_api:app --host 127.0.0.1 --port 8000

# 綠燈：合理門檻
poetry run locust -f locustfile.py --host http://127.0.0.1:8000 \
       --headless -u 20 -r 20 -t 30s
echo "結束碼：$?"

# 紅燈：把平均延遲門檻調到 30ms
MAX_AVG_MS=30 poetry run locust -f locustfile.py --host http://127.0.0.1:8000 \
       --headless -u 20 -r 20 -t 30s
echo "結束碼：$?"
```

門檻以環境變數帶入：`MAX_AVG_MS`（預設 300）、`MAX_FAIL_RATIO`（預設 0.05，
是比例不是百分比）、`MAX_P95_MS`（預設 800）。

## 12.2 反哺實驗：修改前後對照

```bash
poetry run python seed_db.py                                    # 建資料庫
poetry run uvicorn slow_search:app --host 127.0.0.1 --port 8000 # 修改前
for i in $(seq 1 30); do curl -s "http://127.0.0.1:8000/search?q=%E9%90%B5" >/dev/null; done
poetry run uvicorn fixed_search:app --host 127.0.0.1 --port 8000 # 修改後（重跑一次上面的 curl）
```

（查詢字串是中文，網址中必須先做百分比編碼，否則會被伺服器視為無效請求。）

## 12.3 MCP：讓 AI 自己讀 Grafana

```bash
export GRAFANA_ADMIN_PASSWORD='你自己想一組夠長的密碼'   # 必填，沒設會拒絕啟動
docker compose up -d
# 在 Grafana（http://localhost:3000）以 admin 與上面那組密碼登入，
# 建立服務帳號（角色選 Viewer）並簽發權杖
docker pull grafana/mcp-grafana
```

> **憑證安全提醒**：本章的 Grafana 需要登入（建立服務帳號用），管理員密碼
> **不寫在設定檔裡**，而是啟動前以環境變數帶入：
>
> ```bash
> export GRAFANA_ADMIN_PASSWORD='你自己想一組夠長的密碼'
> docker compose up -d
> ```
>
> 沒設定就直接拒絕啟動——這是刻意的，預設密碼是最常見的破口。
> 而你簽發的那枚服務帳號權杖是**真實憑證**：不要寫進任何會進版控的檔案、
> 不要貼進聊天室或議題單；實驗做完後回到 Grafana 把它撤銷
> （Administration → Users and access → Service accounts → 該帳號 → 刪除權杖）。
> 本書所有範例的權杖都以環境變數帶入，正文與程式碼目錄中不含任何真實憑證。

Claude Desktop 設定檔的寫法見正文 12.3。兩個必踩的坑：Docker 映像預設不是
標準輸入輸出模式，必須顯式加 `-t stdio`；容器裡的 `localhost` 不是你的機器，
要用 `host.docker.internal`。

## 實測結果摘要

**數據為本機實際執行之真實結果，重現時會略有差異。**
查核環境：macOS、Python 3.13.5、locust 2.46.2、Grafana 12.4.6、Loki 3.7.4、
Alloy v1.18.0、mcp-grafana（2026-08 版），查核日期 2026-08-04。

### 12.1 品質門

| 門檻設定 | 實測結果 | 結束碼 |
| --- | --- | --- |
| 平均 300ms、P95 800ms、失敗率 5% | 平均 52ms、P95 220ms、失敗率 0.00% | **0** |
| 平均 30ms（刻意調嚴） | 平均 49ms 高於門檻 30ms | **1** |

**關於 `--check-*` 旗標**：本書實測的 Locust 2.46.2 不認得 `--check-avg-response-time`
與 `--check-fail-ratio`（回報 `unrecognized arguments`）——它們來自第三方套件
locust-plugins，不在核心裡。本章採用 Locust 官方文件背書的 `events.quitting`
監聽器寫法，它也是唯一能對 P95／P99 設門檻的做法。

### 12.2 反哺實驗

同一支 `/search` 端點，各打 30 次請求：

| 指標 | 修改前（`slow_search.py`） | 修改後（`fixed_search.py`） |
| --- | --- | --- |
| `db_query_count` | 51 | **2** |
| 延遲中位數 | 86.5 ms | **3.8 ms** |
| 延遲 P95 | 87.5 ms | **4.1 ms** |
| 回應內容 | — | **與修改前逐字元相同** |

AI 的診斷（節錄）：「根本原因：N+1 查詢問題。看的是 `db_query_count` 這一欄，
不是延遲。51 = 1 + 50⋯⋯中位數與 P95 只差 1 ms，延遲分布幾乎沒有離散度，
代表每一筆請求都在做固定數量的工。」

**誠實註記**：`slow_search.py` 的 `query()` 刻意加了 1 毫秒的模擬網路往返
（`DB_ROUND_TRIP_MS`），讓「往返次數」這個成本在本機 SQLite 上也看得見。
這是模擬，不是 SQLite 的真實開銷；但真實系統的資料庫多半在網路另一端，
那 1 毫秒往往還是低估。

### 12.3 MCP 實測

以標準輸入輸出直接對 `mcp-grafana` 下指令，實際回報：

```text
伺服器：mcp-grafana｜協定 2025-06-18
工具總數：65
Loki 相關：analyze_loki_labels, list_loki_label_names, list_loki_label_values,
           query_loki_logs, query_loki_patterns, query_loki_stats,
           suggest_loki_alloy_label_config

list_datasources     → {"uid":"loki-ironman","name":"Loki","type":"loki"}
list_loki_label_names → ["filename","job","level","service_name"]
query_loki_logs      → 成功取回結構化日誌與指標查詢結果
```

服務帳號角色為 **Viewer** 即足夠——它涵蓋「檢視儀表板」與「查詢資料源」，
正是 AI 讀懂觀測數據所需的全部權限。

## 授權

本目錄程式碼為本書原創。設定檔沿自第 8、11 章的部署設定。
`grafana/mcp-grafana` 為 Grafana Labs 維護的獨立專案，授權 Apache-2.0
（與 Grafana 本體、Loki 的 AGPLv3 不同），詳見專案根目錄的 `NOTICE.md`。
