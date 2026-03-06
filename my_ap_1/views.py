import os
import pickle
import torch
from PIL import Image
from huggingface_hub import User
from django.contrib.auth.models import User
from .models import WarehouseLog, Notification
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from .models import Product, Category, CartItem, AdminProfile
from django.db.models import Sum
from .models import Order
import openai
from transformers import CLIPProcessor, CLIPModel
from dotenv import load_dotenv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum

load_dotenv("myy.env")
openai.api_key = os.getenv("OPENAI_API_KEY")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

with open("product_vectors.pkl", "rb") as f:
    product_vectors = pickle.load(f)


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


def search_ai(request):
    result = []

    if request.method == "POST" and request.FILES.get("image"):
        try:
            image = Image.open(request.FILES["image"]).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(device)

            with torch.no_grad():
                query_vector = model.get_image_features(**inputs)
                query_vector = query_vector / query_vector.norm()
                query_vector = query_vector.cpu().numpy()

            sims = [(fn, (query_vector @ vec.T).item())
                    for fn, vec in product_vectors.items()]
            sims.sort(key=lambda x: x[1], reverse=True)
            result = sims[:6]

        except Exception as e:
            print("AI search error:", e)

    return render(request, "search_ai.html", {
        "result": result,
        "cart_item_count": get_cart_count(request)
    })


# =========================
# 💬 CHATBOT
# =========================
def chat_with_ai(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        user_input = data.get("user_input", "")

        if not user_input:
            return JsonResponse({"answer": "Savol bo‘sh!"})

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_input}],
            temperature=0.7
        )

        return JsonResponse({
            "answer": response.choices[0].message["content"]
        })

    return render(request, "chatbot.html", {
        "cart_item_count": get_cart_count(request)
    })



from .models import (
    Product,
    CartItem,
    B2BRequest,
    RestockRequest,
    Order,
    SupplyRequest,
    Delivery
)


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

        sales = Order.objects.filter(
            retailer=user,
            product=product,
            created_at__date__gte=last_week
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
        Order.objects.filter(
            retailer=request.user,
            created_at__date__gte=last_week
        )
        .values("product__name_uz")
        .annotate(total=Sum("quantity"))
        .order_by("-total")[:5]
    )

    # kam qolgan mahsulotlar
    low_stock_products = Product.objects.filter(stock__lt=10).order_by("stock")[:5]

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
top_products = (
    Order.objects
    .values("product__name_uz")
    .annotate(total_sold=Sum("quantity"))
    .order_by("-total_sold")[:10]
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


    # 🔥 TOP SELLING PRODUCTS
    top_products = (
        Order.objects
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

from django.contrib.auth.decorators import login_required
from django.db import transaction

@login_required
def checkout(request):

    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items:
        return redirect("cart_view")

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    order = Order.objects.create(
        retailer=request.user,   # ❗ customer emas
        total_price=total
    )

    for item in cart_items:

        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

        # stock kamayadi
        item.product.stock -= item.quantity
        item.product.save()

    cart_items.delete()

    return redirect("order_success")
def order_success(request):
    return render(request, "order_success.html")