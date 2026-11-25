import re
import time
from typing import Any, Dict, List
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator, MyMemoryTranslator
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from recipe_scrapers import scrape_me
import argostranslate.translate as argo_translate

from services.translator import RecipeTranslator

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

to_id_translator = GoogleTranslator(source="auto", target="id")
to_en_translator = GoogleTranslator(source="auto", target="en")

fallback_id = MyMemoryTranslator(source="en-GB", target="id-ID")
fallback_en = MyMemoryTranslator(source="id-ID", target="en-GB")

HEADERS ={
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

RECIPE_CACHE: Dict[str, Dict[str, Any]] = {}
TRANSLATION_CACHE: Dict[str, str] = {}
EN_RECIPE_CACHE : Dict[str, Dict[str, Any]] = {}



## scraping method logic
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
            if href.rstrip("/").endswith("/resep/baru") or "/resep/baru?" in href:
                continue

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

    for item in recipe_example:
        if item["url"].split("?")[0] == url.split("?")[0]:
            RECIPE_CACHE[url] = item
            return item

    try:
        scraper = scrape_me(url)
        raw_instruction = scraper.instructions()
        if isinstance(raw_instruction, str):
            steps = [line.strip() for line in raw_instruction.split("\n") if line.strip()]
        elif isinstance(raw_instruction, list):
            steps = [str(s).strip() for s in raw_instruction if str(s).strip()]
        else:
            steps = []

        recipe_data ={
            "id":url,
            "title": scraper.title(),
            "ingredients": scraper.ingredients() or[],
            "instructions": steps,
            "image": scraper.image(),
            "url": url,
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

    id_ingredients = [RecipeTranslator().translate_safe(item, "id").lower() for item in cleaned]
    users_set = set(id_ingredients)

    query_str = " ".join(id_ingredients)
    urls = search_cookpad(query_str, limit=5)

    candidates =[]
    if not urls:
        for item in recipe_example:
            ingredients_text = " ".join(item.get("ingredients", [])).lower()
            matching_id = [i for i in users_set if i in ingredients_text]
            if matching_id:
                candidates.append((item, matching_id))
    else:
        for idx, url in enumerate(urls):
            if idx > 0 and url not in RECIPE_CACHE:
                time.sleep(0.8)
            
            recipe = scrape_cookpad_detail(url)
            if not recipe or not isinstance(recipe, dict):
                continue
            ingredients_text = " ".join(recipe.get("ingredients", [])).lower()
            matching_id = [i for i in users_set if i in ingredients_text]
            candidates.append((recipe, matching_id))

    summary_results = []
    for recipe, matching_id in candidates:
        title_en = RecipeTranslator().translate_safe(str(recipe.get("title") or ""), "en")
        matched_en = [RecipeTranslator().translate_safe(m, "en") for m in matching_id]
        summary_results.append({
            "recipe":{
                "id": recipe.get("id") or recipe.get("url"),
                "title" : title_en,
                "image": recipe.get("image"),
                "url": recipe.get("url")
            },
            "match_count": len(matching_id),
            "matched_ingredients": matched_en
        })

    summary_results.sort(key=lambda x: x["match_count"], reverse=True)

    print("Query:", query_str)
    print("Found URLs:", urls)
    print("Scrapped count:" , len(candidates))
    print("Results:", summary_results)
    return {"results": summary_results}

@app.get("/api/recipes/detail")
def get_recipe_detail(url:str = Query(..., min_length=5)):
    recipe = scrape_cookpad_detail(url)
    if not recipe or not isinstance(recipe, dict):
        return{"error": "Recipe detail not available", "url" :url}
    en_recipe = RecipeTranslator().recipe_to_english(recipe)
    return {"recipe": en_recipe}


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

