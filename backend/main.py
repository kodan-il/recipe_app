from tokenize import String

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from urllib.parse import quote
import time
import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me

app = FastAPI(title="Recipe Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

recipe_example = [
{
        "id": 1,
        "title": "Nasi Goreng Telur",
        "ingredients": ["nasi", "telur", "bawang putih", "kecap", "garam"],
        "instructions": ["Tumis bawang putih.", "Masukkan telur lalu orak-arik.", "Masukkan nasi dan kecap, aduk rata."],
        "url": "https://cookpad.com/id/resep/26898751?ref=search&search_term=nasi+goreng"
    },
    {
        "id": 2,
        "title": "Tahu Telur Praktis",
        "ingredients": ["tahu", "telur", "garam", "bawang merah"],
        "instructions": ["Kocok telur dan tahu potongan dadu.", "Goreng hingga kecokelatan."],
        "url": "https://cookpad.com/id/resep/14933518?ref=search&search_term=tahu+telur"
    }
]

HEADERS ={
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

RECIPE_CACHE: Dict[str, Dict[str, Any]] = {}

def search_cookpad(query:str, limit: int = 5) -> List[str]:
    "Finding url list for indonesian recipe from cookpad.com"
    encoded_query = quote(query.strip())
    search_url = f"https://cookpad.com/id/cari/{encoded_query}"

    response = requests.get(search_url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    urls: List[str] = []

    for aLink in soup.find_all("a", href=True):
        href = aLink.get("href")
        #U URL Cookpad Indonesia uses 'id/resep/' or '/resep/'
        if isinstance(href, str) and "/resep/" in href:
            full_url = href if href.startswith("http") else f"https://cookpad.com{href}"
            clean_url = full_url.split("?")[0]  # Remove query parameters
            if clean_url not in urls:
                urls.append(clean_url)
        if len(urls) >= limit:
            break

    return urls

def scrape_cookpad_detail(url: str) -> Dict[str, Any] | None:
    """Getting recipe detail with recipe-scrapers using CACHE"""
    if url in RECIPE_CACHE:
        return RECIPE_CACHE[url]

    try:
        scraper = scrape_me(url)
        recipe_data = {
            "id": url,
            "title": scraper.title(),
            "ingredients": scraper.ingredients(),
            "instructions": (
                scraper.instructions().split("\n")
                if isinstance(scraper.instructions(), str)
                else scraper.instructions()
            ),
            "image": scraper.image(),
            "url": url
        }
        RECIPE_CACHE[url] = recipe_data
        return recipe_data
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

@app.get("/")
def home():
    return {"message": "Recipe engine backend is running!"}

@app.post("/api/recipes/by-ingredients")
def get_recipes_by_ingredients(user_ingredients: List[str]):

    cleaned = [ingredient.strip().lower() for ingredient in user_ingredients if ingredient.strip()]
    if not cleaned:
        return []

    query_str = " ".join(cleaned)
    urls = search_cookpad(query_str, limit=5)

    users_set = set(cleaned)
    matched_results = []

    for idx, url in enumerate(urls):
        if idx > 0 and url not in RECIPE_CACHE:
            time.sleep(1)  # Delay to avoid rate limit

        recipe = scrape_cookpad_detail(url)
        if not recipe or not isinstance(recipe, dict):
            continue
        
        ingredients_text = " ".join(recipe.get("ingredients", [])).lower()
        matching = [i for i in users_set if i in ingredients_text]

        matched_results.append({
            "recipe": recipe,
            "match_count": len(matching),
            "matched_ingredients": matching
        })

    print("Query:", query_str)
    print("Found URLs:", urls)
    print("Scrapped count:" , len(matched_results))
    print("Results:", matched_results)
    return {"results": matched_results}

@app.get("/api/recipes/search")
def search_recipes_by_name(q: str = Query(..., min_length=1)):
    urls = search_cookpad(q, limit=5)
    results = []

    for idx, url in enumerate(urls):
        if idx > 0 and url not in RECIPE_CACHE:
            time.sleep(1)  # Delay to avoid rate limit

        recipe = scrape_cookpad_detail(url)
        if not recipe or not isinstance(recipe, dict):
            continue

        results.append({
            "recipe": recipe,
            "match_count" : 0,
            "matched_ingredients": []
        })

    return results

@app.get("/api/recipes/scrape")
def scrape_recipe(url: str = Query(..., description="URL of the recipe to scrape")):
    try:
        scraper = scrape_me(url)
        return {
            "title": scraper.title(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions()
        }
    except Exception as e:
        return {"error": f"error fetching recipe: {str(e)}"}

