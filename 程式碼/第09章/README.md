# 第 9 章程式碼：LogQL 練習用的 LGTM 堆疊與日誌來源

第 9 章要練的是 **LogQL 查詢**，而查詢必須有日誌可打。因此本目錄自備一整套可獨立
啟動的環境：Loki（倉庫）、Alloy（收集器）、Grafana（燈塔），外加一支持續吐出結構化
JSON 日誌的鐵人商城模擬器。**本章靶場自成一格，不依賴本書其他章節的目錄**——你從第 9 章
翻開這本書，照著下面三步就能把 9.1～9.3 的每一句查詢實際跑一遍。

這套堆疊的組成、資料流與各元件職責，已於第 8 章詳述；本目錄不重複說明，只列執行步驟。

## 檔案角色

```text
程式碼/第09章/
├── docker-compose.yml       ← 【你新增】一鍵拉起 loki / alloy / grafana 三容器
├── loki-config.yaml         ← 【你新增】Loki 單機精簡設定（demo 用）
├── config.alloy             ← 【你新增】Alloy 收集管線（取代已 EOL 的 Promtail）
├── grafana-datasources.yaml ← 【你新增】Grafana 開機自動接上 Loki 資料源
├── log_generator.py         ← 【你新增】模擬鐵人商城 API，持續寫出結構化 JSON 日誌
├── query_cost.sh            ← 【你新增】量出「撈錯誤的三種寫法」各自的查詢成本（9.1）
├── logs/                    ← 【工具寫入】日誌檔 app.log（Alloy 掛載此夾盯哨；不進版控）
└── README.md                ← 本說明
```

> **設定檔出處**：`loki-config.yaml` 的單機精簡設定與 `grafana-datasources.yaml`
> 的資料源佈建格式，改編自 Grafana 官方文件（Loki 部署：
> <https://grafana.com/docs/loki/latest/setup/install/docker/>；資料源佈建：
> <https://grafana.com/docs/grafana/latest/administration/provisioning/>）。

> **收集器為何是 Alloy 不是 Promtail？** Promtail 已於 2026 年 3 月 2 日終止支援
> （EOL，見 <https://grafana.com/docs/loki/latest/send-data/promtail/>），Grafana Labs
> 改推基於 OpenTelemetry Collector 的 **Grafana Alloy**。本書一律採用 Alloy，
> 設定檔即 `config.alloy`。

## 開戰前置（三步）

```bash
docker compose up -d                      # 1. 拉起 loki + alloy + grafana（首次需下載映像檔）
python log_generator.py                   # 2. 開始寫入鐵人商城日誌到 ./logs/app.log（保持這個終端機開著）
# 3. 瀏覽器開 http://localhost:3000 → Explore → 資料源選 Loki → 右上角切 Code 模式
#    先查一句 {job="shop-api"} 確認日誌已流入，再開始 9.1 的各式查詢
```

第一步之後可用 `docker compose ps` 點名，三個容器都顯示 `Up` 才算就緒。
第二步啟動後請讓它跑上幾分鐘再查詢——9.2 的錯誤率突波與 9.3 的趨勢圖，都需要一段
時間累積的日誌才看得出形狀。

關閉：`docker compose down`（注意：Loki 資料存 `/tmp`、Alloy 的 positions 存於容器內，
`down` 後皆會清空。這是教學用的「用完即棄」設定，正式環境務必改存持久卷）。

> **埠號衝突提醒**：本堆疊與第 8、10、11、12 章那幾份使用同一組埠（3000／3100／12345）。
> 若其中任何一套還開著，請先到對應目錄執行 `docker compose down`，再回來啟動本章這套；
> 否則 Docker 會因埠被佔用而啟動失敗。（本章的容器另取名為 `ch9-loki`／`ch9-alloy`／
> `ch9-grafana`，與他章不會撞名。）

## 版本（本目錄實測環境）

| 元件 | 映像檔 |
| --- | --- |
| Loki | `grafana/loki:3.7.4` |
| Alloy | `grafana/alloy:v1.18.0` |
| Grafana | `grafana/grafana:12.4.6` |

## 埠位

| 埠 | 服務 | 用途 |
| --- | --- | --- |
| 3000 | Grafana | 視覺化網頁介面（Explore 就在這裡） |
| 3100 | Loki | 接收日誌、回應查詢的 HTTP API |
| 12345 | Alloy | 收集管線的 Web UI（`/graph`） |

## 查不到日誌時的巡檢

| 環節 | 檢查指令 |
| --- | --- |
| 應用端有在寫？ | `wc -l logs/app.log`（隔幾秒看兩次是否增加） |
| Alloy 有在收？ | `docker logs ch9-alloy`（找 `start tailing file`）或開 `localhost:12345/graph` |
| Loki 有收下？ | `curl localhost:3100/ready`、`curl localhost:3100/loki/api/v1/labels` |
| Grafana 查得到？ | Explore 查 `{job="shop-api"}`；查無先把時間範圍拉大 |

Explore 右上角預設只查「過去 1 小時」。查不到資料時，第一步永遠是把時間範圍拉大。

## 本章各節會用到的查詢

9.1～9.3 示範的每一句 LogQL，**以各該節內文為準**，此處不重複抄錄。日誌產生器帶有
隨機性，內文列出的數字是本機實際執行之真實結果，你重現時的絕對數字會有出入，但
現象的方向（錯誤突波、`/checkout` 延遲最高、瀏覽商品流量最大）會一致重現。

## 查詢成本實測（9.1 的效能階梯）

9.1 那道「撈錯誤的三種寫法」附有一張成本對照表，數據由本目錄的 `query_cost.sh` 產生：

```bash
./query_cost.sh          # 對最近一小時的日誌，三種寫法各跑五輪
./query_cost.sh 7200     # 改查最近兩小時
```

它讀的是 Loki 隨每次查詢回傳的 `stats` 區塊（處理行數、處理位元組、執行秒數）。
建議先讓 `log_generator.py` 跑滿三十分鐘以上再量，數字才有意義。

**本機實測摘要（數據為本機實際執行之真實結果，重現時會略有差異）**：以最近一小時、
每種寫法五輪計，三者回傳筆數完全相同（皆為當時的全部錯誤筆數），差別在代價——

| 寫法 | 處理行數 | 處理位元組 | 耗時區間 |
| --- | --- | --- | --- |
| `{job="shop-api", level="ERROR"}` | 969 | 165 kB | 5.5 – 12.0 ms |
| `{job="shop-api"} \|= "ERROR"` | 13,386 | 2.62 MB | 8.0 – 10.4 ms |
| `{job="shop-api"} \| json \| level_extracted="ERROR"` | 13,386 | 2.62 MB | 28.7 – 32.3 ms |

判讀時請注意兩件事，9.1 內文有完整說明：**（一）** 在這種示範規模下，前兩者的耗時
區間彼此重疊，分不出快慢——那是量測雜訊，真正會隨資料量等比放大的是「處理行數」
那一欄；**（二）** 第三者的掃描量與第二者相同，耗時卻高出約三倍，多出來的成本全花在
逐行解析 JSON 上。

## 授權

本目錄程式碼為本書原創。`loki-config.yaml` 與 `grafana-datasources.yaml` 的單機設定
與資料源佈建方式改編自 Grafana 官方文件（Loki 部署：
<https://grafana.com/docs/loki/latest/setup/install/docker/>；Grafana 資料源佈建：
<https://grafana.com/docs/grafana/latest/administration/provisioning/>）。
所用工具的授權清單見專案根目錄的 `NOTICE.md`。
