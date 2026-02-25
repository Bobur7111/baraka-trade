from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import os
import numpy as np
import pickle

# CLIP modelini yuklash
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Mahsulot rasm katalogi
product_images_dir = "media/products/"

# Mahsulot vectorlarini saqlash
product_vectors = {}
for filename in os.listdir(product_images_dir):
    if filename.lower().endswith((".jpg", ".png", ".webp")):
        path = os.path.join(product_images_dir, filename)
        try:
            image = Image.open(path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(device)
            with torch.no_grad():
                vector = model.get_image_features(**inputs)
                vector = vector / vector.norm()  # normalize
            product_vectors[filename] = vector.cpu().numpy()
        except Exception as e:
            print(f"Error with {filename}: {e}")

# Vectorlarni pickle faylga saqlash
with open("product_vectors.pkl", "wb") as f:
    pickle.dump(product_vectors, f)

print("Mahsulot vectorlari tayyor!")
