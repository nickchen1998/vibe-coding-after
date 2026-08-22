# 開源工具致謝與授權

本書範例大量使用以下開源工具。書中僅「使用」這些工具（透過其公開 API、CLI 與官方映像檔），未散布其原始碼；相關授權標示於此供讀者參考。書中若引用官方設定檔或文件段落，會於該處另行標註出處。

| 工具 | 用途 | 授權 |
| --- | --- | --- |
| [Locust](https://github.com/locustio/locust) | 壓力測試 | MIT |
| [FastAPI](https://github.com/fastapi/fastapi) | 示範靶場 Web 框架 | MIT |
| [Grafana](https://github.com/grafana/grafana) | 監控視覺化 | AGPL-3.0 |
| [Loki](https://github.com/grafana/loki) | 日誌聚合 | AGPL-3.0 |
| [Tempo](https://github.com/grafana/tempo) | 分散式追蹤 | AGPL-3.0 |
| [Mimir](https://github.com/grafana/mimir) | 指標儲存 | AGPL-3.0 |
| [Prometheus](https://github.com/prometheus/prometheus) | 指標蒐集 | Apache-2.0 |
| [Grafana Alloy](https://github.com/grafana/alloy) | 日誌收集器（取代已 EOL 的 Promtail） | Apache-2.0 |
| [Starlette](https://github.com/encode/starlette) | FastAPI 的 ASGI 底盤、中介層基底 | BSD-3-Clause |
| [uvicorn](https://github.com/encode/uvicorn) | ASGI 伺服器 | BSD-3-Clause |
| [httpx](https://github.com/encode/httpx) | 非同步 HTTP 用戶端（跨服務轉發） | BSD-3-Clause |
| [Django](https://github.com/django/django) | 示範靶場 Web 框架 | BSD-3-Clause |
| [Flask](https://github.com/pallets/flask) | 示範靶場 Web 框架 | BSD-3-Clause |
| [Werkzeug](https://github.com/pallets/werkzeug) | Flask 的 WSGI 底層工具箱 | BSD-3-Clause |
| [Jinja](https://github.com/pallets/jinja) | Flask 的模板引擎 | BSD-3-Clause |
| [asgiref](https://github.com/django/asgiref) | ASGI／WSGI 轉接工具 | BSD-3-Clause |
| [Pydantic](https://github.com/pydantic/pydantic) | FastAPI 的資料驗證引擎 | MIT |
| [PostgreSQL](https://www.postgresql.org/) | 第 7 章靶場的資料庫（`postgres:16` 官方映像） | PostgreSQL License |
| [asyncpg](https://github.com/MagicStack/asyncpg) | 連接 PostgreSQL 的非同步驅動 | Apache-2.0 |
| [Faker](https://github.com/joke2k/faker) | 壓測用的擬真假資料生成（5.1） | MIT |
| [Poetry](https://github.com/python-poetry/poetry) | Python 專案與相依管理（全書的軍需官） | MIT |
| [mcp-grafana](https://github.com/grafana/mcp-grafana) | 讓 AI 透過 MCP 讀取 Grafana（終章 12.3） | Apache-2.0 |

本專案 `程式碼/` 目錄下的原創範例程式碼以 **MIT** 授權釋出，詳見 [LICENSE](LICENSE)。書籍正文文字與插圖的著作權另行保留，不在該授權範圍內。
