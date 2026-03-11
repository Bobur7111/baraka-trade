from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.models import User
from .models import WarehouseLog, Notification, OrderItem, PaymentOTP
from .models import  Category, AdminProfile, ProductVoice
from PIL import Image
from .utils import parse_voice_command
import torch
import re
from .models import Food
import random
from django.core.cache import cache
from transformers import CLIPProcessor, CLIPModel
from datetime import timedelta
from .models import Food, FoodOrder, FoodOrderItem
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
IMAGE_FOLDER = "media/products"

device = "cuda" if torch.cuda.is_available() else "cpu"

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


CATEGORIES = {
    "Ko'zoynaklar": ["glasses", "sunglasses", "eyeglasses"],
    "Mobile Telefonlar": ["smartphone", "mobile phone", "iphone"],
    "Soatlar": ["watch", "clock"],
    "Naushnik va aerpotslar": ["earbuds", "airpods", "headphones"],
    "Kalonkalar": ["speaker", "bluetooth speaker"]
}

def detect_category(image):

    texts = []
    mapping = []

    for cat, words in CATEGORIES.items():
        for w in words:
            texts.append(f"a photo of {w}")
            mapping.append(cat)

    inputs = processor(
        text=texts,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    probs = outputs.logits_per_image.softmax(dim=1)

    best = probs.argmax().item()

    return mapping[best]


def search_ai(request):

    result = []
    detected_category = None

    if request.method == "POST":

        image_file = request.FILES.get("image")

        if image_file:

            image = Image.open(image_file).convert("RGB")

            category = detect_category(image)

            print("Detected:", category)

            detected_category = category

            result = Product.objects.filter(
                category__name_uz__icontains=category
            )

    return render(
        request,
        "search_ai.html",
        {
            "result": result,
            "detected_category": detected_category
        }
    )
# =========================
# 🛒 CART HELPERS
# =========================
def get_cart_count(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).count()
    cart = request.session.get("cart", {})
    return sum(cart.values())


def get_cart_items_and_total(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user)
        cart_items = [{
            "product": item.product,
            "quantity": item.quantity,
            "item_total": item.total_price()
        } for item in items]
        total_price = sum(i["item_total"] for i in cart_items)
    else:
        cart = request.session.get("cart", {})
        cart_items = []
        total_price = 0
        for pid, qty in cart.items():
            try:
                product = Product.objects.get(id=pid)
                total = product.price * qty
                total_price += total
                cart_items.append({
                    "product": product,
                    "quantity": qty,
                    "item_total": total
                })
            except Product.DoesNotExist:
                pass
    return cart_items, total_price


# =========================
# 🏠 HOME
# =========================
def home_view(request):
    query = request.GET.get("q")

    products = Product.objects.all()
    if query:
        products = products.filter(
            Q(name_uz__icontains=query) |
            Q(name_en__icontains=query) |
            Q(name_ru__icontains=query) |
            Q(description_uz__icontains=query) |
            Q(description_en__icontains=query) |
            Q(description_ru__icontains=query)
        )

    categories = Category.objects.all()
    admin_info = AdminProfile.objects.first()

    return render(request, "home.html", {
        "products": products,
        "categories": categories,
        "admin_info": admin_info,
        "cart_item_count": get_cart_count(request)
    })


# =========================
# 📂 CATEGORY PRODUCTS
# =========================
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    categories = Category.objects.all()

    return render(request, "home.html", {
        "products": products,
        "categories": categories,
        "selected_category": category,   # ✅ object
        "cart_item_count": get_cart_count(request)
    })


# =========================
# 📦 PRODUCT DETAIL
# =========================
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "product_detail.html", {
        "product": product,
        "cart_item_count": get_cart_count(request)
    })


# =========================
# 🛒 CART VIEWS
# =========================
def cart_view(request):
    cart_items, total_price = get_cart_items_and_total(request)
    return render(request, "cart.html", {
        "cart_items": cart_items,
        "total_price": total_price,
        "cart_item_count": get_cart_count(request)
    })


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        if not created:
            item.quantity += 1
            item.save()
    else:
        cart = request.session.get("cart", {})
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        request.session["cart"] = cart

    return redirect(request.META.get("HTTP_REFERER", "/"))


def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        item = CartItem.objects.filter(
            user=request.user,
            product_id=product_id
        ).first()
        if item:
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()
    else:
        cart = request.session.get("cart", {})
        pid = str(product_id)
        if pid in cart:
            cart[pid] -= 1
            if cart[pid] <= 0:
                del cart[pid]
        request.session["cart"] = cart

    return redirect("cart_view")


def delete_from_cart(request, product_id):
    if request.user.is_authenticated:
        CartItem.objects.filter(
            user=request.user,
            product_id=product_id
        ).delete()
    else:
        cart = request.session.get("cart", {})
        cart.pop(str(product_id), None)
        request.session["cart"] = cart

    return redirect("cart_view")


def clear_cart(request):
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user).delete()
    else:
        request.session["cart"] = {}
    return redirect("cart_view")
def update_cart(request, product_id):
    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        if request.user.is_authenticated:
            item = CartItem.objects.filter(
                user=request.user,
                product_id=product_id
            ).first()

            if item:
                if quantity > 0:
                    item.quantity = quantity
                    item.save()
                else:
                    item.delete()
        else:
            cart = request.session.get("cart", {})
            pid = str(product_id)

            if quantity > 0:
                cart[pid] = quantity
            else:
                cart.pop(pid, None)

            request.session["cart"] = cart

    return redirect("cart_view")


def about_view(request):
    admin_info = AdminProfile.objects.first()
    return render(request, "about.html", {
        "admin_info": admin_info,
        "cart_item_count": get_cart_count(request)
    })


#
# # =========================
# # 💬 CHATBOT
# # =========================
# def chat_with_ai(request):
#     if request.method == "POST":
#         import json
#         data = json.loads(request.body)
#         user_input = data.get("user_input", "")
#
#         if not user_input:
#             return JsonResponse({"answer": "Savol bo‘sh!"})
#
#         response = openai.ChatCompletion.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": user_input}],
#             temperature=0.7
#         )
#
#         return JsonResponse({
#             "answer": response.choices[0].message["content"]
#         })
#
#     return render(request, "chatbot.html", {
#         "cart_item_count": get_cart_count(request)
#     })
#
#

from django.shortcuts import render
from django.http import JsonResponse
from .models import (
    Product,
    CartItem,
    B2BRequest,
    RestockRequest,
    Order,
    SupplyRequest,
    Delivery
)

import json


from django.shortcuts import render
from django.http import JsonResponse
from .models import Product
import json


from django.shortcuts import render
from django.http import JsonResponse
from .models import Product
import json


def chatbot(request):

    if request.method == "POST":

        data = json.loads(request.body)
        message = data.get("message", "").lower()

        price = extract_price(message)

        # TELEFON
        if "telefon" in message:

            products = Product.objects.filter(
                category__name_uz__icontains="telefon"
            )

            # agar narx so'ralgan bo'lsa
            if price:

                filtered = products.filter(price__lte=price)

                # agar topilmasa
                if not filtered.exists():

                    cheapest = products.order_by("price").first()

                    return JsonResponse({
                        "type": "text",
                        "reply": f"Kechirasiz, {price} UZS dan arzon telefon yo‘q. Eng arzoni {cheapest.price} UZS."
                    })

                products = filtered

            products = products.order_by("price")[:5]

            result = []

            for p in products:

                image_url = p.image.url if p.image else ""

                result.append({
                    "id": p.id,
                    "name": str(p),
                    "price": p.price,
                    "image": image_url
                })

            return JsonResponse({
                "type": "products",
                "products": result
            })

        return JsonResponse({
            "type": "text",
            "reply": "Qanday mahsulot kerak? Masalan: telefon, soat yoki naushnik."
        })

    return render(request, "chatbot.html")
@login_required
def create_b2b_request(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    B2BRequest.objects.create(
        retailer=request.user,
        product=product,
        quantity=50
    )

    return redirect("b2b_dashboard")


@login_required
def create_supply_request(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    req = SupplyRequest.objects.create(
        retailer=request.user,
        product=product,
        quantity=10
    )

    # 🔔 notification distributor uchun
    distributors = User.objects.filter(profile__role="distributor")

    for d in distributors:
        Notification.objects.create(
            user=d,
            message=f"New supply request for {product.name_uz}"
        )

    return redirect("b2b_dashboard")


@login_required
def distributor_dashboard(request):

    if request.user.profile.role != "distributor":
        return redirect("home")

    requests = SupplyRequest.objects.all().order_by("-id")

    return render(
        request,
        "b2b/distributor_dashboard.html",
        {
            "requests": requests
        }
    )
def b2b_orders(request):

    orders = B2BRequest.objects.filter(
        retailer=request.user
    ).order_by("-created_at")

    return render(
        request,
        "b2b/orders.html",
        {"orders": orders}
    )
@login_required
def approve_request(request, request_id):

    if request.user.profile.role != "distributor":
        return redirect("home")

    req = get_object_or_404(SupplyRequest, id=request_id)

    req.status = "sent"
    req.save()

    # Delivery yaratamiz
    Delivery.objects.create(
        request=req,
        status="active"
    )

    return redirect("distributor_dashboard")
def low_stock(request):

    products = Product.objects.filter(stock__lt=10)

    return render(
        request,
        "b2b/low_stock.html",
        {"products": products}
    )
from datetime import timedelta
from django.db.models import Sum

from datetime import timedelta

@login_required
def b2b_dashboard(request):

    today = timezone.now().date()

    # 🛒 Bugungi buyurtmalar
    today_orders = Order.objects.filter(
        retailer=request.user,
        created_at__date=today
    )

    today_sales = today_orders.aggregate(
        total=Sum("total_price")
    )["total"] or 0


    # 📉 Kam qolgan mahsulotlar
    low_stock_products = Product.objects.filter(
        stock__lt=10
    ).order_by("stock")

    low_stock_count = low_stock_products.count()


    # 📦 Retailer yuborgan requestlar
    requests_count = SupplyRequest.objects.filter(
        retailer=request.user
    ).count()


    # 🚚 Aktiv yetkazmalar
    active_deliveries = Delivery.objects.filter(
        request__retailer=request.user,
        status="active"
    ).count()


    # 🤖 AI recommendation
    ai_recommendations = Product.objects.order_by("stock")[:3]


    # 📊 7 kunlik sales chart
    sales_labels = []
    sales_data = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        total = Order.objects.filter(
            retailer=request.user,
            created_at__date=day
        ).aggregate(
            total=Sum("total_price")
        )["total"] or 0

        sales_labels.append(day.strftime("%a"))
        sales_data.append(float(total))


    context = {
        "today_sales": today_sales,
        "low_stock_products": low_stock_products,
        "low_stock_count": low_stock_count,
        "requests_count": requests_count,
        "active_deliveries": active_deliveries,
        "ai_recommendations": ai_recommendations,

        "sales_labels": sales_labels,
        "sales_data": sales_data,
    }

    return render(
        request,
        "b2b/b2b_dashboard.html",
        context
    )
@login_required
def sales_analytics(request):

    today = timezone.now().date()

    sales_labels = []
    sales_data = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        total = Order.objects.filter(
            retailer=request.user,
            created_at__date=day
        ).aggregate(
            total=Sum("total_price")
        )["total"] or 0

        sales_labels.append(day.strftime("%a"))
        sales_data.append(float(total))

    context = {
        "sales_labels": sales_labels,
        "sales_data": sales_data
    }

    return render(
        request,
        "b2b/statistics.html",
        context
    )

@login_required
def stock_in(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    quantity = int(request.POST.get("quantity", 1))

    product.stock += quantity
    product.save()

    WarehouseLog.objects.create(
        product=product,
        quantity=quantity,
        action="in",
        note="Manual stock update"
    )

    return redirect("warehouse_dashboard")


@login_required
def stock_out(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    quantity = int(request.POST.get("quantity", 1))

    product.stock -= quantity
    product.save()

    WarehouseLog.objects.create(
        product=product,
        quantity=quantity,
        action="out",
        note="Stock reduced"
    )

    return redirect("warehouse_dashboard")
@login_required
def warehouse_dashboard(request):

    products = Product.objects.all().order_by("stock")

    logs = WarehouseLog.objects.all().order_by("-created_at")[:10]

    context = {
        "products": products,
        "logs": logs
    }

    return render(request, "b2b/warehouse.html", context)

def calculate_restock_predictions(user):

    predictions = []

    today = timezone.now().date()
    last_week = today - timedelta(days=7)

    products = Product.objects.all()

    for product in products:

        sales = OrderItem.objects.filter(
            order__retailer=user,
            product=product,
            order__created_at__date__gte=last_week
        )

        total_sold = sales.aggregate(
            total=Sum("quantity")
        )["total"] or 0

        daily_avg = total_sold / 7 if total_sold else 0

        if daily_avg > 0:

            days_left = product.stock / daily_avg if daily_avg else 0

            if days_left < 5:

                recommended = int(daily_avg * 14)

                predictions.append({
                    "product": product,
                    "daily_avg": round(daily_avg, 2),
                    "days_left": round(days_left, 1),
                    "recommended": recommended
                })

    return predictions
@login_required
def ai_assistant(request):

    today = timezone.now().date()
    last_week = today - timedelta(days=7)

    # eng ko‘p sotilgan mahsulotlar
    top_products = (
        OrderItem.objects.filter(
            order__retailer=request.user
        )
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    # kam qolgan mahsulotlar
    low_stock_products = Product.objects.filter(
        stock__lt=10
    ).order_by("stock")[:5]

    # AI restock prediction
    predictions = calculate_restock_predictions(request.user)

    context = {
        "top_products": top_products,
        "low_stock_products": low_stock_products,
        "predictions": predictions,
    }

    return render(
        request,
        "b2b/ai_assistant.html",
        context
    )
@login_required
def notifications(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "b2b/notifications.html",
        {"notifications": notifications}
    )

@login_required
def sales_analytics(request):

    today = timezone.now().date()

    sales_labels = []
    sales_data = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        total = Order.objects.filter(
            retailer=request.user,
            created_at__date=day
        ).aggregate(
            total=Sum("total_price")
        )["total"] or 0

        sales_labels.append(day.strftime("%a"))
        sales_data.append(float(total))


    # TOP SELLING PRODUCTS
    top_products = (
        OrderItem.objects
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )


    context = {
        "sales_labels": sales_labels,
        "sales_data": sales_data,
        "top_products": top_products
    }

    return render(
        request,
        "b2b/statistics.html",
        context
    )
@login_required
def checkout(request):

    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items:
        return redirect("cart_view")

    total = 0

    # ORDER yaratamiz (payment hali qilinmagan)
    order = Order.objects.create(
        retailer=request.user,
        total_price=0,
        order_type="b2c",
        status="pending"
    )

    for item in cart_items:

        item_total = item.product.price * item.quantity

        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

        total += item_total

    order.total_price = total
    order.save()

    # payment sahifa uchun order id sessionga saqlaymiz
    request.session["payment_order_id"] = order.id

    return redirect("payment_page")

def order_success(request):
    return render(request, "order_success.html")
def voice_search(request):

    body = json.loads(request.body)
    text = body.get("text")

    filters = parse_voice_command(text)

    products = ProductVoice.objects.filter(**filters)[:10]

    data = []

    for p in products:
        data.append({
            "name": p.name,
            "price": p.price,
            "ram": p.ram,
        })

    return JsonResponse({"products": data})

def voice_page(request):
    return render(request, "voice_search.html")
def home(request):

    q = request.GET.get("q")

    products = Product.objects.all()

    if q:

        filters = parse_voice_command(q)

        # CATEGORY FILTER
        if "category" in filters:
            products = products.filter(
                category__name_uz=filters["category"]
            )

        # PRICE FILTER
        if "price__lt" in filters:
            products = products.filter(
                price__lt=filters["price__lt"]
            )

        # RAM FILTER
        if "ram" in filters:
            products = products.filter(
                ram=filters["ram"]
            )

    context = {
        "products": products
    }

    return render(request, "home.html", context)

from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, CartItem


@csrf_exempt
def add_to_cart_api(request, product_id):

    if request.method == "POST":

        try:

            product = Product.objects.get(id=product_id)

            CartItem.objects.create(
                product=product,
                quantity=1
            )

            return JsonResponse({"success": True})

        except Exception as e:

            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False})


def extract_price(text):

    text = text.lower()

    # 2 million
    million_match = re.search(r'(\d+)\s*(million|mln)', text)
    if million_match:
        return int(million_match.group(1)) * 1000000

    # 2000000
    number_match = re.search(r'\d{5,}', text)
    if number_match:
        return int(number_match.group())

    return None
from django.shortcuts import render
from .models import Restaurant


def restaurant_list(request):

    restaurants = Restaurant.objects.all()

    context = {
        "restaurants": restaurants
    }

    return render(request, "eda/restaurants.html", context)

def restaurant_detail(request, pk):

    restaurant = get_object_or_404(Restaurant, id=pk)

    foods = Food.objects.filter(restaurant=restaurant)

    context = {
        "restaurant": restaurant,
        "foods": foods
    }

    return render(request, "eda/restaurant_detail.html", context)


def create_food_order(request, food_id):

    food = Food.objects.get(id=food_id)

    order = FoodOrder.objects.create(
        restaurant=food.restaurant,
        customer_name="Test User",
        customer_phone="998901234567",
        latitude=41.3111,
        longitude=69.2797
    )

    FoodOrderItem.objects.create(
        order=order,
        food=food,
        quantity=1
    )

    return redirect("/eda/restaurants/")

def courier_orders(request):
    orders = FoodOrder.objects.filter(status="new")

    context = {
        "orders": orders
    }

    return render(request, "eda/courier_orders.html", context)
def accept_order(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id)

    order.status = "accepted"
    order.save()

    return redirect("/eda/courier/orders/")
def courier_order_detail(request, order_id):

    order = FoodOrder.objects.get(id=order_id)

    context = {
        "order": order
    }

    return render(request, "eda/courier_order_detail.html", context)


def b2b_sales_dashboard(request):

    today = timezone.now().date()

    b2c_today_sales = (
        OrderItem.objects.filter(
            product__seller=request.user,
            order__status="paid",
            order__created_at__date=today
        ).aggregate(total=Sum("price"))
    )

    daily_sales = (
        OrderItem.objects.filter(
            product__seller=request.user,
            order__status="paid"
        )
        .annotate(day=TruncDate("order__created_at"))
        .values("day")
        .annotate(total=Sum("price"))
        .order_by("-day")[:7]
    )

    top_products = (
        OrderItem.objects.filter(
            product__seller=request.user,
            order__status="paid"
        )
        .values("product__name")
        .annotate(total_sold=Count("id"))
        .order_by("-total_sold")[:5]
    )

    context = {
        "b2c_today_sales": b2c_today_sales["total"] or 0,
        "daily_sales": daily_sales,
        "top_products": top_products,
    }

    return render(request, "b2b/b2b_dashboard.html", context)
@login_required
def confirm_payment(request):

    order_id = request.session.get("payment_order_id")

    if not order_id:
        return redirect("home")

    order = Order.objects.get(id=order_id)

    items = OrderItem.objects.filter(order=order)

    for item in items:

        product = item.product
        product.stock -= item.quantity
        product.save()

    order.status = "paid"
    order.save()

    CartItem.objects.filter(user=request.user).delete()

    return redirect("order_success")
@login_required
def payment_page(request):

    order_id = request.session.get("payment_order_id")

    if not order_id:
        return redirect("home")

    order = Order.objects.get(id=order_id)

    return render(
        request,
        "payment.html",
        {
            "order": order
        }
    )
def send_payment_code(request):

    if request.method == "POST":

        data = json.loads(request.body)

        phone = data.get("phone")

        if not phone:
            return JsonResponse({"success": False, "error": "Telefon kiritilmadi"})

        code = str(random.randint(100000, 999999))

        PaymentOTP.objects.create(
            user=request.user,
            phone=phone,
            code=code
        )

        print("SMS CODE:", code)

        return JsonResponse({"success": True})
@login_required
def verify_payment(request):

    code = request.POST.get("code")

    otp = PaymentOTP.objects.filter(
        user=request.user,
        code=code
    ).last()

    if not otp:
        return redirect("payment_page")

    order_id = request.session.get("payment_order_id")

    if not order_id:
        return redirect("home")

    order = Order.objects.get(id=order_id)

    items = OrderItem.objects.filter(order=order)

    for item in items:

        product = item.product
        product.stock -= item.quantity
        product.save()

    order.status = "paid"
    order.save()

    CartItem.objects.filter(user=request.user).delete()

    # sessionni tozalaymiz
    del request.session["payment_order_id"]

    return redirect("order_success")
@login_required
def buy_now(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    # agar cartda shu product bo'lsa quantity oshiramiz
    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        item.quantity += 1
        item.save()

    return redirect("checkout")


foods = Food.objects.all()[:10]