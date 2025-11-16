import shutil
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

# Fonction pour extraire tous les noms de Pokémon et leurs liens exacts depuis la page nationale
def extract_all_pokemon_names_and_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    names = []
    links = []
    for a in soup.find_all("a", class_="ent-name"):
        names.append(a.text.strip())
        href = a.get("href", "")
        if href.startswith("/pokedex/"):
            links.append("https://pokemondb.net" + href)
        else:
            links.append("")
    return names, links

# Extraire tous les noms de Pokémon et leurs liens exacts
national_url = "https://pokemondb.net/pokedex/national"
all_names, links = extract_all_pokemon_names_and_links(national_url)
df_names = pd.DataFrame({"Nom": all_names, "Lien": links})

# Créer le dossier csv s'il n'existe pas
os.makedirs("csv", exist_ok=True)

csv_names_path = os.path.join("csv", "pokemon_names.csv")
df_names.to_csv(csv_names_path, index=False, encoding="utf-8")
print("Le fichier pokemon_names.csv a été généré avec", len(df_names), "Pokémon.")
ok = input("La génération du CSV est-elle correcte ? (o/n) ")
if ok.strip().lower() != 'o':
    print("Arrêt du script. Vérifiez le CSV.")
    exit(0)


# --- Demander à l'utilisateur combien de Pokémon scraper ---
df_names = pd.read_csv(csv_names_path)
try:
    n = int(input("Combien de Pokémon voulez-vous scraper ? "))
    if n < 1 or n > len(df_names):
        print(f"Nombre invalide, on prendra {min(10, len(df_names))} par défaut.")
        n = min(10, len(df_names))
except Exception:
    print(f"Entrée invalide, on prendra 10 par défaut.")
    n = 10
selected_pokemon = df_names.head(n)


# Fonction pour récupérer dynamiquement le lien de l'image officielle depuis la page du Pokémon
def get_pokemon_image_url(soup):
    a_img = soup.find("a", rel="lightbox")
    if a_img and a_img.has_attr("href"):
        return a_img["href"]
    return ""

# Fonction générique pour extraire les infos d'un tableau à partir du titre h2
def extract_table_data(soup, h2_title):
    """Extrait les infos d'un tableau identifié par le titre h2 sous forme de dictionnaire."""
    h2 = soup.find("h2", string=h2_title)
    data = {}
    if h2:
        table = h2.find_next("table", class_="vitals-table")
        if table:
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.text.strip()
                    # Pour les types, abilities, local numbers, on veut le texte complet (avec <br> séparés)
                    if key in ["Type", "Abilities", "Local №"]:
                        value = " | ".join([t.strip() for t in td.stripped_strings])
                    else:
                        value = td.text.strip()
                    data[key] = value
    return data



# --- Scraping des infos pour le nombre choisi de Pokémon ---
all_pokemon_data = []
for _, row in selected_pokemon.iterrows():
    name = row["Nom"]
    url = row["Lien"]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    # Utilisation de la fonction pour extraire les données de plusieurs tableaux
    data = {}
    for section in ["Pokédex data", "Training", "Breeding", "Base stats"]:
        section_data = extract_table_data(soup, section)
        for k, v in section_data.items():
            if k in data:
                data[f"{section} - {k}"] = v
            else:
                data[k] = v
    image_url = get_pokemon_image_url(soup)
    data_with_name = {"Nom": name}
    data_with_name.update(data)
    data_with_name["Image"] = image_url
    all_pokemon_data.append(data_with_name)

# Convertir en DataFrame et sauvegarder
df = pd.DataFrame(all_pokemon_data)
csv_data_path = os.path.join("csv", "pokedex_data.csv")
df.to_csv(csv_data_path, index=False, encoding="utf-8")
print(df)


# --- Vérification des liens des CSV pour erreurs 404 ---
def check_links_for_404(csv_path, column):
    import requests
    df = pd.read_csv(csv_path)
    errors = []
    for i, url in enumerate(df[column]):
        if not isinstance(url, str) or not url.startswith("http"):
            errors.append((i, url, "URL invalide"))
            continue
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code == 404:
                errors.append((i, url, "404"))
        except Exception as e:
            errors.append((i, url, str(e)))
    if errors:
        print(f"Erreurs détectées dans {csv_path} (colonne {column}):")
        for idx, url, err in errors:
            print(f"  Ligne {idx+1}: {url} -> {err}")
    else:
        print(f"Aucune erreur 404 détectée dans {csv_path} (colonne {column})")

do_check = input("Voulez-vous vérifier les liens des CSV ? (o/n) ")
if do_check.strip().lower() == 'o':
    print("\nVérification des liens du CSV des noms :")
    check_links_for_404(csv_names_path, "Lien")
    print("\nVérification des liens du CSV des images :")
    check_links_for_404(csv_data_path, "Image")



# --- Téléchargement des 5 premières images du CSV pokedex_data.csv ---
def download_images_from_csv(csv_path, column, dest_folder, n=5):
    df = pd.read_csv(csv_path)
    os.makedirs(dest_folder, exist_ok=True)
    for i, url in enumerate(df[column].head(n)):
        if not isinstance(url, str) or not url.startswith("http"):
            print(f"Image {i+1}: URL invalide, ignorée.")
            continue
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                ext = os.path.splitext(url)[1]
                if not ext or len(ext) > 5:
                    ext = ".jpg"
                filename = f"{i+1}{ext}"
                path = os.path.join(dest_folder, filename)
                with open(path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                print(f"Image {i+1} téléchargée : {filename}")
            else:
                print(f"Image {i+1}: Erreur HTTP {response.status_code}")
        except Exception as e:
            print(f"Image {i+1}: Erreur {e}")

do_dl = input("Voulez-vous télécharger les 5 premières images ? (o/n) ")
if do_dl.strip().lower() == 'o':
    download_images_from_csv(os.path.join("csv", "pokedex_data.csv"), "Image", "images", n=5)