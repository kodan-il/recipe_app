import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app
from app.services.glossary import RecipeGlossary
from app.services.scrapper import ScraperError, scrapper
from app.services.translator import RecipeTranslator

client = TestClient(app)


def test_glossary_pre_and_post_processing():
    glossary = RecipeGlossary()

    pre = glossary.apply_glossary_pre("1 kotak tahu putih, potong dadu")
    assert "white tofu" in pre.lower()
    assert "diced" in pre.lower()

    post = glossary.apply_glossary_post("sauces know")
    assert post.lower() == "tofu"


def test_translator_uses_cache_with_mocked_engine(monkeypatch):
    calls = {"count": 0}

    def fake_translate(text: str, from_code: str, to_code: str) -> str:
        calls["count"] += 1
        return f"translated-{text}"

    monkeypatch.setattr("app.services.translator.argo_translate.translate", fake_translate)

    translator = RecipeTranslator()
    sample = "unique test ingredient xyz"

    first = translator.translate_safe(sample, "en")
    second = translator.translate_safe(sample, "en")

    assert first == second
    assert calls["count"] == 1  # the second call was served from the cache


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_without_filters_returns_422():
    response = client.get("/api/v1/recipes")

    assert response.status_code == 422


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP Error: {self.status_code}")


def test_scrapper_search_returns_recipe_ids(monkeypatch):
    sample_search_html = """
        <html><body>
            <a href="/id/resep/123456-nasi-goreng">Nasi Goreng</a>
            <a href="/id/resep/789012-tahu-telur">Tahu Telur</a>
            <a href="/id/cari">Search page</a>
        </body></html>
    """

    def fake_get(url, headers=None, params=None, timeout=10):
        return DummyResponse(sample_search_html)

    monkeypatch.setattr("app.services.scrapper.requests.get", fake_get)

    ids = scrapper().search("nasi goreng", limit=5)

    assert ids == ["123456", "789012"]  # ids only; non-recipe links are ignored


def test_scrapper_wraps_network_errors(monkeypatch):
    def failing_get(*args, **kwargs):
        raise requests.ConnectionError("Offline test")

    monkeypatch.setattr("app.services.scrapper.requests.get", failing_get)

    with pytest.raises(ScraperError):
        scrapper().search("tahu", limit=5)