"""第 11 章｜本機告警接收器

Grafana 的聯絡點（Contact point）支援多種通知管道。本書為了讓讀者不必
申請任何外部服務就能親眼看見「通知長什麼樣」，準備了這支極簡的接收器：
它就是一個會把收到的內容原樣印出來的網址。

啟動：python webhook_sink.py
Grafana 的聯絡點指向：http://host.docker.internal:9099/alert
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class SinkHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

        print("\n" + "=" * 68)
        try:
            payload = json.loads(raw)
            print(f"警報狀態：{payload.get('status')}｜共 {len(payload.get('alerts', []))} 則")
            for a in payload.get("alerts", []):
                labels = a.get("labels", {})
                ann = a.get("annotations", {})
                print(f"  規則：{labels.get('alertname')}")
                print(f"  狀態：{a.get('status')}")
                print(f"  摘要：{ann.get('summary', '（無）')}")
                print(f"  說明：{ann.get('description', '（無）')}")
                print(f"  觸發時間：{a.get('startsAt')}")
        except json.JSONDecodeError:
            print(raw[:800])
        print("=" * 68)

    def log_message(self, *args):
        pass          # 關掉預設的存取紀錄，畫面才乾淨


if __name__ == "__main__":
    print("告警接收器待命中：http://127.0.0.1:9099/alert（Ctrl+C 結束）")
    HTTPServer(("0.0.0.0", 9099), SinkHandler).serve_forever()
