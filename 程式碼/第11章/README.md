# 第 11 章程式碼：黃金儀表板與自動化告警

以四塊面板（RED ＋ 飽和度）看盡鐵人商城的健康，讓 Locust 的攻擊與 Loki 的
日誌落在同一根時間軸上，最後裝上一條會自己開火的告警規則。

**本章靶場自成一格，不依賴本書其他章節的目錄。**

## 目錄結構

```text
第11章/
├── docker-compose.yml       ← 一鍵拉起 Loki + Alloy + Grafana
├── config.alloy             ← Alloy 收集管線（只提升 level 為標籤）
├── loki-config.yaml         ← Loki 單機設定
├── grafana-datasources.yaml ← 資料源，uid 寫死為 loki-ironman
├── dashboards/
│   └── golden-dashboard.json    ← 黃金儀表板本體（儀表板即程式碼）
├── provisioning/
│   ├── dashboards/dashboards.yaml   ← 告訴 Grafana 去哪裡找儀表板
│   └── alerting/alerts.yaml         ← 告警規則、聯絡點、通知政策
├── shop_api.py              ← 靶場：鐵人商城 API（含金流連線池）
├── locustfile.py            ← 階梯攻擊：10 → 30 → 60 → 100 人
├── locust_bridge.py         ← 把 Locust 的 CSV 統計推進 Loki（雙側同屏）
├── webhook_sink.py          ← 本機告警接收器，看得見通知長什麼樣
└── logs/                    ← 程式自動建立（api.log、attack.log）
```

## 執行步驟

```bash
# 1. 拉起收集與視覺化堆疊（首次需下載映像檔）
docker compose up -d

# 2. 啟動靶場
poetry run uvicorn shop_api:app --host 127.0.0.1 --port 8000

# 3. 啟動告警接收器（另一個終端機）
poetry run python webhook_sink.py

# 4. 啟動橋接器與階梯攻擊（再一個終端機）
poetry run python locust_bridge.py attack_stats_history.csv &
poetry run locust -f locustfile.py --host http://127.0.0.1:8000 --headless \
       --csv attack --csv-full-history
```

Grafana 在 <http://localhost:3000>（已開匿名登入，**僅供學習，勿用於生產**）。
開機時會自動佈建資料源、黃金儀表板與告警規則，**不需要手動匯入任何東西**。

> **注意**：本堆疊與第 8、10 章那兩份使用同一組埠（3000／3100／12345）。
> 若那些堆疊還開著，請先到對應目錄執行 `docker compose down`。

驗收標準：儀表板「鐵人商城｜黃金儀表板（RED）」出現五塊面板，攻擊強度的階梯
與 RED 曲線落在同一時間軸；攻擊進行到第三分半左右，告警規則由 Normal 翻成
Pending、再翻成 Firing，接收器印出 `firing` 通知；攻擊結束後回到 Normal 並
收到 `resolved` 通知。

## 實測結果摘要

**數據為本機實際執行之真實結果，重現時會略有差異。**
查核環境：macOS、Python 3.13.5、fastapi 0.141.1、uvicorn 0.52.0、locust 2.46.2、
Grafana 12.4.6、Loki 3.7.4、Alloy v1.18.0，查核日期 2026-08-03。

### 階梯攻擊：飽和度率先開口

四分鐘、四階兵力，靶場的金流連線池容量為 6：

| 兵力 | 結帳筆數 | 連線池排隊 P95 | 結帳延遲 P95 | 城內人數峰值 |
| --- | --- | --- | --- | --- |
| 10 人 | 255 | 0 ms | 247 ms | 10 |
| 30 人 | 671 | 0 ms | 246 ms | 18 |
| 60 人 | 1,427 | 145 ms | 359 ms | 25 |
| 100 人 | 1,822 | 1,185 ms | 1,384 ms | 53 |

**60 人那一階是關鍵**：排隊已達 145 毫秒，延遲卻只從 246 爬到 359——
飽和度先動，體感後動，正是第 3 章 3.2 的預言。

整場合計：靶場日誌 23,276 筆、5xx 196 筆、**錯誤率 0.84%**；
Locust 側 23,239 個請求、聚合 P95 880 ms、P99 1,300 ms、峰值 96.78 req/s；
儀表板上流量最後一階的峰值約 250 req/s（圖例 Max 欄的 444 是起跑瞬間的孤立尖刺，屬取樣窗邊界假象）、連線池最長排隊 1,481 ms。

### 告警

規則「P99 延遲過高」：`for: 1m`、門檻 500 ms、每 30 秒評估一次。
實測走完 Normal → Pending → Firing → Resolved 全程，接收器收到 `firing`
與 `resolved` 兩則通知。

### 一個實作上踩過的坑

把 Locust 的日誌接進同一條流之後，錯誤面板整塊變成 `No data`。
Loki 的錯誤訊息直接指出兇手：

```text
pipeline error: 'LabelFilterErr' ... strconv.ParseFloat: parsing "": invalid syntax
filename="/var/log/app/attack.log" ... status=""
```

攻擊方的日誌沒有 `status` 欄位，導致 `status>=500` 的數值比較失敗。
修法是每一句查詢都加上 `| service="shop-api"` 畫清作用域。

## 授權

本目錄程式碼為本書原創。`loki-config.yaml` 與 `grafana-datasources.yaml` 沿自
第 8 章的部署設定；其單機設定與資料源佈建方式改編自 Grafana 官方文件
（Loki 部署：<https://grafana.com/docs/loki/latest/setup/install/docker/>；
Grafana 佈建：<https://grafana.com/docs/grafana/latest/administration/provisioning/>）。
所用工具的授權清單見專案根目錄的 `NOTICE.md`。
