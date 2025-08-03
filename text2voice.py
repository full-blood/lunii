import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pydub import AudioSegment
import io
import time
import urllib.parse
from gtts import gTTS  # Fallback option

def get_edge_tts_audio(text, lang='en', voice_preference=None):
    """
    Utilise Edge-TTS (Microsoft) avec choix de voix
    """
    try:
        import edge_tts
        import asyncio
        
        # Voix par défaut pour chaque langue
        default_voices = {
            'en': ['en-GB-ThomasNeural', 'en-GB-LibbyNeural'],  # Thomas en premier, Libby en backup
            'fr': ['fr-FR-DeniseNeural']   # Voix française de qualité
        }
        
        # Utiliser la voix spécifiée ou les voix par défaut
        if voice_preference:
            voices_to_try = [voice_preference]
        else:
            voices_to_try = default_voices.get(lang, default_voices['en'])
        
        async def get_audio_with_voice(voice):
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        
        # Essayer chaque voix dans l'ordre
        for voice in voices_to_try:
            try:
                print(f"    🎤 Essai voix: {voice}")
                audio_data = asyncio.run(get_audio_with_voice(voice))
                
                if audio_data:
                    print(f"    ✅ Succès avec {voice}")
                    return AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            except Exception as voice_error:
                print(f"    ❌ Échec {voice}: {voice_error}")
                continue
        
        return None
        
    except ImportError:
        print("    ⚠️  edge-tts non installé")
        return None
    except Exception as e:
        print(f"    ⚠️  Erreur Edge-TTS générale: {e}")
        return None

def download_wordreference_audio(word, lang='en'):
    """
    Télécharge l'audio depuis WordReference pour un mot donné
    
    Args:
        word (str): Le mot à télécharger
        lang (str): 'en' pour anglais, 'fr' pour français
    
    Returns:
        AudioSegment or None: L'audio téléchargé ou None si échec
    """
    try:
        # URL de WordReference
        if lang == 'en':
            url = f"https://www.wordreference.com/definition/{urllib.parse.quote(word)}"
        else:  # français
            url = f"https://www.wordreference.com/fren/{urllib.parse.quote(word)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher les liens audio (WordReference utilise différents formats)
        audio_links = []
        
        # Méthode 1: liens directs vers fichiers audio
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and ('.mp3' in href or '.wav' in href or 'audio' in href):
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://www.wordreference.com' + href
                audio_links.append(href)
        
        # Méthode 2: chercher dans les scripts JavaScript pour les URLs audio
        for script in soup.find_all('script'):
            if script.string:
                text = script.string
                # Patterns courants pour les URLs audio
                import re
                patterns = [
                    r'https?://[^"\']*\.mp3[^"\']*',
                    r'https?://[^"\']*audio[^"\']*',
                    r'/audio/[^"\']*\.mp3'
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        if match.startswith('/'):
                            match = 'https://www.wordreference.com' + match
                        audio_links.append(match)
        
        # Essayer de télécharger le premier lien audio trouvé
        for audio_url in audio_links[:3]:  # Limiter aux 3 premiers
            try:
                audio_response = requests.get(audio_url, headers=headers, timeout=10)
                if audio_response.status_code == 200 and len(audio_response.content) > 1000:
                    return AudioSegment.from_file(io.BytesIO(audio_response.content))
            except:
                continue
                
        return None
        
    except Exception as e:
        print(f"    ⚠️  Erreur WordReference pour '{word}': {e}")
        return None

def get_quality_audio(word, lang='en', max_retries=1):
    """
    Essaie plusieurs sources pour obtenir un audio de qualité
    Ordre: WordReference → Edge-TTS (Thomas puis Libby) → gTTS
    
    Args:
        word (str): Le mot
        lang (str): Langue ('en' ou 'fr')
        max_retries (int): Nombre maximum de tentatives
    
    Returns:
        AudioSegment or None
    """
    # 1. Essayer WordReference en premier
    for attempt in range(max_retries):
        try:
            print(f"    🔍 Tentative WordReference ({attempt + 1}/{max_retries})")
            wr_audio = download_wordreference_audio(word, lang)
            if wr_audio:
                print(f"    ✅ Audio trouvé via WordReference")
                return wr_audio
            time.sleep(1)  # Pause entre tentatives
        except Exception as e:
            print(f"    ❌ Échec WordReference: {e}")
            continue
    
    # 2. Essayer Edge-TTS (Thomas puis Libby pour l'anglais)
    print(f"    🎤 Tentative Edge-TTS...")
    edge_audio = get_edge_tts_audio(word, lang)
    if edge_audio:
        return edge_audio
    
    # 3. Fallback vers gTTS
    try:
        print(f"    🔄 Fallback vers gTTS...")
        tts = gTTS(text=word, lang=lang)
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        audio = AudioSegment.from_mp3(audio_io)
        print(f"    ✅ Audio créé via gTTS")
        return audio
    except Exception as e:
        print(f"    ❌ Échec gTTS: {e}")
        return None

def create_word_audio_enhanced(word_en, word_fr, output_file, pause_duration=800):
    """
    Version améliorée avec sources audio de qualité
    """
    try:
        print(f"  🎵 Création audio pour: {word_en} → {word_fr}")
        
        # Télécharger l'audio anglais
        print(f"    🇬🇧 Recherche audio anglais...")
        en_audio = get_quality_audio(word_en, 'en')
        
        if not en_audio:
            print(f"    ❌ Impossible de créer l'audio anglais pour '{word_en}'")
            return False
        
        # Télécharger l'audio français
        print(f"    🇫🇷 Recherche audio français...")
        fr_audio = get_quality_audio(word_fr, 'fr')
        
        if not fr_audio:
            print(f"    ❌ Impossible de créer l'audio français pour '{word_fr}'")
            return False
        
        # Créer les pauses
        pause = AudioSegment.silent(duration=pause_duration)
        postpause = AudioSegment.silent(duration=(pause_duration//2))
        
        # Combiner
        combined_audio = en_audio + pause + fr_audio + postpause
        
        # Normaliser le volume
        combined_audio = combined_audio.normalize()
        
        # Sauvegarder
        combined_audio.export(output_file, format="mp3")
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur pour '{word_en}' - '{word_fr}': {e}")
        return False

def create_category_file(category_name, output_file):
    """
    Crée un fichier audio avec le nom de la catégorie en français
    """
    try:
        category_clean = category_name.replace("/", "et")
        
        # Essayer d'abord une source de qualité
        fr_audio = get_quality_audio(category_clean, 'fr', max_retries=1)
        
        if fr_audio:
            fr_audio.export(output_file, format="mp3")
        else:
            print(f"  ❌ Impossible de créer l'audio pour la catégorie '{category_name}'")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Erreur catégorie '{category_name}': {e}")
        return False

def process_category(category_name, category_words, output_dir, pause_duration=1500):
    """
    Traite une catégorie avec audio de meilleure qualité
    """
    print(f"📁 Traitement catégorie : {category_name}")
    
    # Créer le nom de dossier sécurisé
    safe_category_name = category_name.replace(" ", "_").replace("/", "et")
    category_dir = os.path.join(output_dir, "")
    os.makedirs(category_dir, exist_ok=True)
    
    # 1. Créer le fichier catégorie
    category_file = os.path.join(category_dir, f"{categ_nb:02d}-00_{safe_category_name}.mp3")
    if create_category_file(category_name, category_file):
        print(f"  ✅ Catégorie créée : {os.path.basename(category_file)}")
    
    # 2. Créer un fichier par mot
    created_files = []
    for i, (word_en, word_fr) in enumerate(category_words, 1):
        # Nom de fichier sécurisé
        safe_word_en = word_en.replace(" ", "_").replace("/", "_")
        safe_word_fr = word_fr.replace(" ", "_").replace("/", "_")
        
        word_file = os.path.join(category_dir, f"{categ_nb:02d}-{i:02d}_{safe_word_en}.mp3")
        
        print(f"  🎵 Création {i:2d}/{len(category_words)}: {word_en} → {word_fr}")
        
        if create_word_audio_enhanced(word_en, word_fr, word_file, pause_duration):
            created_files.append(word_file)
            print(f"    ✅ Créé : {os.path.basename(word_file)}")
        
        # Pause respectueuse entre requêtes (seulement pour WordReference)
        time.sleep(1)
    
    print(f"  🎉 Catégorie terminée : {len(created_files)} mots + 1 catégorie\n")
    
    return len(created_files)

# Configuration et exécution
if __name__ == "__main__":
    print("🎤 Générateur d'audio avec WordReference + Edge-TTS + gTTS")
    print("🔄 Ordre de priorité:")
    print("   1️⃣ WordReference")
    print("   2️⃣ Edge-TTS (en-GB-ThomasNeural puis en-GB-LibbyNeural)")
    print("   3️⃣ gTTS (fallback)")
    print()
    
    # Vérifier Edge-TTS
    try:
        import edge_tts
        print("✅ Edge-TTS disponible")
    except ImportError:
        print("⚠️  Edge-TTS non installé. Installation:")
        print("   pip install edge-tts")
        print("   (Le script continuera avec WordReference + gTTS)")
    
    # Charger le fichier CSV
    print("\n📊 Chargement du fichier CSV...")
    df = pd.read_csv("vocabulaire_anglais_100w_EnFr.csv")

    # Créer le dossier de sortie
    output_dir = "assets"
    os.makedirs(output_dir, exist_ok=True)

    # Grouper les mots par catégorie
    print("🔄 Groupement par catégories...")
    categories = {}
    for _, row in df.iterrows():
        category = row["Category"]
        word_en = row["Word"]
        word_fr = row["French"]
        
        if category not in categories:
            categories[category] = []
        
        categories[category].append((word_en, word_fr))

    # Configuration
    pause_duration = 1000  # 1 seconde de pause

    print(f"\n🎵 Génération des fichiers audio...")
    print(f"📚 {len(categories)} catégories à traiter")
    print(f"⏱️  Pause entre anglais/français : {pause_duration/1000}s")
    print(f"📁 Dossier de sortie : {output_dir}\n")

    # Traiter chaque catégorie
    total_files = 0
    categ_nb = 1
    for category_name, words in categories.items():
        files_created = process_category(
            category_name=category_name,
            category_words=words,
            output_dir=output_dir,
            pause_duration=pause_duration,
        )
        categ_nb = categ_nb + 1
        total_files += files_created + 1  # +1 pour le fichier catégorie

    print("🎉 Génération terminée avec succès !")
    print(f"📁 Tous les fichiers sont dans : {output_dir}")
    print(f"📊 {total_files} fichiers audio créés au total")