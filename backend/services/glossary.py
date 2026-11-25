import re
from typing import Dict, List, Tuple

class RecipeGlossary:

    RECIPE_GLOSSARY_PRE: Dict[str, str] = {
        "kecap manis": "sweet soy sauce",
        "kecap asin": "salty soy sauce",
        "daun jeruk": "kaffir lime leaves",
        "daun salam": "indonesian bay leaves",
        "bawang putih": "garlic",
        "bawang merah": "shallots",
        "bawang bombay": "onion",
        "telur puyuh": "quail eggs",
        "tahu putih": "white tofu",
        "tahu kuning": "yellow tofu",
        "cabai rawit": "cayenne pepper",
        "cabai merah": "red chili",
        "santan cair": "thin coconut milk",
        "santan kental": "thick coconut milk",
        "potong dadu": "diced",
        "iris tipis": "thinly sliced",
        "haluskan": "grind",
        "santan": "coconut milk",
        "tempe": "tempeh",
        "terasi": "shrimp paste",
        "kemiri": "candlenut",
        "kunyit": "turmeric",
        "lengkuas": "galangal",
        "serai": "lemongrass",
        "tumis": "sauté",
        "tahu": "tofu",
        "udang": "shrimp",
        "sdm": "tbsp",
        "sdt": "tsp",
        "siung": "cloves",
        "lembar": "leaves",
        "btr": "pieces",
        "bh": "pieces",
        "ceplok" : "fried",
        "telor" : "eggs",
        "satset": "quick",
        "baso": "meatball",
        "masak": "style",
    }

    RECIPE_GLOSSARY_POST: Dict[str, str] = {
        "sauces know": "tofu",
        "knows": "tofu",
        " know ": " tofu ",
        "sautéed": "sauté",
    }

    def __init__(self):
        sorted_pre = sorted(self.PRE_RECIPE_GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True)
        self._pre_patterns: List[Tuple[re.Pattern, str]] = [
                (re.compile(re.escape(k), re.IGNORECASE), v) for k, v in sorted_pre
            ]
            
        self._post_patterns: List[Tuple[re.Pattern, str]] = [
                (re.compile(re.escape(k), re.IGNORECASE), v) for k, v in self.POST_GLOSSARY.items()
            ]


    def apply_glossary_pre(self, text: str) -> str:
        result = text
        sorted_glossary = sorted(self.RECIPE_GLOSSARY_PRE.items(), key=lambda x: len(x[0]), reverse=True)

        for id_term, en_term in sorted_glossary:
            pattern = re.compile(re.escape(id_term), re.IGNORECASE)
            result = pattern.sub(en_term, result)

        return result

    def apply_glossary_post(self,text: str) -> str:
        result = text
        for bad_term, fixed_term in self.RECIPE_GLOSSARY_POST.items():
            pattern = re.compile(re.escape(bad_term), re.IGNORECASE)
            result = pattern.sub(fixed_term, result)
        return result