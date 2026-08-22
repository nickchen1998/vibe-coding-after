"""後台訂單點名冊的兩種寫法：天真版與正解版。"""

from django.http import JsonResponse

from .models import Order


def order_list_naive(request):
    """天真版：每翻一頁，就向資料庫索取 101 次補給。

    Order.objects.all() 只發一次查詢取回 50 筆訂單，
    但迴圈裡每碰一次 o.customer 與 o.shipment，Django 就得再跑一趟資料庫——
    這就是 N+1：1 次主查詢，加上 N 次（此處是 50×2）額外查詢。
    """
    rows = []
    for o in Order.objects.all()[:50]:
        rows.append({
            "order_no": o.order_no,
            "customer": o.customer.name,          # ← 每一列各一次查詢
            "shipment": o.shipment.status,        # ← 每一列再一次查詢
            "amount": o.amount,
        })
    return JsonResponse({"rows": rows})


def order_list_optimized(request):
    """正解版：一次把買家與物流一起撈回來。

    select_related 讓 Django 以 JOIN 把關聯資料一次帶回，
    整頁只需一次查詢。判準已於第 7 章詳述：正向的 ForeignKey
    與 OneToOneField 用 select_related。
    """
    rows = []
    for o in Order.objects.select_related("customer", "shipment").all()[:50]:
        rows.append({
            "order_no": o.order_no,
            "customer": o.customer.name,
            "shipment": o.shipment.status,
            "amount": o.amount,
        })
    return JsonResponse({"rows": rows})


def order_detail(request, order_no):
    """單筆訂單查詢：查無此單就明白地回 404。"""
    order = Order.objects.filter(order_no=order_no).first()
    if order is None:
        return JsonResponse({"detail": "查無此訂單"}, status=404)
    return JsonResponse({"order_no": order.order_no, "amount": order.amount})


def order_refund(request, order_no):
    """退款：刻意留著一個未捕捉的例外，用來檢驗守衛在出事時還在不在崗位上。"""
    order = Order.objects.get(order_no=order_no)   # 查無此單會拋 Order.DoesNotExist
    raise RuntimeError(f"退款閘道無回應：{order.order_no}")
