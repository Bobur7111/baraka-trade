from .models import CartItem
from .translations import TRANSLATIONS

def global_context(request):
    # 🛒 Cart count
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
    else:
        cart = request.session.get('cart', {})
        cart_count = sum(cart.values())

    # 🌐 Language
    lang = request.GET.get("lang")
    if lang in ["uz", "en", "ru"]:
        request.session["lang"] = lang

    current_lang = request.session.get("lang", "uz")

    # 🔤 Translations
    t = TRANSLATIONS.get(current_lang, TRANSLATIONS["uz"])

    return {
        "cart_item_count": cart_count,
        "current_lang": current_lang,
        "t": t,
        "year": 2026
    }
