from .models import CartItem
from .translations import TRANSLATIONS
from .models import Notification


def global_context(request):

    # cart
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
    else:
        cart = request.session.get('cart', {})
        cart_count = sum(cart.values())

    # language
    lang = request.GET.get("lang")
    if lang in ["uz", "en", "ru"]:
        request.session["lang"] = lang

    current_lang = request.session.get("lang", "uz")

    t = TRANSLATIONS.get(current_lang, TRANSLATIONS["uz"])

    return {
        "cart_item_count": cart_count,
        "current_lang": current_lang,
        "t": t,
        "year": 2026
    }


def notifications_count(request):

    if request.user.is_authenticated:

        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return {"notifications_count": count}

    return {"notifications_count": 0}