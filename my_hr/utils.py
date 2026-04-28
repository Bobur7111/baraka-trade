from decimal import Decimal

def calculate_bonus(total_sales):
    total_sales = Decimal(total_sales)

    if total_sales >= Decimal('5000000'):
        return total_sales * Decimal('0.15')
    elif total_sales >= Decimal('3000000'):
        return total_sales * Decimal('0.10')
    elif total_sales >= Decimal('1000000'):
        return total_sales * Decimal('0.05')
    return Decimal('0')