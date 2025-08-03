import os
import json
import uuid
import random
import shutil
import zipfile
import re
from collections import defaultdict

# === CONFIGURATION DE BASE ===
script_dir = os.path.dirname(os.path.abspath(__file__))
script_folder_name = os.path.basename(script_dir)
assets_dir = os.path.join(script_dir, "assets")
build_dir = os.path.join(script_dir, "build")
build_assets = os.path.join(build_dir, "assets")
os.makedirs(build_assets, exist_ok=True)

# Fonctions utilitaires
def generate_random_hex(length):
    """Génère une chaîne hexadécimale aléatoire"""
    return ''.join(random.choices('0123456789abcdef', k=length))

def generate_uuid():
    """Génère un UUID v4"""
    return str(uuid.uuid4())

def format_number_02d(number):
    """Formate un nombre avec 2 chiffres (01, 02, etc.)"""
    return f"{number:02d}"

# === VALIDATION DES FICHIERS COVER & TITLE ===
cover_path = os.path.join(assets_dir, "cover.png")
cover_1_1_path  = os.path.join(assets_dir, "cover_1-1.png")
title_audio_path = os.path.join(assets_dir, "title.mp3")

if not os.path.exists(cover_path):
    raise FileNotFoundError(f"Fichier manquant : {cover_path}")
if not os.path.exists(title_audio_path):
    raise FileNotFoundError(f"Fichier manquant : {title_audio_path}")

# === NOMMAGE ALEATOIRE POUR COVER & AUDIO PRINCIPAL ===
image_cover_name = generate_random_hex(40) + ".png"
audio_title_name = generate_random_hex(40) + ".mp3"
uuid_cover = generate_uuid()

# UUIDs pour les éléments du menu principal
main_menu_question_uuid = "cb10798f-a70b-418b-be94-111111111111"
main_menu_options_uuid = "cb10798f-a70b-418b-be94-333333333333" 
main_menu_question_stage_uuid = "cb10798f-a70b-418b-be94-222222222222"
group_id = "cb10798f-a70b-418b-be94-cf3c33619a7a"

# === COPIES INITIALES ===
thumbnail_path = os.path.join(build_dir, "thumbnail.png")
shutil.copy(cover_1_1_path, thumbnail_path)
shutil.copy(cover_path, os.path.join(build_assets, image_cover_name))
shutil.copy(title_audio_path, os.path.join(build_assets, audio_title_name))

# === MAPPAGE DES FICHIERS VOCABULAIRES ===
media_mapping = {}  # clé logique -> nom de fichier hex
label_mapping = {}  # clé logique -> nom lisible
menu_structure = defaultdict(set)  # Utiliser un set pour éviter les doublons

# Traitement des fichiers avec format NN-NN_label.ext
for filename in os.listdir(assets_dir):
    # Ignorer les fichiers spéciaux (cover, title, sound, etc.)
    if filename in ["cover.png", "title.mp3", "sound.mp3"]:
        continue
        
    match = re.match(r"(\d{2})-(\d{2})_([^\.]+)\.(mp3|png)", filename)
    if match:
        cat_id, word_id, label, ext = match.groups()
        key = f"{cat_id}-{word_id}"
        label_mapping[key] = label.replace("_", " ")
        hex_name = generate_random_hex(40) + f".{ext}"
        media_mapping[f"{key}.{ext}"] = hex_name
        
        # Copie du fichier avec le nouveau nom
        shutil.copy(os.path.join(assets_dir, filename), os.path.join(build_assets, hex_name))
        
        # Si ce n'est pas un fichier de menu (word_id != "00")
        if word_id != "00":
            menu_structure[cat_id].add((word_id, label.replace("_", " ")))

# Traitement des fichiers spéciaux (sound.mp3, etc.)
special_files = ["sound.mp3"]
for special_file in special_files:
    special_path = os.path.join(assets_dir, special_file)
    if os.path.exists(special_path):
        hex_name = generate_random_hex(40) + os.path.splitext(special_file)[1]
        media_mapping[special_file] = hex_name
        shutil.copy(special_path, os.path.join(build_assets, hex_name))
        
# Convertir les sets en listes triées pour le traitement ultérieur
menu_structure = {cat_id: sorted(list(words)) for cat_id, words in menu_structure.items()}

# === CONSTRUCTION DU JSON ===
story_data = {
    "format": "v1",
    "title": "Vocabulaire anglais",
    "version": 1,
    "description": f"Pack de vocabulaire - {len(menu_structure)} catégories",
    "nightModeAvailable": True,
    "stageNodes": [],
    "actionNodes": []
}

# === COVER NODE ===
story_data["stageNodes"].append({
    "uuid": uuid_cover,
    "type": "cover",
    "name": "Vocabulaire",
    "position": {"x": 100, "y": 500},
    "image": image_cover_name,
    "audio": audio_title_name,
    "okTransition": {
        "actionNode": main_menu_question_uuid,
        "optionIndex": 0
    },
    "homeTransition": None,
    "controlSettings": {
        "wheel": True,
        "ok": True,
        "home": False,
        "pause": False,
        "autoplay": True
    },
    "squareOne": True
})

# === MENU QUESTION STAGE ===
story_data["stageNodes"].append({
    "uuid": main_menu_question_stage_uuid,
    "type": "menu.questionstage",
    "groupId": group_id,
    "name": "Menu node",
    "image": None,
    "audio": media_mapping.get("sound.mp3"),  # Audio optionnel pour le menu
    "okTransition": {
        "actionNode": main_menu_options_uuid,
        "optionIndex": 0
    },
    "homeTransition": None,
    "controlSettings": {
        "wheel": False,
        "ok": False,
        "home": False,
        "pause": False,
        "autoplay": True
    }
})

# === GÉNÉRATION DES CATÉGORIES ET MOTS ===
category_option_stages = []

for menu_index, (menu_id, words) in enumerate(sorted(menu_structure.items())):
    # UUID pour l'option stage de cette catégorie
    option_stage_uuid = f"cb10798f-a70b-418b-be94-44444444{format_number_02d(int(menu_id))}"
    category_option_stages.append(option_stage_uuid)
    
    # UUID pour l'action node de cette catégorie
    action_node_uuid = generate_uuid()
    
    # Récupération des médias pour cette catégorie
    menu_key = f"{menu_id}-00"
    menu_image = media_mapping.get(f"{menu_key}.png")
    menu_audio = media_mapping.get(f"{menu_key}.mp3")
    menu_label = label_mapping.get(menu_key, f"Catégorie {menu_id}")
    
    # === OPTION STAGE POUR CETTE CATÉGORIE ===
    story_data["stageNodes"].append({
        "uuid": option_stage_uuid,
        "type": "menu.optionstage", 
        "groupId": group_id,
        "name": menu_label,
        "image": menu_image,
        "audio": menu_audio,
        "okTransition": {
            "actionNode": action_node_uuid,
            "optionIndex": 0
        },
        "homeTransition": None,
        "controlSettings": {
            "wheel": True,
            "ok": True,
            "home": True,
            "pause": False,
            "autoplay": True
        }
    })
    
    # === GÉNÉRATION DES STAGES POUR LES MOTS DE CETTE CATÉGORIE ===
    word_stage_uuids = []
    
    for word_index, (word_id, word_label) in enumerate(sorted(words)):
        word_stage_uuid = generate_uuid()
        word_stage_uuids.append(word_stage_uuid)
        
        # Récupération des médias pour ce mot
        word_key = f"{menu_id}-{word_id}"
        word_image = media_mapping.get(f"{word_key}.png")
        word_audio = media_mapping.get(f"{word_key}.mp3")
        
        # Calcul de la position (disposition en grille par catégorie)
        # Chaque catégorie a sa propre ligne
        base_x = 1576 + (word_index % 5) * 250  # 5 colonnes max
        base_y = 236 + (int(menu_id) - 1) * 300 + (word_index // 5) * 200  # Espacement vertical par catégorie
        
        # Calcul de la transition vers le prochain mot
        next_word_option_index = word_index + 1 if word_index < len(words) - 1 else 0
        
        # === STAGE POUR CE MOT ===
        story_data["stageNodes"].append({
            "uuid": word_stage_uuid,
            "type": "stage",
            "name": word_label,  # Utiliser le label au lieu du numéro
            "position": {"x": base_x, "y": base_y},
            "image": word_image,
            "audio": word_audio,
            "okTransition": {
                "actionNode": action_node_uuid,
                "optionIndex": next_word_option_index
            },
            "homeTransition": {
                "actionNode": main_menu_question_uuid,
                "optionIndex": 0
            },
            "controlSettings": {
                "wheel": True,
                "ok": False,
                "home": True,
                "pause": True,
                "autoplay": True
            }
        })
    
    # === ACTION NODE POUR CETTE CATÉGORIE ===
    action_position_x = 1323 + menu_index * 50
    action_position_y = 255 + menu_index * 300  # Même espacement que les stages
    
    story_data["actionNodes"].append({
        "id": action_node_uuid,
        "name": menu_label,
        "position": {"x": action_position_x, "y": action_position_y},
        "options": word_stage_uuids
    })

# === ACTION NODES POUR LE MENU PRINCIPAL ===
story_data["actionNodes"].extend([
    {
        "id": main_menu_question_uuid,
        "type": "menu.questionaction",
        "groupId": group_id,
        "name": "Menu node.questionaction",
        "position": {"x": 681.59, "y": 1660.68},
        "options": [main_menu_question_stage_uuid]
    },
    {
        "id": main_menu_options_uuid,
        "type": "menu.optionsaction",
        "groupId": group_id,
        "name": "Menu node.optionsaction",
        "position": {"x": 681.59, "y": 1860.68},
        "options": category_option_stages
    }
])

# === ÉCRITURE DU FICHIER JSON ===
story_json_path = os.path.join(build_dir, "story.json")
with open(story_json_path, "w", encoding="utf-8") as f:
    json.dump(story_data, f, indent=2, ensure_ascii=False)

# === CRÉATION DE L'ARCHIVE ZIP ===
zip_filename = os.path.join(script_dir, f"{script_folder_name}_{generate_random_hex(4)}.zip")
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Ajout du story.json
    zipf.write(story_json_path, "story.json")
    # Ajout du thumbnail
    zipf.write(thumbnail_path, "thumbnail.png")
    # Ajout de tous les assets
    for root, _, files in os.walk(build_assets):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, build_dir)
            zipf.write(full_path, rel_path)

# === NETTOYAGE ===
shutil.rmtree(build_dir)

# === RAPPORT FINAL ===
print("=" * 60)
print("✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS")
print("=" * 60)
print(f"📦 Archive ZIP : {os.path.basename(zip_filename)}")
print(f"📁 Catégories traitées : {len(menu_structure)}")

total_words = sum(len(words) for words in menu_structure.values())
print(f"📝 Total de mots : {total_words}")

print("\n📋 DÉTAIL DES CATÉGORIES :")
for menu_id, words in sorted(menu_structure.items()):
    menu_key = f"{menu_id}-00"
    menu_label = label_mapping.get(menu_key, f"Catégorie {menu_id}")
    print(f"  {format_number_02d(int(menu_id))}. {menu_label} ({len(words)} mots)")

print("=" * 60)