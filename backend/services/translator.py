import re
from typing import Any, Dict, Optional, List, Tuple
from backend.main import EN_RECIPE_CACHE, TRANSLATION_CACHE
from deep_translator import GoogleTranslator, MyMemoryTranslator
import argostranslate.translate as argo_translate

from services.glossary import RecipeGlossary

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
        # try:
        #     translator = to_en_translator if target_lang == "en" else to_id_translator
        #     translated = translator.translate(cleaned)
        #     if isinstance(translated, str) and translated.strip():
        #         TRANSLATION_CACHE[cache_key] = translated.strip()
        #         return translated.strip()
        # except Exception:
        #     pass

        # try:
        #     fallback = fallback_en if target_lang == "en" else fallback_id
        #     translate_fallback = fallback.translate(cleaned)
        #     if isinstance(translate_fallback, str) and translate_fallback.strip():
        #         TRANSLATION_CACHE[cache_key] = translate_fallback.strip()
        #         return translate_fallback.strip()
        # except Exception:
        #     pass

        # return ""  # Return empty string if translation fails

    def translate_batch_safe(self, texts: List[str], target_lang: str = "en") -> List[str]:
        return [self.translate_safe(text, target_lang) for text in texts ]
        # if not texts:
        #     return []

        # translator = to_en_translator if target_lang == "en" else to_id_translator
        # results: List[str] = []
        # missing_indices: List[int] = []
        # to_translate: List[str] = []

        # for idx, raw in enumerate(texts):
        #     original = str(raw or "").strip()
        #     if not original:
        #         results.append("")
        #         continue

        #     cleaned = clean_for_translate(original) or original
        #     cache_key = f"{target_lang}:{cleaned}"

        #     if cache_key in TRANSLATION_CACHE:
        #         results.append(TRANSLATION_CACHE[cache_key])
        #     else:
        #         results.append(original)
        #         missing_indices.append(idx)
        #         to_translate.append(cleaned)

        # chunk_size = 8
        # for start in range(0, len(to_translate), chunk_size):
        #     chunk_texts = to_translate[start: start + chunk_size]
        #     chunk_idx = missing_indices[start: start + chunk_size]
        #     try:
        #         translated_list = translator.translate_batch(chunk_texts)
        #         for idx, orig_clean, trans in zip(chunk_idx, chunk_texts, translated_list):
        #             final_str = trans if isinstance(trans, str) and trans.strip() else orig_clean
        #             results[idx] = final_str
        #             TRANSLATION_CACHE[f"{target_lang}:{orig_clean}"] = final_str
        #         time.sleep(0.4)  # Delay to avoid rate limit
        #     except Exception as e:
        #         print(f"Batch translate fallback ({target_lang}): {e}")
        #         for idx, orig_clean in zip(chunk_idx, chunk_texts):
        #             try:
        #                 single = translator.translate(orig_clean)
        #                 final_str = single if isinstance(single, str)  and single.strip() else orig_clean
        #             except Exception:
        #                 final_str = orig_clean

        #             results[idx] = final_str
        #             TRANSLATION_CACHE[f"{target_lang}:{orig_clean}"] = final_str
        #             time.sleep(0.3)

        
        # return results

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

        return result