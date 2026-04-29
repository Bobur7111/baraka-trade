from django.urls import path
from .import views

urlpatterns = [

    path("pos-terminal/", views.pos_terminal, name="pos_terminal"),

    path("pos-scan/", views.pos_scan_sell, name="pos_scan_sell"),
    path(
        "barcode/png/<int:product_id>/",
        views.barcode_png_view,
        name="barcode_png"
    ),

    path(
        "barcode/pdf/<int:product_id>/",
        views.barcode_pdf_view,
        name="barcode_pdf"
    ),
    path("pos-scan/", views.pos_scan_sell),

]
