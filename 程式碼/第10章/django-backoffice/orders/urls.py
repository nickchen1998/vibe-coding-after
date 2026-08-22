from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.order_list_naive, name="order-list-naive"),
    path("orders/fast/", views.order_list_optimized, name="order-list-optimized"),
    path("orders/<str:order_no>/", views.order_detail, name="order-detail"),
    path("orders/<str:order_no>/refund/", views.order_refund, name="order-refund"),
]
