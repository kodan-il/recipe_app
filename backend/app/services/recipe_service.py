from typing import Literal, Protocol

from app.schemas import RecipeDetail, RecipeSummary
from app.services.sample_data import SAMPLE_RECIPES

class RecipeNotFound(Exception):
    """Recipe not found in the scraper or sample data."""

class Scraper(Protocol):
    def search(self, query: str, limit: int = 5) -> list[str]: ...
    def get(self, recipe_id: str) -> dict | None: ...

class Translator(Protocol):
    def translate_safe(self, text: str, target_lang: str = "en") -> str: ...
    def recipe_to_english(self, recipe: dict) -> dict: ...

class RecipeService:
    def __init__(self, scraper: Scraper, translator: Translator) -> None:
        self._scraper = scraper
        self._translator = translator

    def search_by_ingredients(self, ingredients: list[str], limit: int = 5) -> list[RecipeSummary]:
        wanted = list(
            dict.fromkeys(
                self._translator.translate_safe(item, "id").lower()
                for item in ingredients
            )
        )
        ids = self._scraper.search(" ".join(wanted), limit) or list(SAMPLE_RECIPES)

        summaries = []
        for recipe_id in ids[:limit]:
            recipe = self._scraper.get(recipe_id)
            if recipe is None:
                continue
            haystack = " ".join(recipe["ingredients"]).lower()
            matched = [item for item in wanted if item in haystack]
            if matched:
                summaries.append(self._summarize(recipe, matched))
        return sorted(summaries, key=lambda x: len(x.matched_ingredients), reverse=True)

    def search_by_name(self, query: str, limit: int = 5) -> list[RecipeSummary]:
        summaries = []
        for recipe_id in self._scraper.search(query, limit):
            recipe =self._scraper.get(recipe_id)
            if recipe is not None:
                summaries.append(self._summarize(recipe, matched=[]))
        return summaries

    
    def get_detail(
        self, recipe_id: str, lang: Literal["en", "id"] = "en"
    ) -> RecipeDetail:
        recipe = self._scraper.get(recipe_id)
        if recipe is None:
            raise RecipeNotFound(recipe_id)
        if lang == "en":
            recipe = self._translator.recipe_to_english(recipe)
        return RecipeDetail.model_validate(recipe)

    def _summarize(self, recipe: dict, matched: list[str]) -> RecipeSummary:
        translate = self._translator.translate_safe
        return RecipeSummary(
            id=str(recipe["id"]),
            title=translate(str(recipe.get("title") or ""), "en"),
            image=recipe.get("image"),
            url=recipe["url"],
            match_count=len(matched),
            matched_ingredients=[translate(item, "en") for item in matched],
        )