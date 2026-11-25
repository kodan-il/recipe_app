import re
import time
from typing import Any, Dict, List
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
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

to_id_translator = GoogleTranslator(source="auto", target="id")
to_en_translator = GoogleTranslator(source="auto", target="en")

HEADERS ={
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

RECIPE_CACHE: Dict[str, Dict[str, Any]] = {}
TRANSLATION_CACHE: Dict[str, str] = {}
EN_RECIPE_CACHE : Dict[str, Dict[str, Any]] = {}

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
        elif isinstance(raw_instructions, list):
            steps = [str(s).strip() for s in raw_instructions if str(s).strip()]
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

def translate_safe(text: str, target_lang: str = "en") -> str:
    if not text or not text.strip():
        return text

    cleaned = clean_for_translate(text) or text.strip()
    cache_key = f"{target_lang}:{cleaned}"
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]
    try:
        translator = to_en_translator if target_lang == "en" else to_id_translator
        translated = translator.translate(text)
        final_str = translated if isinstance(translated, str) and translated.strip() else cleaned
        TRANSLATION_CACHE[cache_key] = final_str
        return translated if isinstance(translated, str) else text
    except Exception as e:
        print(f"Translation warning ({target_lang}): {e}")
        return text

def translate_batch_safe(texts: List[str], target_lang: str = "en") -> List[str]:
    if not texts:
        return []

    translator = to_en_translator if target_lang == "en" else to_id_translator
    results: List[str] = []
    missing_indices: List[int] = []
    to_translate: List[str] = []

    for idx, raw in enumerate(texts):
        original = str(raw or "").strip()
        if not original:
            results.append("")
            continue

        cleaned = clean_for_translate(original) or original
        cache_key = f"{target_lang}:{cleaned}"

        if cache_key in TRANSLATION_CACHE:
            results.append(TRANSLATION_CACHE[cache_key])
        else:
            results.append(original)
            missing_indices.append(idx)
            to_translate.append(cleaned)

    chunk_size = 8
    for start in range(0, len(to_translate), chunk_size):
        chunk_texts = to_translate[start: start + chunk_size]
        chunk_idx = missing_indices[start: start + chunk_size]
        try:
            translated_list = translator.translate_batch(chunk_texts)
            for idx, orig_clean, trans in zip(chunk_idx, chunk_texts, translated_list):
                final_str = trans if isinstance(trans, str) and trans.strip() else orig_clean
                results[idx] = final_str
                TRANSLATION_CACHE[f"{target_lang}:{orig_clean}"] = final_str
            time.sleep(0.4)  # Delay to avoid rate limit
        except Exception as e:
            print(f"Batch translate fallback ({target_lang}): {e}")
            for idx, orig_clean in zip(chunk_idx, chunk_texts):
                try:
                    single = translator.translate(orig_clean)
                    final_str = single if isinstance(single, str)  and single.strip() else orig_clean
                except Exception:
                    final_str = orig_clean

                results[idx] = final_str
                TRANSLATION_CACHE[f"{target_lang}:{orig_clean}"] = final_str
                time.sleep(0.3)

    
    return results

def recipe_to_english(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Translate recipe fields to English"""
    cache_key = str(recipe.get("url") or recipe.get("id") or "")
    if cache_key and cache_key in EN_RECIPE_CACHE:
        return EN_RECIPE_CACHE[cache_key]

    
    result = dict(recipe)
    title_str = str(recipe.get("title")or "")
    raw_ingredients = [str(x) for x in (recipe.get("ingredients") or []) if x is not None]
    raw_instructions = [str(x) for x in (recipe.get("instructions") or []) if x is not None]

    combined = [title_str] + raw_ingredients + raw_instructions
    translated = translate_batch_safe(combined, target_lang="en")

    num_ingredients = len(raw_ingredients)
    result["title"] = translated[0] if translated else title_str
    result["ingredients"] = translated[1 : 1 + num_ingredients]
    result["instructions"] = translated[1 + num_ingredients :]

    return result

def clean_for_translate(text: str) -> str:
    no_emoji = re.sub(r"[^\w\s.,!?;:()'\"-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", no_emoji).strip()

@app.get("/")
def home():
    return {"message": "Recipe engine backend is running!"}

@app.post("/api/recipes/by-ingredients")
def get_recipes_by_ingredients(user_ingredients: List[str]):
    cleaned = [ingredient.strip().lower() for ingredient in user_ingredients if ingredient.strip()]
    if not cleaned:
        return []

    id_ingredients = [translate_safe(item, "id").lower() for item in cleaned]
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
        title_en = translate_safe(str(recipe.get("title") or ""), "en")
        matched_en = [translate_safe(m, "en") for m in matching_id]
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
    en_recipe = recipe_to_english(recipe)
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

