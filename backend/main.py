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
from services.scrapper import scrapper

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
    urls = scrapper().search_cookpad(query_str, limit=5)

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
            
            recipe = scrapper().scrape_cookpad_detail(url)
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
    recipe = scrapper().scrape_cookpad_detail(url)
    if not recipe or not isinstance(recipe, dict):
        return{"error": "Recipe detail not available", "url" :url}
    en_recipe = RecipeTranslator().recipe_to_english(recipe)
    return {"recipe": en_recipe}


@app.get("/api/recipes/search")
def search_recipes_by_name(q: str = Query(..., min_length=1)):
    urls = scrapper().search_cookpad(q, limit=5)
    results = []

    for idx, url in enumerate(urls):
        if idx > 0 and url not in RECIPE_CACHE:
            time.sleep(1)  # Delay to avoid rate limit

        recipe = scrapper().scrape_cookpad_detail(url)
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

