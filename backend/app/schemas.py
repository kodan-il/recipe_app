from pydantic import BaseModel, Field

class RecipeSummary(BaseModel):
    id: str
    title: str
    image: str | None = None
    url: str = Field(description="Link to the original recipe page.")
    match_count: int = 0
    matched_ingredients: list[str] = Field(default_factory=list)

class RecipeSearchResponse(BaseModel):
    count: int
    results: list[RecipeSummary]
    
class RecipeDetail(BaseModel):
    id:str
    title:str
    image:str | None = None
    url:str
    ingredients: list[str]
    instructions: list[str]