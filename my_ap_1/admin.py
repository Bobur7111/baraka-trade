from django.contrib import admin
from .models import *
from django.contrib import admin
from .models import WarehouseLog

admin.site.register(WarehouseLog)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "retailer", "total_price", "created_at")
    inlines = [OrderItemInline]


admin.site.register(Product)
admin.site.register(Category)
admin.site.register(AdminProfile)
admin.site.register(Profile)
admin.site.register(B2BRequest)
admin.site.register(RestockRequest)
admin.site.register(SupplyRequest)
admin.site.register(Delivery)
admin.site.register(ProductVoice)

admin.site.register(Restaurant)
admin.site.register(Food)
admin.site.register(Courier)
admin.site.register(FoodOrder)
admin.site.register(FoodOrderItem)

admin.site.register(Order, OrderAdmin)