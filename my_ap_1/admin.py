# # my_ap_1/admin.py
# from django.contrib import admin
# from .models import Product
#
# admin.site.register(Product)
from django.contrib import admin
from .models import Product, Category
from .models import AdminProfile
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(AdminProfile)