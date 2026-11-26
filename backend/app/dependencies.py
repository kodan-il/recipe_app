from functools import lru_cache

from fastapi import Depends

from app.services.recipe_service import RecipeService
from app.services.scrapper import scrapper

@lru_cache
def get_scrapper() -> scrapper:
    return scrapper()

@lru_cache
def get_translator():
    from app.services.translator import RecipeTranslator
    return RecipeTranslator()

def get_recipe_service(
    scraper: scrapper = Depends(get_scrapper),
    translator = Depends(get_translator),
) -> RecipeService:
    return RecipeService(scraper, translator)