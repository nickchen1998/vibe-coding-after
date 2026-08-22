from django.contrib import admin

from .models import Customer, Order, Shipment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "customer", "amount", "shipment")
    search_fields = ("order_no",)


admin.site.register(Customer)
admin.site.register(Shipment)

admin.site.site_header = "鐵人商城後台"
admin.site.site_title = "鐵人商城後台"
admin.site.index_title = "營運管理"
