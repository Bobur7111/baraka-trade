from django.urls import path
from . import views

urlpatterns = [

    # =========================
    # HOME & PRODUCTS
    # =========================
    path('', views.home_view, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),


    # =========================
    # CART
    # =========================
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('delete-from-cart/<int:product_id>/', views.delete_from_cart, name='delete_from_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),


    # =========================
    # OTHER PAGES
    # =========================
    path('about/', views.about_view, name='about'),


    # =========================
    # AI FEATURES
    # =========================
    path('search-ai/', views.search_ai, name='search_ai'),
    path('chatbot/', views.chat_with_ai, name='chatbot'),


    # =========================
    # B2B DASHBOARD
    # =========================
    path('b2b/dashboard/', views.b2b_dashboard, name='b2b_dashboard'),

    path(
        'b2b/create/<int:product_id>/',
        views.create_b2b_request,
        name='create_b2b'
    ),

    path(
        'b2b/request/<int:product_id>/',
        views.create_supply_request,
        name='create_supply_request'
    ),


    # =========================
    # DISTRIBUTOR PANEL
    # =========================
    path(
        'b2b/distributor/',
        views.distributor_dashboard,
        name='distributor_dashboard'
    ),

    path(
        'b2b/approve/<int:request_id>/',
        views.approve_request,
        name='approve_request'
    ),
    path(
    "b2b/orders/",
    views.b2b_orders,
    name="b2b_orders"
    ),
   path(
    "b2b/low-stock/",
    views.low_stock,
    name="low_stock"
    ),
   path(
    "b2b/statistics/",
    views.sales_analytics,
    name="sales_analytics"
    ),
   path("b2b/warehouse/", views.warehouse_dashboard, name="warehouse_dashboard"),
   path("b2b/stock-in/<int:product_id>/", views.stock_in, name="stock_in"),
   path("b2b/stock-out/<int:product_id>/", views.stock_out, name="stock_out"),
   path(
    "b2b/ai-assistant/",
    views.ai_assistant,
    name="ai_assistant"
    ),
   path(
    "notifications/",
    views.notifications,
    name="notifications"
    ),
   path(
    "checkout/",
    views.checkout,
    name="checkout"
    ),

   path(
    "order-success/",
    views.order_success,
    name="order_success"
    ),
]