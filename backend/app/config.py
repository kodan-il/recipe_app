import os

# Comma-separated list, e.g. ALLOWED_ORIGINS="http://localhost:5173,https://myapp.com"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

COOKPAD_BASE = "https://cookpad.com"
REQUEST_TIMEOUT = 10  # seconds
SCRAPE_DELAY = 0.8  # minimum seconds between requests to Cookpad

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}
