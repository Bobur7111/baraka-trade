from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random


# =========================
# CATEGORY
# =========================

class Category(models.Model):
    name_uz = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    name_ru = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name_uz

    def get_name(self, lang="uz"):
        return getattr(self, f"name_{lang}", None) or self.name_uz


# =========================
# PRODUCT
# =========================

class Product(models.Model):

    name_uz = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, null=True)
    name_ru = models.CharField(max_length=255, blank=True, null=True)

    description_uz = models.TextField(blank=True)
    description_en = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    image = models.ImageField(upload_to="products/", blank=True, null=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name_uz

    def get_name(self, lang="uz"):
        return getattr(self, f"name_{lang}", None) or self.name_uz

    def get_description(self, lang="uz"):
        return getattr(self, f"description_{lang}", None) or self.description_uz


# =========================
# CART
# =========================

class CartItem(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name_uz} x {self.quantity}"

    def total_price(self):
        return self.product.price * self.quantity


# =========================
# ADMIN PROFILE
# =========================

class AdminProfile(models.Model):

    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    photo = models.ImageField(upload_to="admin_photos/")
    address = models.TextField()

    def __str__(self):
        return self.full_name


# =========================
# USER PROFILE (ROLE)
# =========================

class Profile(models.Model):

    ROLE_CHOICES = (
        ('retailer', 'Retailer'),
        ('distributor', 'Distributor'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='retailer'
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


# =========================
# B2B REQUEST
# =========================

class B2BRequest(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlandi'),
        ('shipped', 'Yuborildi'),
        ('delivered', 'Yetkazildi'),
    )

    retailer = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.retailer.username} - {self.product.name_uz}"


# =========================
# RESTOCK REQUEST
# =========================

class RestockRequest(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
    )

    retailer = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.retailer.username} - {self.product.name_uz}"


# =========================
# ORDER
# =========================

class Order(models.Model):

    ORDER_TYPE = (
        ("b2b", "B2B"),
        ("b2c", "B2C"),
    )

    STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
    )

    retailer = models.ForeignKey(User, on_delete=models.CASCADE)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    order_type = models.CharField(
        max_length=10,
        choices=ORDER_TYPE,
        default="b2c"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.retailer}"


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name_uz} x {self.quantity}"

class SupplyRequest(models.Model):

    STATUS = (
        ("pending", "Pending"),
        ("sent", "Sent"),
    )

    retailer = models.ForeignKey(User, on_delete=models.CASCADE)

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )

    def __str__(self):
        return f"{self.product} request"


# =========================
# DELIVERY
# =========================

class Delivery(models.Model):

    STATUS = (
        ("active", "Active"),
        ("completed", "Completed"),
    )

    request = models.ForeignKey(SupplyRequest, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS)

    def __str__(self):
        return f"Delivery {self.request.id}"
class WarehouseLog(models.Model):

    ACTIONS = (
        ("in", "Stock In"),
        ("out", "Stock Out"),
    )

    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    quantity = models.IntegerField()
    action = models.CharField(max_length=10, choices=ACTIONS)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name_uz} - {self.action} ({self.quantity})"
class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    message = models.CharField(max_length=255)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

class ProductVoice(models.Model):
    CATEGORY_CHOICES = (
        ("phone", "Phone"),
        ("accessory", "Accessory"),
    )

    name = models.CharField(max_length=255)
    price = models.IntegerField()
    ram = models.IntegerField(null=True, blank=True)
    brand = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.name

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to="restaurants/")
    description = models.TextField(blank=True)

    latitude = models.FloatField()
    longitude = models.FloatField()

    rating = models.FloatField(default=5)

    def __str__(self):
        return self.name


class Food(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="foods/")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Courier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


def generate_order_code():
    return str(random.randint(100000, 999999))


class FoodOrder(models.Model):

    code = models.CharField(max_length=6, default=generate_order_code)

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    courier = models.ForeignKey(Courier, null=True, blank=True, on_delete=models.SET_NULL)

    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)

    latitude = models.FloatField()
    longitude = models.FloatField()

    status = models.CharField(max_length=50, default="new")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FoodOrder {self.code}"


class FoodOrderItem(models.Model):

    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE)

    food = models.ForeignKey(Food, on_delete=models.CASCADE)

    quantity = models.IntegerField(default=1)

    def __str__(self):
        return self.food.name

class PaymentOTP(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20)

    code = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone} - {self.code}"