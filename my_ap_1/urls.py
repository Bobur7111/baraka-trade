from django.urls import path
from . import views

urlpatterns = [
    # =========================
    # PUBLIC / LANDING
    # =========================
    path('', views.landing, name='landing'),
    path('home/', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),

    # =========================
    # AUTH
    # =========================
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),

    # =========================
    # PRODUCTS / B2C
    # =========================
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),

    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('delete-from-cart/<int:product_id>/', views.delete_from_cart, name='delete_from_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),

    path('checkout/', views.checkout, name='checkout'),
    path('payment/', views.payment_page, name='payment_page'),
    path('send-payment-code/', views.send_payment_code, name='send_payment_code'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('order-success/', views.order_success, name='order_success'),

    path('b2c/dashboard/', views.b2c_dashboard, name='b2c_dashboard'),

    # =========================
    # AI / CHAT / VOICE
    # =========================
    path('search-ai/', views.search_ai, name='search_ai'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('voice-search/', views.voice_search, name='voice_search'),
    path('voice/', views.voice_page, name='voice_page'),

    # =========================
    # B2B
    # =========================
    path('b2b/dashboard/', views.b2b_dashboard, name='b2b_dashboard'),
    path('b2b/create/<int:product_id>/', views.create_b2b_request, name='create_b2b'),
    path('b2b/request/<int:product_id>/', views.create_supply_request, name='create_supply_request'),
    path('b2b/distributor/', views.distributor_dashboard, name='distributor_dashboard'),
    path('b2b/approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('b2b/orders/', views.b2b_orders, name='b2b_orders'),
    path('b2b/statistics/', views.sales_analytics, name='sales_analytics'),
    path('b2b/warehouse/', views.warehouse_dashboard, name='warehouse_dashboard'),
    path('b2b/stock-in/<int:product_id>/', views.stock_in, name='stock_in'),
    path('b2b/stock-out/<int:product_id>/', views.stock_out, name='stock_out'),
    path('b2b/ai-assistant/', views.ai_assistant, name='ai_assistant'),

    path('notifications/', views.notifications, name='notifications'),

    # =========================
    # SUPPLIER / DISTRIBUTOR
    # =========================
    path('supplier/dashboard/', views.supplier_dashboard, name='supplier_dashboard'),
    path('supplier/<int:supplier_id>/products/', views.supplier_products, name='supplier_products'),
    path('distributor/add-product/<int:supplier_product_id>/', views.add_product_to_distributor, name='add_product_to_distributor'),
    path('distributor/order-supplier/<int:supplier_product_id>/', views.order_to_supplier, name='order_to_supplier'),

    # =========================
    # EDA / RESTAURANTS
    # =========================
    path('eda/restaurants/', views.restaurant_list, name='restaurant_list'),
    path('eda/restaurant/<int:pk>/', views.restaurant_detail, name='restaurant_detail'),

    path('food/add/<int:food_id>/', views.add_food_to_cart, name='add_food_to_cart'),
    path('eda/cart/', views.cart_view_2, name='food_cart'),
    path('eda/update-cart/', views.update_food_cart, name='update_food_cart'),
    path('eda/checkout/', views.food_checkout, name='food_checkout'),
    path('eda/receipt/<int:order_id>/', views.receipt, name='receipt'),
    path('eda/profile/', views.profile, name='profile'),
    path("b2b/low-stock/", views.low_stock, name="low_stock"),


    path('eda/courier/orders/', views.courier_orders, name='courier_orders'),
    path('eda/courier/accept/<int:order_id>/', views.accept_order, name='accept_order'),
    path('eda/courier/order/<int:order_id>/', views.courier_order_detail, name='courier_order_detail'),
    path("telegram-login/<str:token>/", views.telegram_auto_login, name="telegram_login"),
]