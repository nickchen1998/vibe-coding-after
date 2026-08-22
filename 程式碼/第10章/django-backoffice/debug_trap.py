"""第 10 章 10.2｜connection.queries 的 DEBUG 陷阱實證

同一段程式碼、同一批查詢，只因為 settings 裡一個布林值不同，
connection.queries 就會從「101 筆」變成「0 筆」——而且不會報任何錯。
execute_wrapper 則兩種情況下都算得準。

執行：python debug_trap.py
"""

import os

import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backoffice.settings")
django.setup()

from django.db import connection  # noqa: E402

from orders.models import Order  # noqa: E402
from orders.monitoring import QueryCounter  # noqa: E402


def touch_orders() -> int:
    """翻一頁點名冊：每一列都碰一次買家與物流，製造 N+1。"""
    n = 0
    for o in Order.objects.all()[:50]:
        _ = o.customer.name
        _ = o.shipment.status
        n += 1
    return n


def probe(debug: bool) -> None:
    settings.DEBUG = debug
    connection.queries_log.clear()

    counter = QueryCounter()
    with connection.execute_wrapper(counter):
        rows = touch_orders()

    print(f"  DEBUG = {str(debug):<5}｜翻了 {rows} 列"
          f"｜connection.queries 說 {len(connection.queries):>3} 次"
          f"｜execute_wrapper 說 {counter.count:>3} 次")


if __name__ == "__main__":
    print("同一段程式碼，同一批查詢，只有 DEBUG 不同：\n")
    probe(True)
    probe(False)
    print("\n  connection.queries 在 DEBUG=False 時靜默歸零，不會拋任何錯誤；")
    print("  execute_wrapper 與 DEBUG 無關，兩種情況下都算得準。")
