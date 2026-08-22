# 第 8 章程式碼：Grafana LGTM 監控堆疊（Loki + Alloy + Grafana）

以一份 Docker Compose 拉起精簡的地端可觀測性平台，打通「應用程式 → 收集 → 儲存 → 視覺化」的完整資料流。**本章靶場自成一格，不依賴本書其他章節的目錄**；第 9 章另備了一份同構的堆疊在 `程式碼/第09章/`，兩者各自獨立啟動。

## 檔案角色

```text
程式碼/第08章/
├── docker-compose.yml       ← 【你新增】一鍵拉起 loki / alloy / grafana 三容器
├── loki-config.yaml         ← 【你新增】Loki 單機精簡設定（demo 用）
├── config.alloy             ← 【你新增】Alloy 收集管線（取代已 EOL 的 Promtail）
├── grafana-datasources.yaml ← 【你新增】Grafana 開機自動接上 Loki 資料源
├── log_generator.py         ← 【你新增】模擬鐵人商城 API，持續寫出結構化 JSON 日誌
├── logs/                    ← 【工具寫入】日誌檔 app.log（Alloy 掛載此夾盯哨；不進版控）
└── README.md                ← 本說明
```

> **設定檔出處**：`loki-config.yaml` 的單機精簡設定與 `grafana-datasources.yaml`
> 的資料源佈建格式，改編自 Grafana 官方文件（Loki 部署：
> <https://grafana.com/docs/loki/latest/setup/install/docker/>；資料源佈建：
> <https://grafana.com/docs/grafana/latest/administration/provisioning/>）。

> **收集器為何是 Alloy 不是 Promtail？** Promtail 已於 2026 年 3 月 2 日終止支援（EOL，官方公告見 <https://grafana.com/docs/loki/latest/send-data/promtail/>），Grafana Labs 改推基於 OpenTelemetry Collector 的 **Grafana Alloy**；舊設定可用 `alloy convert` 自動轉換（見 <https://grafana.com/docs/alloy/latest/set-up/migrate/from-promtail/>）。本書一律採用 Alloy，設定檔即 `config.alloy`。

## 環境準備與重現

```bash
docker compose up -d                      # 1. 拉起 loki + alloy + grafana（首次需下載映像檔）
python log_generator.py                   # 2. 開始寫入鐵人商城日誌到 ./logs/app.log
# 3. 瀏覽器開 http://localhost:3000 → Explore → 資料源選 Loki → 切 Code 模式
#    查 {job="shop-api"} 即可見日誌流入
```

關閉：`docker compose down`（注意：Loki 資料存 /tmp、Alloy 的 positions 存於容器內，`down` 後皆會清空）。

## 版本（本章實測）

| 元件 | 映像檔 |
| --- | --- |
| Loki | `grafana/loki:3.7.4` |
| Alloy | `grafana/alloy:v1.18.0` |
| Grafana | `grafana/grafana:12.4.6` |

## 埠位

| 埠 | 服務 | 用途 |
| --- | --- | --- |
| 3000 | Grafana | 視覺化網頁介面 |
| 3100 | Loki | 接收日誌、回應查詢的 HTTP API |
| 12345 | Alloy | 收集管線的 Web UI（`/graph`） |

## 資料流驗證與斷流巡檢

| 環節 | 檢查指令 |
| --- | --- |
| 應用端有在寫？ | `wc -l logs/app.log`（隔幾秒看兩次是否增加） |
| Alloy 有在收？ | `docker logs lgtm-alloy`（找 `start tailing file`）或開 `localhost:12345/graph` |
| Loki 有收下？ | `curl localhost:3100/ready`、`curl localhost:3100/loki/api/v1/labels` |
| Grafana 查得到？ | Explore 查 `{job="shop-api"}`；查無先把時間範圍拉大 |

斷流演習：`docker compose stop alloy` → 觀察 `app.log` 仍增長但 Grafana 停止更新 → `docker compose start alloy` 恢復（容器保留時，Alloy 靠 positions 從斷點續傳）。

> 本目錄的截圖與數據，均為本機實際部署所得；因隨機性與時序，重現時的數字會略有差異。

> **埠號衝突提醒**：本堆疊與第 9、10、11、12 章那幾份使用同一組埠（3000／3100／12345）。若其中任何一套還開著，請先到對應目錄執行 `docker compose down`，再回來啟動本章這套。

## 授權

本目錄程式碼為本書原創。`loki-config.yaml` 的單機精簡設定與 `grafana-datasources.yaml`
的資料源佈建格式，改編自 Grafana 官方文件（Loki 部署：
<https://grafana.com/docs/loki/latest/setup/install/docker/>；Grafana 資料源佈建：
<https://grafana.com/docs/grafana/latest/administration/provisioning/>）。
所用工具的授權清單見專案根目錄的 `NOTICE.md`。
