from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name_uz = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    name_ru = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name_uz

    def get_name(self, lang="uz"):
        return getattr(self, f"name_{lang}", None) or self.name_uz


class Product(models.Model):
    name_uz = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    name_ru = models.CharField(max_length=255, blank=True, null=True)

    description_uz = models.TextField(blank=True)
    description_en = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name_uz

    def get_name(self, lang="uz"):
        return getattr(self, f"name_{lang}", None) or self.name_uz

    def get_description(self, lang="uz"):
        return getattr(self, f"description_{lang}", None) or self.description_uz


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name_uz} x {self.quantity}"

    def total_price(self):
        return self.product.price * self.quantity


class AdminProfile(models.Model):
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    photo = models.ImageField(upload_to="admin_photos/")
    address = models.TextField()

    def __str__(self):
        return self.full_name
