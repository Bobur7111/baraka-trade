from django.contrib import admin
from .models import *
from .models import WarehouseLog
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = ("name_uz", "price", "stock", "category")
    search_fields = ("name_uz",)
    list_filter = ("category",)


admin.site.register(Category)
admin.site.register(AdminProfile)
admin.site.register(Profile)
admin.site.register(B2BRequest)
admin.site.register(RestockRequest)
admin.site.register(Order)
admin.site.register(SupplyRequest)
admin.site.register(Delivery)

@admin.register(WarehouseLog)
class WarehouseLogAdmin(admin.ModelAdmin):
    list_display = ("product", "action", "quantity", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("product__name_uz",)