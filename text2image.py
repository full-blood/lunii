from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os

# Charger les mots
df = pd.read_csv("vocabulaire_anglais_100w_EnFr.csv")

# Créer dossier de sortie
output_dir = "assets"
os.makedirs(output_dir, exist_ok=True)

catNb=0
iteNb=1
prev_Cat = ""

# Définir police (utilise Arial ou une police système)
try:
    font = ImageFont.truetype("arial.ttf", 50)
except:
    font = ImageFont.load_default()

# Générer une image pour chaque mot
for _, row in df.iterrows():
    word_en = row["Word"]
    category = row["Category"].replace(" ", "_")
    category = row["Category"].replace("/", "et")
    img_w = 320
    img_h = 240
    
    if category != prev_Cat :
        catNb=catNb+1
        iteNb=0
        prev_Cat=category
        print(f"cat change {category}/{prev_Cat}")
    iteNb=iteNb+1

    # Créer un sous-dossier par catégorie
    category_dir = os.path.join(output_dir, "")
    os.makedirs(category_dir, exist_ok=True)

    # Créer image blanche
    img = Image.new('RGB', (img_w, img_h), color='black')
    draw = ImageDraw.Draw(img)

    # Centrer les textes
    text = f"{word_en}"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculer les coordonnées centrées
    x = (img_w - text_width) // 2
    y = (img_h - text_height) // 2
    draw.text((x, y), text, fill="white", font=font)

    # Sauvegarder
    img.save(os.path.join(category_dir, f"{catNb:02d}-{iteNb:02d}_{word_en}.png"))

    
    print(f"✅ Image créée pour : {word_en}")

print("\n🖼️ Toutes les images ont été générées.")
