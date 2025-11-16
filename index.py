import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Fonction pour extraire tous les noms de Pokémon depuis la page nationale
def extract_all_pokemon_names(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    names = [a.text.strip() for a in soup.find_all("a", class_="ent-name")]
    return names

# Fonction pour générer le lien Pokédex pour chaque Pokémon
def get_pokedex_url(name):
    base_url = "https://pokemondb.net/pokedex/"
    # Cas particuliers pour certains noms
    if name.lower() == "farfetch'd":
        return base_url + "farfetchd"
    if name.lower() in ["nidoran♀", "nidoran", "nidoran-f"]:
        return base_url + "nidoran-f"
    if name.lower() in ["nidoran♂", "nidoran", "nidoran-m"]:
        return base_url + "nidoran-m"
    # Nettoyer le nom : minuscules, espaces et caractères spéciaux remplacés par '-'
    name_clean = name.lower()
    name_clean = name_clean.replace(" ", "-")
    return f"{base_url}{name_clean}"


# Extraire tous les noms de Pokémon et générer leurs liens
national_url = "https://pokemondb.net/pokedex/national"
all_names = extract_all_pokemon_names(national_url)
links = [get_pokedex_url(name) for name in all_names]
df_names = pd.DataFrame({"Nom": all_names, "Lien": links})
df_names.to_csv("pokemon_names.csv", index=False, encoding="utf-8")


# --- Demander à l'utilisateur combien de Pokémon scraper ---
df_names = pd.read_csv("pokemon_names.csv")
try:
    n = int(input("Combien de Pokémon voulez-vous scraper ? "))
    if n < 1 or n > len(df_names):
        print(f"Nombre invalide, on prendra {min(10, len(df_names))} par défaut.")
        n = min(10, len(df_names))
except Exception:
    print(f"Entrée invalide, on prendra 10 par défaut.")
    n = 10
selected_pokemon = df_names.head(n)


# Fonction pour générer le lien de l'image à partir du nom du Pokémon
def get_pokemon_image_url(name):
    base_url = "https://img.pokemondb.net/artwork/large/"
    # Cas particuliers pour certains noms
    if name.lower() == "farfetch'd":
        return base_url + "farfetchd.avif"
    if name.lower() in ["nidoran♀", "nidoran\u001e", "nidoran-f"]:
        return base_url + "nidoran-f.jpg"
    if name.lower() in ["nidoran♂", "nidoran\u001a", "nidoran-m"]:
        return base_url + "nidoran-m.jpg"
    # Nettoyer le nom : minuscules, espaces et caractères spéciaux remplacés par '-'
    name_clean = name.lower()
    name_clean = re.sub(r"[^a-z0-9]+", "-", name_clean)
    name_clean = name_clean.strip('-')
    return f"{base_url}{name_clean}.jpg"

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
    image_url = get_pokemon_image_url(name)
    data_with_name = {"Nom": name}
    data_with_name.update(data)
    data_with_name["Image"] = image_url
    all_pokemon_data.append(data_with_name)

# Convertir en DataFrame et sauvegarder
df = pd.DataFrame(all_pokemon_data)
df.to_csv("pokedex_data.csv", index=False, encoding="utf-8")
print(df)