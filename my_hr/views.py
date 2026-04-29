from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal

from .models import Employee
from barcod_app.models import OfflineSale  # 🔥 TO‘G‘RI MODEL

@login_required
def hr_dashboard(request):

    try:
        me = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        me = None

    # 🔥 faqat o‘zini sales
    total_sales = OfflineSale.objects.filter(
        seller=request.user
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')

    # 🔥 BONUS
    if total_sales >= Decimal('5000000'):
        bonus = total_sales * Decimal('0.15')
    elif total_sales >= Decimal('3000000'):
        bonus = total_sales * Decimal('0.10')
    elif total_sales >= Decimal('1000000'):
        bonus = total_sales * Decimal('0.05')
    else:
        bonus = Decimal('0')

    # 🔥 salary
    total_salary = (me.base_salary if me else 0) + bonus

    # 🔥 recent sales
    recent_sales = OfflineSale.objects.filter(
        seller=request.user
    ).order_by('-created_at')[:5]

    return render(request, 'hr/dashboard.html', {
        'employees': [{
            'employee': me,
            'sales': total_sales,
            'bonus': bonus,
            'salary': total_salary
        }],
        'me': me,
        'recent_sales': recent_sales
    })