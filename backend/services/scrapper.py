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

HEADERS ={
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

RECIPE_CACHE: Dict[str, Dict[str, Any]] = {}

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

class scrapper:
                        
    ## scraping method logic
    def search_cookpad(self, query:str, limit: int = 5) -> List[str]:
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

    def scrape_cookpad_detail(self, url: str) -> Dict[str, Any] | None:
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



