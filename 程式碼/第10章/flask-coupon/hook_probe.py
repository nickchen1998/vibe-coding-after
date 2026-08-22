"""第 10 章 10.3｜Flask 三個鉤子的執行保證實證

同一支會拋例外的視圖，在「正式模式」與「除錯模式」下各打一次，
把三個鉤子的出場序列印出來——差別會讓你嚇一跳。

執行：python hook_probe.py
"""

from flask import Flask, g


def build_app(debug: bool) -> Flask:
    app = Flask(__name__)
    app.debug = debug

    @app.before_request
    def _before():
        g.marks = ["before_request"]
        print("  before_request     ← 訪客進城")

    @app.after_request
    def _after(response):
        print(f"  after_request      ← 回應要出城了，狀態碼 {response.status_code}")
        return response

    @app.teardown_request
    def _teardown(exc):
        print(f"  teardown_request   ← 收場，例外是 {exc!r}")

    @app.route("/boom")
    def boom():
        raise ValueError("券碼格式無法解析")

    return app


def run(debug: bool) -> None:
    label = "除錯模式（debug=True）" if debug else "正式模式（debug=False）"
    print(f"\n=== {label} ===")
    app = build_app(debug)
    client = app.test_client()
    try:
        resp = client.get("/boom")
        print(f"  用戶端收到：HTTP {resp.status_code}")
    except Exception as e:
        print(f"  例外被重新拋給了伺服器：{type(e).__name__}: {e}")


if __name__ == "__main__":
    run(debug=False)
    run(debug=True)
