from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np
import re


# =========================
# DEVICE
# =========================
device = "cuda" if torch.cuda.is_available() else "cpu"


# =========================
# CLIP MODEL
# =========================
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


# =========================
# IMAGE → VECTOR
# =========================
def get_image_vector(image):

    image = image.convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        features = model.get_image_features(**inputs)

    vector = features[0].cpu().numpy()

    return vector


# =========================
# VOICE COMMAND PARSER
# =========================
def parse_voice_command(text):

    filters = {}

    if not text:
        return filters

    text = text.lower()


    # PRICE (million)
    price_match = re.search(r'(\d+)\s*(million|mln|milliondan)', text)
    if price_match:
        filters["price__lt"] = int(price_match.group(1)) * 1000000


    # PRICE (so'm)
    som_match = re.search(r'(\d+)\s*(som|so\'m|sum)', text)
    if som_match:
        filters["price__lt"] = int(som_match.group(1))


    # RAM
    ram_match = re.search(r'(\d+)\s*gb', text)
    if ram_match:
        filters["ram"] = int(ram_match.group(1))


    # CATEGORY
    if "telefon" in text or "phone" in text:
        filters["category"] = "Mobile Telefonlar"

    elif "soat" in text or "watch" in text:
        filters["category"] = "Soatlar"

    elif "ko'zoynak" in text or "kozoynak" in text or "glasses" in text:
        filters["category"] = "Ko'zoynaklar"

    elif "naushnik" in text or "airpods" in text:
        filters["category"] = "Naushnik va aerpotslar"

    elif "kalonka" in text or "speaker" in text:
        filters["category"] = "Kalonkar"

    elif "aksessuar" in text or "accessory" in text:
        filters["category"] = "Aksessuarlar"


    return filters
def smart_parse(text):
    text = text.lower()
    filters = {}

    # CATEGORY
    if "telefon" in text:
        filters["category"] = "Mobile Telefonlar"

    elif "soat" in text:
        filters["category"] = "Soatlar"

    elif "ko'zoynak" in text or "achki" in text:
        filters["category"] = "Ko'zoynaklar"

    elif "naushnik" in text or "airpods" in text:
        filters["category"] = "Naushnik va aerpotslar"

    # PRICE (million)
    price_match = re.search(r'(\d+)\s*(million|mln)', text)
    if price_match:
        filters["price__lt"] = int(price_match.group(1)) * 1000000

    # ARZON keyword
    if "arzon" in text and "price__lt" not in filters:
        filters["price__lt"] = 2000000

    return filters