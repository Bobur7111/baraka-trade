from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import re
import numpy as np
device = "cuda" if torch.cuda.is_available() else "cpu"

# Global model va processor (faqat bir marta yuklanadi)
_model = None
_processor = None


def get_model_and_processor():
    global _model, _processor

    if _model is None or _processor is None:
        print("CLIP model yuklanmoqda...")  # birinchi marta yuklanganda ko'rinadi
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    return _model, _processor


def get_image_vector(image: Image.Image) -> np.ndarray:
    """Rasmni CLIP orqali vectorga aylantiradi"""
    model, processor = get_model_and_processor()

    # Rasmni RGB formatiga o'tkazamiz
    if image.mode != "RGB":
        image = image.convert("RGB")

    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        image_features = model.get_image_features(**inputs)

    # Vectorni numpy ga aylantirib qaytaramiz
    vector = image_features[0].cpu().numpy()
    return vector


def parse_voice_command(text: str) -> dict:
    """Ovozli buyruqdan filterlarni aniqlaydi (to'liqroq versiya)"""
    if not text:
        return {}

    text = text.lower().strip()
    filters = {}

    # ==================== Kategoriyalar ====================
    category_map = {
        "telefon": "Mobile Telefonlar",
        "phone": "Mobile Telefonlar",
        "soat": "Soatlar",
        "watch": "Soatlar",
        "ko'zoynak": "Ko'zoynaklar",
        "kozoynak": "Ko'zoynaklar",
        "glasses": "Ko'zoynaklar",
        "achki": "Ko'zoynaklar",
        "naushnik": "Naushnik va aerpotslar",
        "airpods": "Naushnik va aerpotslar",
        "kalonka": "Kalonkar",
        "speaker": "Kalonkar",
        "aksessuar": "Aksessuarlar",
        "accessory": "Aksessuarlar",
    }

    for keyword, category in category_map.items():
        if keyword in text:
            filters["category"] = category
            break  # birinchi topilgan kategoriyani oladi

    # ==================== Narx filterlari ====================
    # million/mln
    price_million = re.search(r'(\d+)\s*(million|mln|mlrd|milliard)', text)
    if price_million:
        value = int(price_million.group(1))
        unit = price_million.group(2)
        if unit in ['mlrd', 'milliard']:
            filters["price__lt"] = value * 1_000_000_000
        else:
            filters["price__lt"] = value * 1_000_000

    # so'm
    price_som = re.search(r'(\d+)\s*(som|so\'m|sum)', text)
    if price_som:
        filters["price__lt"] = int(price_som.group(1))

    # RAM
    ram_match = re.search(r'(\d+)\s*gb', text)
    if ram_match:
        filters["ram"] = int(ram_match.group(1))

    # Arzon so'zi (agar narx hali belgilanmagan bo'lsa)
    if "arzon" in text and "price__lt" not in filters:
        filters["price__lt"] = 2_000_000

    return filters


# Qo'shimcha: oddiyroq versiya (agar kerak bo'lsa)
def smart_parse(text: str) -> dict:
    """Oddiyroq va tezroq parse funksiyasi"""
    if not text:
        return {}

    text = text.lower().strip()
    filters = {}

    # Kategoriya
    if "telefon" in text or "phone" in text:
        filters["category"] = "Mobile Telefonlar"
    elif "soat" in text or "watch" in text:
        filters["category"] = "Soatlar"
    elif "ko'zoynak" in text or "kozoynak" in text or "achki" in text or "glasses" in text:
        filters["category"] = "Ko'zoynaklar"
    elif "naushnik" in text or "airpods" in text:
        filters["category"] = "Naushnik va aerpotslar"
    elif "kalonka" in text or "speaker" in text:
        filters["category"] = "Kalonkar"
    elif "aksessuar" in text or "accessory" in text:
        filters["category"] = "Aksessuarlar"

    # Narx (million)
    price_match = re.search(r'(\d+)\s*(million|mln)', text)
    if price_match:
        filters["price__lt"] = int(price_match.group(1)) * 1_000_000

    # Arzon
    if "arzon" in text and "price__lt" not in filters:
        filters["price__lt"] = 2_000_000

    return filters