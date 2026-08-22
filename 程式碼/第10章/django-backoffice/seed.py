"""灌入示範資料：50 位買家、50 筆物流、50 張訂單。"""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backoffice.settings")
django.setup()

from orders.models import Customer, Order, Shipment

Order.objects.all().delete(); Customer.objects.all().delete(); Shipment.objects.all().delete()
NAMES = ["陳", "林", "黃", "張", "李", "王", "吳", "劉", "蔡", "楊"]
STATUS = ["已出貨", "配送中", "已送達", "待出貨"]
for i in range(1, 51):
    c = Customer.objects.create(name=f"{NAMES[i % 10]}小明{i:02d}")
    s = Shipment.objects.create(tracking_no=f"TW{i:08d}", status=STATUS[i % 4])
    Order.objects.create(order_no=f"A{i:05d}", amount=100 * i, customer=c, shipment=s)
print("買家", Customer.objects.count(), "物流", Shipment.objects.count(), "訂單", Order.objects.count())
