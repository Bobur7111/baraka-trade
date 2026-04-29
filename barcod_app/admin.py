from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BarcodeItem,
    OfflineSale,
    OfflineSaleItem
)


# ==============================
# BARCODE ADMIN
# ==============================

@admin.register(BarcodeItem)
class BarcodeItemAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "barcode",
        "print_png",
        "print_pdf",
        "created_at",
    )

    search_fields = (
        "product__name_uz",
        "barcode",
    )

    readonly_fields = (
        "barcode",
        "created_at",
    )

    def print_png(self, obj):

        return format_html(
            '<a class="button" href="/barcode/png/{}/">PNG</a>',
            obj.product.id
        )

    print_png.short_description = "Print PNG"

    def print_pdf(self, obj):

        return format_html(
            '<a class="button" href="/barcode/pdf/{}/">PDF</a>',
            obj.product.id
        )

    print_pdf.short_description = "Print PDF"


# ==============================
# OFFLINE SALE ITEMS INLINE
# ==============================

class OfflineSaleItemInline(admin.TabularInline):

    model = OfflineSaleItem

    extra = 0


# ==============================
# OFFLINE SALE ADMIN
# ==============================

@admin.register(OfflineSale)
class OfflineSaleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "seller",
        "total_price",
        "created_at",
    )

    list_filter = (
        "created_at",
        "seller",
    )

    search_fields = (
        "seller__username",
    )

    inlines = [
        OfflineSaleItemInline
    ]


# ==============================
# OFFLINE SALE ITEM ADMIN
# ==============================

@admin.register(OfflineSaleItem)
class OfflineSaleItemAdmin(admin.ModelAdmin):

    list_display = (
        "sale",
        "product",
        "quantity",
        "price",
    )

    search_fields = (
        "product__name_uz",
    )