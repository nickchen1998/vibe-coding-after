"""鐵人商城後台：訂單點名冊的資料模型。

三張表刻意設計成有關聯：一筆訂單指向一位買家（多對一），
並各自對應一筆物流紀錄（一對一）。這兩種關聯，正是 N+1 查詢的溫床。
"""

from django.db import models


class Customer(models.Model):
    """買家。"""
    name = models.CharField("姓名", max_length=50)

    def __str__(self) -> str:
        return self.name


class Shipment(models.Model):
    """物流紀錄：一筆訂單對應一筆。"""
    tracking_no = models.CharField("物流單號", max_length=30)
    status = models.CharField("配送狀態", max_length=20)

    def __str__(self) -> str:
        return f"{self.tracking_no}（{self.status}）"


class Order(models.Model):
    """訂單：點名冊上的一列。"""
    order_no = models.CharField("訂單編號", max_length=20, unique=True)
    amount = models.IntegerField("金額")
    created_at = models.DateTimeField("成立時間", auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="買家")
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, verbose_name="物流")

    def __str__(self) -> str:
        return self.order_no
