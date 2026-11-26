from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, HTTPException, Path

from app.dependencies import get_recipe_service
from app.schemas import RecipeDetail,RecipeSearchResponse,RecipeSummary
from app.services.recipe_service import RecipeService, RecipeNotFound
from app.services.scrapper import ScraperError

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])

ServiceDep = Annotated[RecipeService, Depends(get_recipe_service)]

def _parse_ingredients(raw: list[str] | None) -> list[str]:
    parts = (part for value in raw or [] for part in value.split(","))
    return [part.strip() for part in parts if part.strip()]

@router.get("", response_model=RecipeSearchResponse, summary="Search recipes by ingredients")
def search_recipes(
    service: ServiceDep,
    ingredients: Annotated[
        list[str] | None,
        Query(description="Ingredients (EN or ID), Comma-separated."),
    ] = None, 
    q: Annotated[
        str| None, Query(min_length=1, description="Search by recipe name.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> RecipeSearchResponse:
    wanted = _parse_ingredients(ingredients)
    if bool(wanted) == bool(q):
        raise HTTPException(
            status_code=422,  detail="Provide either 'ingredients' or 'q' parameter, but not both.",
        )
    try:
        if wanted:
            results = service.search_by_ingredients(wanted, limit=limit)
        else:
            assert q is not None
            results = service.search_by_name(q, limit)
    except ScraperError as e:
        raise HTTPException(status_code=502, detail="Upstream recipe site is unavailable.") from e
    return RecipeSearchResponse(count=len(results), results=results)

@router.get("/{recipe_id}", response_model=RecipeDetail, summary="Get one recipe")
def get_recipe(
    recipe_id: Annotated[str, Path(pattern=r"^\d+$")],
    service: ServiceDep,
    lang: Literal["en", "id"] = "en",
) -> RecipeDetail:
    try:
        return service.get_detail(recipe_id, lang)
    except RecipeNotFound as exc:
        raise HTTPException(status_code=404, detail="Recipe not found.") from exc