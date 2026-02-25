import os
import pickle
import torch
from PIL import Image

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse

from .models import Product, Category, CartItem, AdminProfile

import openai
from transformers import CLIPProcessor, CLIPModel
from dotenv import load_dotenv


# =========================
# 🔐 ENV & AI SETUP
# =========================
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


# =========================
# 🖼 AI IMAGE SEARCH
# =========================
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
