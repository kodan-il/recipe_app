## Indonesian Recipe Finder App

A test case scenario of Indonesian recipe application finder that automatically translated into English directly.

This app featuring **FastAPI** RESTfulAPI backend with **offline translation** (`Argos Translate` + custom culinary glossary & caching) and **React + Vite** frontend.

## Project Structure
- `backend/` - FastAPI application, recipe scraping, and offline translation services.
- `frontend/` - React + Vite user interface

## Tech stacks and Dependencies
### Backend (Python)
- **FastAPI & Uvicorn** - RESTful API framework and ASGI server
- **ARGOS Translate** - Local oofline translation engine (ID <-> EN) combined with a custom recipe glossary and in-memory caching
- **Recipe-Scrapers, Reqeusts, & BeautifulSoup4** - Recipe scraping and HTML Parsing

### Frontend (React)
- **React** - UI Components for searching and viewing recipe details
- **Vite** - Frontend build tool and development server

## Setup and Running Local

### 1. Backend
```bash
cd backend
python3 -m venv myenv
./myenv/bin/pip install --upgrade pip
./myenv/bin/pip install -r requirements.txt

./myenv/bin/python -c "
import argostranslate.package

argostranslate.package.update_package_index()
packages = argostranslate.package.get_available_packages()
for src, dst in [('id', 'en'), ('en', 'id')]:
    pkg = next((p for p in packages if p.from_code == src and p.to_code == dst), None)
    if pkg:
        print(f'Installing {src} -> {dst}...')
        argostranslate.package.install_from_path(pkg.download())
print('Done.')
"

./myenv/bin/python -m uvicorn main:app --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```