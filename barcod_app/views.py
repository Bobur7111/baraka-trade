from itertools import product
from urllib import request

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import BarcodeItem, OfflineSale, OfflineSaleItem
from my_ap_1.models import Product
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from .telegram_utils import send_telegram_message
from django.utils import timezone

from .models import BarcodeItem
from .utils import generate_barcode_png

@login_required
@csrf_exempt
def pos_scan_sell(request):

    barcode = request.POST.get("barcode")

    try:
        barcode_item = BarcodeItem.objects.filter(barcode=barcode).first()

        if not barcode_item:
            return JsonResponse({"error": "Barcode topilmadi"})
        product = barcode_item.product
    except BarcodeItem.DoesNotExist:
        return JsonResponse({"error": "Barcode not found"})

    if product.stock <= 0:
        return JsonResponse({"error": "Stock empty"})

    # stock kamayadi
    product.stock -= 1
    product.save()

    # sale yaratamiz
    sale = OfflineSale.objects.create(
        seller=request.user,
        total_price=product.price
    )

    OfflineSaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=1,
        price=product.price
    )

    return JsonResponse({
        "success": True,
        "product": product.name_uz,
        "price": float(product.price),
        "stock": product.stock
    })

@login_required
def pos_terminal(request):
    return render(request,"pos_terminal.html")



def barcode_png_view(request, product_id):

    barcode_item = get_object_or_404(BarcodeItem, product_id=product_id)

    path = generate_barcode_png(barcode_item.barcode)

    return FileResponse(open(path, "rb"), content_type="image/png")


def barcode_pdf_view(request, product_id):

    barcode_item = get_object_or_404(BarcodeItem, product_id=product_id)

    path = generate_barcode_png(barcode_item.barcode)

    pdf_path = path.replace(".png", ".pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)

    c.drawString(100, 750, barcode_item.product.name_uz)
    c.drawImage(path, 100, 650, width=300, height=100)

    c.save()

    return FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
@login_required
@csrf_exempt
def pos_scan_sell(request):
    barcode = request.POST.get("barcode", "").strip()

    barcode_item = BarcodeItem.objects.get(barcode=barcode)
    product = barcode_item.product

    if product.stock <= 0:
        return JsonResponse({"error": "Stock empty"})

    product.stock -= 1
    product.save()

    sale = OfflineSale.objects.create(
        seller=request.user,
        total_price=product.price
    )

    OfflineSaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=1,
        price=product.price
    )
    # Telegram xabar
    time_now = timezone.now().strftime("%H:%M")

    message = f"""
🛒 YANGI SOTUV!

📦 Mahsulot: {product.name_uz}
💰 Narxi: {product.price} so'm
📉 Omborda qoldi: {product.stock} ta

👤 Sotuvchi: {request.user.username}
⏰ Vaqt: {time_now}

📊 Baraka Market POS
"""

    send_telegram_message(
        7191312648,
        message
    )
    if product.stock <= 3:

        send_telegram_message(
            7191312648,
            f"""
⚠ DIQQAT!

📦 {product.name_uz}

Omborda juda kam qoldi!
Qolgan: {product.stock} ta
"""
        )