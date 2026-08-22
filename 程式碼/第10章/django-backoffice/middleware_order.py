"""第 10 章 10.2｜Django 中介層的出場順序實證

Django 官方文件以洋蔥比喻中介層：請求階段由 MIDDLEWARE 清單「由上而下」
穿入，回應階段再「由下而上」穿出。這支腳本把那個順序印出來。

執行：python middleware_order.py
"""

import os

import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backoffice.settings")
django.setup()

from django.test import Client  # noqa: E402


class OrderProbe:
    """一位只會喊口令的守衛。子類別各自帶一個名字。"""
    name = "?"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"守衛 {self.name}：進入")
        response = self.get_response(request)
        print(f"守衛 {self.name}：離開")
        return response


class ProbeA(OrderProbe):
    name = "A"


class ProbeB(OrderProbe):
    name = "B"


if __name__ == "__main__":
    settings.MIDDLEWARE = [
        "middleware_order.ProbeA",     # 清單上方
        "middleware_order.ProbeB",     # 清單下方
    ]
    print("settings.MIDDLEWARE 由上而下：A、B")
    print("---- 發出一次請求 ----")
    Client().get("/orders/fast/")
