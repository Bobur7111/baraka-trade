from django import template

register = template.Library()

@register.filter
def tr(obj, lang):
    """
    Universal translator:
    {{ product|tr:current_lang }}
    {{ category|tr:current_lang }}
    """
    if hasattr(obj, "get_name"):
        return obj.get_name(lang)
    return ""


@register.filter
def tr_desc(obj, lang):
    """
    Product description translator
    """
    if hasattr(obj, "get_description"):
        return obj.get_description(lang)
    return ""
