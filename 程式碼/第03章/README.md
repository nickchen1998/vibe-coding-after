# 第 3 章程式碼：Hello Locust

本目錄是第 3 章的可執行範例——一個被壓測的 FastAPI 靶場，以及第一支 Locust 腳本。

## 檔案

- `target_app.py`：示範靶場，提供三個特性不同的端點（首頁、模擬 DB 查詢、模擬結帳）。
- `locustfile.py`：第一支 Locust 腳本，示範 `HttpUser`、`@task` 與權重。

## 執行步驟

建議在虛擬環境中安裝相依套件：

```bash
pip install "locust" "fastapi" "uvicorn[standard]"
```

### 1. 啟動靶場（終端機 A）

```bash
uvicorn target_app:app --host 127.0.0.1 --port 8000
```

### 2. 發動壓測（終端機 B）

無介面模式，結果直接印在終端機：

```bash
locust -f locustfile.py --host http://127.0.0.1:8000 \
       --headless --users 50 --spawn-rate 10 --run-time 30s
```

或啟動 Web UI（瀏覽器開 http://localhost:8089）：

```bash
locust -f locustfile.py --host http://127.0.0.1:8000
```

> 書中所有數據與截圖均為本機實際執行 Locust 2.45 的真實結果，因含隨機延遲與失敗率，讀者重現時數字會略有不同。
