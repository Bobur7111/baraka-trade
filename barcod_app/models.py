import uuid
from django.db import models
from django.contrib.auth.models import User
from my_ap_1.models import Product


def generate_barcode():
    return str(uuid.uuid4()).replace("-", "")[:12]


class BarcodeItem(models.Model):

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="barcode_item"
    )

    barcode = models.CharField(
        max_length=20,
        unique=True,
        default=generate_barcode
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name_uz} | {self.barcode}"


class OfflineSale(models.Model):

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offline Sale {self.id}"


class OfflineSaleItem(models.Model):

    sale = models.ForeignKey(
        OfflineSale,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField(default=1)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.product.name_uz