from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from my_hr.utils import calculate_bonus
from barcod_app.models import OfflineSale
class Employee(models.Model):
    ROLE_CHOICES = (
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    image = models.ImageField(upload_to='employees/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seller')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(blank=True, null=True)

    def total_hours(self):
        if self.check_out:
            return (self.check_out - self.check_in).total_seconds() / 3600
        return 0


def save(self, *args, **kwargs):
    total = OfflineSale.objects.filter(
        seller=self.employee.user
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')

    self.total_sales = total
    self.bonus = calculate_bonus(total)
    self.total_salary = self.employee.base_salary + self.bonus

    super().save(*args, **kwargs)