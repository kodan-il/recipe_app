import re
from typing import Any, Dict, Optional, List
import argostranslate.translate as argo_translate

from app.services.glossary import RecipeGlossary


TRANSLATION_CACHE: Dict[str, str] = {}
EN_RECIPE_CACHE : Dict[str, Dict[str, Any]] = {}

class RecipeTranslator:

    def __init__(self, glossary:Optional[RecipeGlossary]=None):
        self.glossary = glossary or RecipeGlossary()

    @staticmethod
    def clean_for_translate(text: str) -> str:
        no_emoji = re.sub(r"[^\w\s.,!?;:()'\"-]", "", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", no_emoji).strip()

    def translate_safe(self,text: str, target_lang: str = "en") -> str:
        if not text or not text.strip():
            return text

        cleaned = self.clean_for_translate(text) or text.strip()
        cache_key = f"{target_lang}:{cleaned}"
        if cache_key in TRANSLATION_CACHE:
            return TRANSLATION_CACHE[cache_key]

        try:
            from_code = "id" if target_lang == "en" else "en"
            to_code = target_lang
            pre_processed = self.glossary.apply_glossary_pre(cleaned) if target_lang == "en" else cleaned
            translated = argo_translate.translate(pre_processed, from_code, to_code)
            final_result = self.glossary.apply_glossary_post(translated) if target_lang == "en" else translated
            final_result = final_result.strip() if final_result else cleaned

            TRANSLATION_CACHE[cache_key] = final_result
            return final_result
        except Exception as e:
            print(f"Argos Translate failed ({target_lang}): {e}")
            return cleaned

    def translate_batch_safe(self, texts: List[str], target_lang: str = "en") -> List[str]:
        return [self.translate_safe(text, target_lang) for text in texts ]

    def recipe_to_english(self,recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Translate recipe fields to English"""
        cache_key = str(recipe.get("url") or recipe.get("id") or "")
        if cache_key and cache_key in EN_RECIPE_CACHE:
            return EN_RECIPE_CACHE[cache_key]

        
        result = dict(recipe)
        title_str = str(recipe.get("title")or "")
        raw_ingredients = [str(x) for x in (recipe.get("ingredients") or []) if x is not None]
        raw_instructions = [str(x) for x in (recipe.get("instructions") or []) if x is not None]

        combined = [title_str] + raw_ingredients + raw_instructions
        translated = self.translate_batch_safe(combined, target_lang="en")

        num_ingredients = len(raw_ingredients)
        result["title"] = translated[0] if translated else title_str
        result["ingredients"] = translated[1 : 1 + num_ingredients]
        result["instructions"] = translated[1 + num_ingredients :]

        if cache_key:
            EN_RECIPE_CACHE[cache_key] = result
        return result