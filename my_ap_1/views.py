import json
import random
import re
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.core.signing import Signer, BadSignature
from .models import TelegramProfile
import torch
from django.contrib import messages
from PIL import Image
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from transformers import CLIPModel, CLIPProcessor

from .models import (
    AdminProfile,
    B2BRequest,
    CartItem,
    Category,
    Delivery,
    DistributorSupplier,
    Food,
    FoodCart,
    FoodCartItem,
    FoodOrder,
    FoodOrderItem,
    FoodPayment,
    Notification,
    Order,
    OrderItem,
    PaymentOTP,
    Product,
    ProductVoice,
    Restaurant,
    SupplierOrder,
    SupplierProduct,
    SupplyRequest,
    WarehouseLog,
)
from .utils import parse_voice_command


# =========================================================
# AI SEARCH CONFIG
# =========================================================
IMAGE_FOLDER = "media/products"

device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

CATEGORIES = {
    "Ko'zoynaklar": ["glasses", "sunglasses", "eyeglasses"],
    "Mobile Telefonlar": ["smartphone", "mobile phone", "iphone"],
    "Soatlar": ["watch", "clock"],
    "Naushnik va aerpotslar": ["earbuds", "airpods", "headphones"],
    "Kalonkalar": ["speaker", "bluetooth speaker"],
}


# =========================================================
# HELPERS
# =========================================================
def detect_category(image):
    texts = []
    mapping = []

    for cat, words in CATEGORIES.items():
        for word in words:
            texts.append(f"a photo of {word}")
            mapping.append(cat)

    inputs = processor(
        text=texts,
        images=image,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    probs = outputs.logits_per_image.softmax(dim=1)
    best = probs.argmax().item()
    return mapping[best]


def extract_price(text):
    text = text.lower()

    million_match = re.search(r"(\d+)\s*(million|mln)", text)
    if million_match:
        return int(million_match.group(1)) * 1_000_000

    number_match = re.search(r"\d{5,}", text)
    if number_match:
        return int(number_match.group())

    return None


def get_cart_count(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).count()

    cart = request.session.get("cart", {})
    return sum(cart.values())


def get_cart_items_and_total(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user).select_related("product")
        cart_items = [
            {
                "product": item.product,
                "quantity": item.quantity,
                "item_total": item.total_price(),
            }
            for item in items
        ]
        total_price = sum(item["item_total"] for item in cart_items)
        return cart_items, total_price

    cart = request.session.get("cart", {})
    cart_items = []
    total_price = 0

    for pid, qty in cart.items():
        try:
            product = Product.objects.get(id=pid)
            item_total = product.price * qty
            total_price += item_total
            cart_items.append(
                {
                    "product": product,
                    "quantity": qty,
                    "item_total": item_total,
                }
            )
        except Product.DoesNotExist:
            continue

    return cart_items, total_price


def calculate_restock_predictions(user):
    predictions = []

    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    products = Product.objects.all()

    for product in products:
        sales = OrderItem.objects.filter(
            order__retailer=user,
            product=product,
            order__created_at__date__gte=last_week,
        )

        total_sold = sales.aggregate(total=Sum("quantity"))["total"] or 0
        daily_avg = total_sold / 7 if total_sold else 0

        if daily_avg > 0:
            days_left = product.stock / daily_avg if daily_avg else 0
            if days_left < 5:
                recommended = int(daily_avg * 14)
                predictions.append(
                    {
                        "product": product,
                        "daily_avg": round(daily_avg, 2),
                        "days_left": round(days_left, 1),
                        "recommended": recommended,
                    }
                )

    return predictions


def _ensure_food_cart(user):
    cart, _ = FoodCart.objects.get_or_create(user=user)
    return cart


# =========================================================
# LANDING / PUBLIC PAGES
# =========================================================
def landing(request):
    return render(request, "landing.html")


def home_view(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)

        if profile and profile.role:
            role = profile.role.lower()

            if role == "supplier":
                return redirect("supplier_dashboard")

            if role == "distributor":
                return redirect("distributor_dashboard")

    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category")

    products = Product.objects.all().select_related("category", "seller")

    if query:
        products = products.filter(
            Q(name_uz__icontains=query)
            | Q(name_en__icontains=query)
            | Q(name_ru__icontains=query)
            | Q(description_uz__icontains=query)
            | Q(description_en__icontains=query)
            | Q(description_ru__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.all()
    admin_info = AdminProfile.objects.first()

    return render(
        request,
        "home.html",
        {
            "products": products,
            "categories": categories,
            "admin_info": admin_info,
            "cart_item_count": get_cart_count(request),
            "query": query,
            "selected_category_id": category_id,
        },
    )
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    categories = Category.objects.all()

    return render(
        request,
        "home.html",
        {
            "products": products,
            "categories": categories,
            "selected_category": category,
            "selected_category_id": category.id,
            "cart_item_count": get_cart_count(request),
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(
        request,
        "product_detail.html",
        {
            "product": product,
            "cart_item_count": get_cart_count(request),
        },
    )


def about_view(request):
    admin_info = AdminProfile.objects.first()
    return render(
        request,
        "about.html",
        {
            "admin_info": admin_info,
            "cart_item_count": get_cart_count(request),
        },
    )


# =========================================================
# AI / CHAT / VOICE
# =========================================================
def search_ai(request):
    result = []
    detected_category = None

    if request.method == "POST":
        image_file = request.FILES.get("image")
        if image_file:
            image = Image.open(image_file).convert("RGB")
            detected_category = detect_category(image)
            result = Product.objects.filter(category__name_uz__icontains=detected_category)

    return render(
        request,
        "search_ai.html",
        {
            "result": result,
            "detected_category": detected_category,
        },
    )


def chatbot(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "").lower()
        price = extract_price(message)

        if "telefon" in message:
            products = Product.objects.filter(category__name_uz__icontains="telefon")

            if price:
                filtered = products.filter(price__lte=price)
                if not filtered.exists():
                    cheapest = products.order_by("price").first()
                    if cheapest:
                        return JsonResponse(
                            {
                                "type": "text",
                                "reply": f"Kechirasiz, {price} UZS dan arzon telefon yo‘q. Eng arzoni {cheapest.price} UZS.",
                            }
                        )
                    return JsonResponse({"type": "text", "reply": "Telefon topilmadi."})
                products = filtered

            products = products.order_by("price")[:5]
            result = []

            for product in products:
                image_url = product.image.url if product.image else ""
                result.append(
                    {
                        "id": product.id,
                        "name": str(product),
                        "price": product.price,
                        "image": image_url,
                    }
                )

            return JsonResponse({"type": "products", "products": result})

        return JsonResponse(
            {
                "type": "text",
                "reply": "Qanday mahsulot kerak? Masalan: telefon, soat yoki naushnik.",
            }
        )

    return render(request, "chatbot.html")


def voice_search(request):
    body = json.loads(request.body)
    text = body.get("text")
    filters = parse_voice_command(text)
    products = ProductVoice.objects.filter(**filters)[:10]

    data = []
    for product in products:
        data.append(
            {
                "name": product.name,
                "price": product.price,
                "ram": product.ram,
            }
        )

    return JsonResponse({"products": data})


def voice_page(request):
    return render(request, "voice_search.html")


# =========================================================
# B2C CART
# =========================================================
def cart_view(request):
    cart_items, total_price = get_cart_items_and_total(request)
    return render(
        request,
        "cart.html",
        {
            "cart_items": cart_items,
            "total_price": total_price,
            "cart_item_count": get_cart_count(request),
        },
    )


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        item, created = CartItem.objects.get_or_create(user=request.user, product=product)
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
        item = CartItem.objects.filter(user=request.user, product_id=product_id).first()
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
        CartItem.objects.filter(user=request.user, product_id=product_id).delete()
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
            item = CartItem.objects.filter(user=request.user, product_id=product_id).first()
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


def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not request.user.is_authenticated:
        return redirect(f"/login/?next=/buy-now/{product_id}/")

    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += 1
        item.save()

    return redirect("checkout")


# =========================================================
# B2C CHECKOUT / PAYMENT
# =========================================================
@login_required(login_url="/login/")
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    if not cart_items.exists():
        return redirect("cart_view")

    with transaction.atomic():
        previous_order_id = request.session.get("payment_order_id")
        if previous_order_id:
            Order.objects.filter(
                id=previous_order_id,
                retailer=request.user,
                status="pending",
            ).delete()

        total = 0
        order_items_payload = []

        for item in cart_items:
            if item.quantity > item.product.stock:
                return redirect("cart_view")
            item_total = item.product.price * item.quantity
            total += item_total
            order_items_payload.append(item)

        order = Order.objects.create(
            retailer=request.user,
            total_price=total,
            order_type="b2c",
            status="pending",
        )

        for item in order_items_payload:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )

        request.session["payment_order_id"] = order.id
        request.session.modified = True

    return redirect("payment_page")


def order_success(request):
    return render(request, "order_success.html")


@login_required
def payment_page(request):
    order_id = request.session.get("payment_order_id")
    if not order_id:
        return redirect("home")

    order = get_object_or_404(Order, id=order_id, retailer=request.user)
    return render(request, "payment.html", {"order": order})


@login_required
@require_POST
def send_payment_code(request):
    data = json.loads(request.body)
    phone = data.get("phone")

    if not phone:
        return JsonResponse({"success": False, "error": "Telefon raqami kiritilmadi"})

    code = str(random.randint(100000, 999999))
    PaymentOTP.objects.create(user=request.user, phone=phone, code=code)

    print("🔥 OTP:", code)
    return JsonResponse({"success": True, "code": code})


@login_required
def verify_payment(request):
    code = request.POST.get("code")

    otp = PaymentOTP.objects.filter(user=request.user, code=code).last()
    if not otp:
        return redirect("payment_page")

    order_id = request.session.get("payment_order_id")
    if not order_id:
        return redirect("home")

    order = get_object_or_404(Order, id=order_id, retailer=request.user)

    if order.status == "paid":
        return redirect("order_success")

    items = OrderItem.objects.filter(order=order).select_related("product")

    with transaction.atomic():
        for item in items:
            product = item.product
            if product.stock < item.quantity:
                return redirect("cart_view")

        for item in items:
            product = item.product
            product.stock -= item.quantity
            product.save(update_fields=["stock"])

        order.status = "paid"
        order.save(update_fields=["status"])

        CartItem.objects.filter(user=request.user).delete()
        request.session.pop("payment_order_id", None)

    return redirect("order_success")


# =========================================================
# B2C DASHBOARD
# =========================================================
@login_required
def b2c_dashboard(request):
    if not request.user.is_superuser:
        return redirect("hr_dashboard")

    today = timezone.now().date()

    order_items = OrderItem.objects.filter(
        order__order_type="b2c",
        order__status="paid",
        order__created_at__date=today,
    )

    today_sales = order_items.aggregate(total=Sum(F("price") * F("quantity")))["total"] or 0
    today_orders_count = order_items.values("order").distinct().count()

    top_products = (
        OrderItem.objects.filter(order__status="paid")
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    low_stock_products = Product.objects.filter(stock__lte=7)

    return render(
        request,
        "b2c/dashboard.html",
        {
            "today_sales": today_sales,
            "today_orders_count": today_orders_count,
            "top_products": top_products,
            "low_stock_products": low_stock_products,
        },
    )


# =========================================================
# B2B
# =========================================================
def b2b_entry(request):
    if not request.user.is_authenticated:
        return redirect("login")

    profile = getattr(request.user, "profile", None)

    if not profile or not profile.role:
        return redirect("home")

    role = profile.role.lower()

    if role == "retailer":
        return redirect("b2b_dashboard")

    if role == "distributor":
        return redirect("distributor_dashboard")

    if role == "supplier":
        return redirect("supplier_dashboard")

    return redirect("home")
@login_required
def create_b2b_request(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    B2BRequest.objects.create(retailer=request.user, product=product, quantity=50)
    return redirect("b2b_dashboard")


@login_required
def create_supply_request(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    SupplyRequest.objects.create(retailer=request.user, product=product, quantity=10)

    distributors = User.objects.filter(profile__role="distributor")
    for distributor in distributors:
        Notification.objects.create(
            user=distributor,
            message=f"New supply request for {product.name_uz}",
        )

    return redirect("b2b_dashboard")


@login_required
def distributor_dashboard(request):
    if request.user.profile.role != "distributor":
        return redirect("home")

    requests = SupplyRequest.objects.filter(
        product__seller=request.user
    ).order_by("-id")
    suppliers = DistributorSupplier.objects.filter(distributor=request.user)

    return render(
        request,
        "b2b/distributor_dashboard.html",
        {
            "requests": requests,
            "suppliers": suppliers,
        },
    )


@login_required
def b2b_orders(request):
    orders = B2BRequest.objects.filter(retailer=request.user).order_by("-created_at")
    return render(request, "b2b/orders.html", {"orders": orders})


@login_required
def approve_request(request, request_id):
    if request.user.profile.role != "distributor":
        return redirect("home")

    supply_request = get_object_or_404(SupplyRequest, id=request_id)
    supply_request.status = "sent"
    supply_request.save(update_fields=["status"])

    Delivery.objects.create(request=supply_request, status="active")
    return redirect("distributor_dashboard")


@login_required
def b2b_dashboard(request):
    b2b_orders_qs = Order.objects.filter(
        retailer=request.user,
        order_type="b2b",
        status="paid",
    )

    total_sales = b2b_orders_qs.aggregate(total=Sum("total_price"))["total"] or 0

    low_stock_products = Product.objects.filter(
        seller=request.user,
        stock__lte=7
    )
    low_stock_count = low_stock_products.count()

    requests_count = SupplyRequest.objects.filter(retailer=request.user).count()
    active_deliveries = Delivery.objects.filter(
        request__retailer=request.user,
        status="active",
    ).count()

    top_products = (
        OrderItem.objects.filter(order__retailer=request.user, order__status="paid")
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    return render(
        request,
        "b2b/b2b_dashboard.html",
        {
            "total_sales": total_sales,
            "low_stock_products": low_stock_products,
            "low_stock_count": low_stock_count,
            "requests_count": requests_count,
            "active_deliveries": active_deliveries,
            "top_products": top_products,
        },
    )


@login_required
def sales_analytics(request):
    today = timezone.now().date()
    sales_labels = []
    sales_data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = (
            Order.objects.filter(retailer=request.user, created_at__date=day)
            .aggregate(total=Sum("total_price"))["total"]
            or 0
        )
        sales_labels.append(day.strftime("%a"))
        sales_data.append(float(total))

    top_products = (
        OrderItem.objects.filter(order__retailer=request.user)
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    return render(
        request,
        "b2b/statistics.html",
        {
            "sales_labels": sales_labels,
            "sales_data": sales_data,
            "top_products": top_products,
        },
    )


@login_required
def stock_in(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))

    if quantity <= 0:
        return redirect("warehouse_dashboard")

    product.stock += quantity
    product.save(update_fields=["stock"])

    WarehouseLog.objects.create(
        product=product,
        quantity=quantity,
        action="in",
        note="Manual stock update",
    )
    return redirect("warehouse_dashboard")


@login_required
def stock_out(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))

    if quantity <= 0 or quantity > product.stock:
        return redirect("warehouse_dashboard")

    product.stock -= quantity
    product.save(update_fields=["stock"])

    WarehouseLog.objects.create(
        product=product,
        quantity=quantity,
        action="out",
        note="Stock reduced",
    )
    return redirect("warehouse_dashboard")


@login_required
def warehouse_dashboard(request):
    products = Product.objects.filter(seller=request.user).order_by("stock")

    logs = WarehouseLog.objects.filter(
        product__seller=request.user
    ).order_by("-created_at")[:10]
    return render(request, "b2b/warehouse.html", {"products": products, "logs": logs})


@login_required
def ai_assistant(request):
    top_products = (
        OrderItem.objects.filter(order__retailer=request.user)
        .values("product__name_uz")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    low_stock_products = Product.objects.filter(
        seller=request.user,
        stock__lt=10
    )
    predictions = calculate_restock_predictions(request.user)

    return render(
        request,
        "b2b/ai_assistant.html",
        {
            "top_products": top_products,
            "low_stock_products": low_stock_products,
            "predictions": predictions,
        },
    )


@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    user_notifications.filter(is_read=False).update(is_read=True)

    return render(
        request,
        "b2b/notifications.html",
        {
            "notifications": user_notifications
        }
    )

# =========================================================
# RESTAURANTS / EDA
# =========================================================
def restaurant_list(request):
    restaurants = Restaurant.objects.all()
    cart_count = 0

    if request.user.is_authenticated:
        cart_count = FoodCartItem.objects.filter(cart__user=request.user).count()

    return render(
        request,
        "eda/restaurants.html",
        {
            "restaurants": restaurants,
            "cart_count": cart_count,
        },
    )


def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, id=pk)
    foods = Food.objects.filter(restaurant=restaurant)
    return render(
        request,
        "eda/restaurant_detail.html",
        {
            "restaurant": restaurant,
            "foods": foods,
        },
    )


@login_required
def add_food_to_cart(request, food_id):
    food = get_object_or_404(Food, id=food_id)
    cart = _ensure_food_cart(request.user)

    item, created = FoodCartItem.objects.get_or_create(cart=cart, food=food)
    if not created:
        item.quantity += 1
        item.save(update_fields=["quantity"])

    return redirect(request.META.get("HTTP_REFERER", "/eda/restaurants/"))


@login_required
def cart_view_2(request):
    cart = _ensure_food_cart(request.user)
    items = FoodCartItem.objects.filter(cart=cart).select_related("food")
    total = sum(item.food.price * item.quantity for item in items)

    return render(
        request,
        "eda/cart.html",
        {
            "items": items,
            "total": total,
        },
    )


@login_required
@require_POST
def update_food_cart(request):
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")

    item = get_object_or_404(FoodCartItem, id=item_id, cart__user=request.user)

    if action in ["plus", "inc"]:
        item.quantity += 1
        item.save(update_fields=["quantity"])
    elif action in ["minus", "dec"]:
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
            cart_total = sum(
                i.food.price * i.quantity
                for i in FoodCartItem.objects.filter(cart__user=request.user).select_related("food")
            )
            return JsonResponse({"deleted": True, "cart_total": int(cart_total)})
        item.save(update_fields=["quantity"])
    elif action == "remove":
        item.delete()
        cart_total = sum(
            i.food.price * i.quantity
            for i in FoodCartItem.objects.filter(cart__user=request.user).select_related("food")
        )
        return JsonResponse({"deleted": True, "cart_total": int(cart_total)})

    item_total = item.food.price * item.quantity
    cart_total = sum(
        i.food.price * i.quantity
        for i in FoodCartItem.objects.filter(cart=item.cart).select_related("food")
    )

    return JsonResponse(
        {
            "qty": item.quantity,
            "item_total": int(item_total),
            "total": int(cart_total),
            "cart_total": int(cart_total),
        }
    )


@login_required
def food_checkout(request):
    cart = _ensure_food_cart(request.user)
    items = FoodCartItem.objects.filter(cart=cart).select_related("food", "food__restaurant")

    if not items.exists():
        return redirect("/eda/cart/")

    total = sum(item.food.price * item.quantity for item in items)

    if request.method == "POST":
        customer_phone = request.POST.get("phone", "").strip()
        customer_name = request.POST.get("name", request.user.username).strip() or request.user.username
        address = request.POST.get("address", "Toshkent").strip() or "Toshkent"
        payment_type = request.POST.get("payment_type", "cash")

        if payment_type not in ["cash", "card"]:
            payment_type = "cash"

        with transaction.atomic():
            order = FoodOrder.objects.create(
                restaurant=items.first().food.restaurant,
                customer_name=customer_name,
                customer_phone=customer_phone,
                latitude=41.3,
                longitude=69.2,
                status="new",
                address=address,
            )

            for item in items:
                FoodOrderItem.objects.create(order=order, food=item.food, quantity=item.quantity)

            FoodPayment.objects.create(
                order=order,
                payment_type=payment_type,
                is_paid=(payment_type == "cash"),
            )

            items.delete()

        return redirect(f"/eda/receipt/{order.id}/")

    return render(request, "eda/checkout.html", {"items": items, "total": total})


@login_required
def receipt(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id)
    items = FoodOrderItem.objects.filter(order=order).select_related("food")
    total = sum(item.food.price * item.quantity for item in items)

    return render(
        request,
        "eda/receipt.html",
        {
            "order": order,
            "items": items,
            "total": total,
        },
    )


@login_required
def profile(request):
    orders = FoodOrder.objects.filter(customer_phone__isnull=False).order_by("-created_at")
    return render(request, "eda/profile.html", {"orders": orders})


# =========================================================
# COURIER FLOW
# =========================================================
@login_required
def courier_orders(request):
    orders = FoodOrder.objects.filter(status="new").select_related("restaurant", "courier")
    return render(request, "eda/courier_orders.html", {"orders": orders})


@login_required
def accept_order(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id)
    order.status = "accepted"
    order.save(update_fields=["status"])
    return redirect("/eda/courier/orders/")


@login_required
def courier_order_detail(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id)
    return render(request, "eda/courier_order_detail.html", {"order": order})


# =========================================================
# SUPPLIER / DISTRIBUTOR
# =========================================================
@login_required
def supplier_products(request, supplier_id):
    if request.user.profile.role != "distributor":
        return redirect("home")

    products = SupplierProduct.objects.filter(supplier_id=supplier_id)
    return render(request, "b2b/supplier_products.html", {"products": products})


@login_required
def add_product_to_distributor(request, supplier_product_id):
    if request.user.profile.role != "distributor":
        return redirect("home")

    supplier_product = get_object_or_404(SupplierProduct, id=supplier_product_id)
    DistributorSupplier.objects.get_or_create(
        distributor=request.user,
        supplier=supplier_product.supplier,
    )
    return redirect("distributor_dashboard")


@login_required
def order_to_supplier(request, supplier_product_id):
    if request.user.profile.role != "distributor":
        return redirect("home")

    supplier_product = get_object_or_404(SupplierProduct, id=supplier_product_id)

    SupplierOrder.objects.create(
        distributor=request.user,
        supplier=supplier_product.supplier,
        product=supplier_product.product,
        quantity=10,
    )

    return redirect("distributor_dashboard")


@login_required
def supplier_dashboard(request):
    if request.user.profile.role != "supplier":
        return redirect("home")

    products = SupplierProduct.objects.filter(supplier=request.user)
    orders = SupplierOrder.objects.filter(supplier=request.user)

    return render(
        request,
        "b2b/supplier_dashboard.html",
        {
            "products": products,
            "orders": orders,
        },
    )


# =========================================================
# AUTH
# =========================================================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get("next")
            return redirect(next_url or "home")

    return render(request, "auth/login_register.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        role = request.POST.get("role", "customer").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Username va parol kiritilishi shart.")
            return redirect("login")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Bu username oldin ro‘yxatdan o‘tgan.")
            return redirect("login")

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        profile = user.profile
        profile.phone = phone
        profile.address = address
        profile.role = role if role in ["customer", "retailer", "distributor", "supplier"] else "customer"
        profile.save()

        login(request, user)
        return redirect("home")

    return redirect("login")
@login_required
def low_stock(request):
    products = Product.objects.filter(stock__lt=10).order_by("stock")

    return render(
        request,
        "b2b/low_stock.html",
        {"products": products}
    )
signer = Signer()

def telegram_auto_login(request, token):
    try:
        telegram_id = signer.unsign(token)
    except BadSignature:
        return redirect("login")

    profile = TelegramProfile.objects.filter(telegram_id=telegram_id).first()

    if not profile:
        return redirect("login")

    login(request, profile.user)
    return redirect("home")
@login_required
def profile_view(request):
    profile = request.user.profile

    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        request.user.save()

        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()

        if request.FILES.get("image"):
            profile.image = request.FILES.get("image")

        profile.save()
        return redirect("profile_view")

    return render(request, "profile.html", {"profile": profile})
@login_required
def my_products(request):
    products = Product.objects.filter(seller=request.user)

    return render(request, 'my_products.html', {
        'products': products
    })
@login_required
def add_product(request):
    categories = Category.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        category_id = request.POST.get("category")

        image = request.FILES.get("image")

        Product.objects.create(
            seller=request.user,
            name_uz=name,
            price=price,
            stock=stock,
            category_id=category_id,
            image=image
        )

        return redirect("my_products")

    return render(request, "add_product.html", {
        "categories": categories
    })
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    categories = Category.objects.all()

    if request.method == "POST":
        product.name_uz = request.POST.get("name_uz", "").strip()
        product.name_en = request.POST.get("name_en", "").strip()
        product.name_ru = request.POST.get("name_ru", "").strip()

        product.description_uz = request.POST.get("description_uz", "").strip()
        product.description_en = request.POST.get("description_en", "").strip()
        product.description_ru = request.POST.get("description_ru", "").strip()

        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        product.category_id = request.POST.get("category")

        if request.FILES.get("image"):
            product.image = request.FILES.get("image")

        product.save()
        return redirect("my_products")

    return render(request, "edit_product.html", {
        "product": product,
        "categories": categories
    })


@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)

    if request.method == "POST":
        product.delete()
        return redirect("my_products")

    return render(request, "delete_product.html", {
        "product": product
    })
def online_users_count(request):
    limit_time = timezone.now() - timedelta(minutes=5)

    count = User.objects.filter(
        profile__last_seen__gte=limit_time
    ).count()

    return JsonResponse({
        "online_users": count
    })
@login_required
def unread_notifications_count(request):
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "unread_count": count
    })