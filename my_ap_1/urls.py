from django.urls import path
from . import views

urlpatterns = [
    # Bosh sahifa va product yo‘llari
    path('', views.home_view, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),

    # Savatcha yo‘llari
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('delete-from-cart/<int:product_id>/', views.delete_from_cart, name='delete_from_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),

    # Boshqa sahifalar
    path('about/', views.about_view, name='about'),

    # AI Image Search
    path('search-ai/', views.search_ai, name='search_ai'),

    # AI Chatbot
    path('chatbot/', views.chat_with_ai, name='chatbot'),  # eski 'views.chatbot' o‘rniga
]
