import re
import time
from typing import Any, Dict, List, cast
from urllib.parse import quote
import logging
from urllib.parse import quote    

import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me
from app import config
from app.services.sample_data import SAMPLE_RECIPES


logger = logging.getLogger(__name__)

RECIPE_ID_PATTERN = re.compile(r"/resep/(\d+)")

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
class ScraperError(Exception):
    """Recipe site could not be reached or parsed."""
    
class scrapper:
    def __init__(self, delay: float = config.SCRAPE_DELAY) -> None:
        self._last_fetch = float('-inf')
        self._delay = delay
        self._cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def url_for(recipe_id: str) -> str:
        return f"{config.COOKPAD_BASE}id/resep/{recipe_id}"

    @staticmethod
    def extract_id(href: str) -> str | None:
        match = RECIPE_ID_PATTERN.search(href)
        if match:
            return match.group(1)
        return None
                        
    ## scraping method logic
    def search_cookpad(self, query:str, limit: int = 5) -> List[str]:
        "Finding url list for indonesian recipe from cookpad.com"
        encoded_query = quote(query.strip())
        search_url = f"{config.COOKPAD_BASE}/id/cari/{encoded_query}"
        try:
            response = requests.get(
                search_url, headers=config.HTTP_HEADERS, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ScraperError(str(e)) from e


        soup = BeautifulSoup(response.text, "html.parser")
        ids: list[str] = []

        for aLink in soup.find_all("a", href=True):
            recipe_id = self.extract_id(str(aLink["href"]))
            if recipe_id and recipe_id not in ids:
                ids.append(recipe_id)
            if len(ids) >= limit:
                break
        return ids

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
                instructions = cast(List[Any], raw_instruction)
                steps = [str(s).strip() for s in instructions if str(s).strip()]
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

    def get(self, recipe_id:str) -> dict | None:
        if recipe_id in self._cache:
            return self._cache[recipe_id]
        if recipe_id in SAMPLE_RECIPES:
            return SAMPLE_RECIPES[recipe_id]

        self._throttle()
        url = self.url_for(recipe_id)
        try:
            page = scrape_me(url)
            recipe = {
                "id": recipe_id,
                "title": page.title(),
                "ingredients": page.ingredients() or [],
                "instructions": self._split_steps(page.instructions()),
                "image": page.image(),
                "url": url,
            }
        except Exception as e:
            logger.warning("Failed to scrape %s", url, exc_info=True)
            return None

        self._cache[recipe_id] = recipe
        return recipe

    def _throttle(self) -> None:
        wait = self._delay - (time.monotonic() - self._last_fetch)
        if wait > 0:
            time.sleep(wait)
        self._last_fetch = time.monotonic()

    @staticmethod
    def _split_steps(raw: str | list | None) -> list[str]:
        if isinstance(raw, str):
            lines = raw.split("\n")
        elif isinstance(raw, list):
            lines = [str(item) for item in raw]
        else:
            return []
        return [line.strip() for line in lines if line.strip()]