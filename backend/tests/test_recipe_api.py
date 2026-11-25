from fastapi.testclient import TestClient

from main import app
from services.translator import RecipeTranslator
from services.glossary import RecipeGlossary
from services.scrapper import scrapper

client = TestClient(app)

def test_glossary_pre_and_post_processing():
    glossary = RecipeGlossary()

    pre = glossary.apply_glossary_pre("1 kotak tahu putih, potong dadu")
    assert "white tofu" in pre.lower()
    assert "diced" in pre.lower()

    post = glossary.apply_glossary_post("sauces know")
    assert post.lower() == "tofu"

def test_translator_uses_cache_mocked_engine(monkeypatch):

    calls = {"count": 0}
    def fake_translate(text: str, from_code: str, to_code: str) -> str:
        calls["count"] += 1
        return f"translated-{text}"

    monkeypatch.setattr("services.translator.argo_translate.translate", fake_translate)

    translator = RecipeTranslator()
    sample = "unique test ingredient xyz"

    fist = translator.translate_safe(sample, "en")
    second = translator.translate_safe(sample, "en")

    assert fist == second
    assert calls["count"] == 1

def test_home_endpoint():
    response = client.get("/")
    assert response.status_code ==200
    assert "message" in response.json()

def test_by_ingredients_empty_input_returns_empty_results():
    response = client.post("/api/recipes/by-ingredients", json=[])
    data = response.json()
    assert response.status_code == 200
    assert data == {"results": []}

class DummyResponse:
    def __init__(self, text:str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

def test_scrapper_search_recipe(monkeypatch):
    sample_search_html = """
        <html>
        <body>
            <a href="/id/resep/123456-nasi-goreng">Nasi Goreng</a>
            <a href="/id/resep/789012-tahu-telur">Tahu Telur</a>
            <a href="/id/cari">Search page</a>
        </body>
        </html>
    """
    def fake_get(url, headers=None, params=None, timeout=10):
        return DummyResponse(sample_search_html, status_code=200)

    monkeypatch.setattr("services.scrapper.requests.get", fake_get)

    s = scrapper()
    urls = s.search_cookpad("nasi goreng", limit=5)

    assert isinstance(urls, list)
    assert any("123456-nasi-goreng" in url for url in urls)

def test_scrapper_handle_error(monkeypatch):
    def failing_get(*args, **kwargs):
        raise ConnectionError("Offline test")

    monkeypatch.setattr("services.scrapper.requests.get", failing_get)

    s = scrapper()
    urls = s.search_cookpad("tahu", limit=5)

    assert urls == []