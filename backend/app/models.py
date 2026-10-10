from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class MovieDNA(BaseModel):
    title: str
    year: int
    country: str
    genres: List[str]
    themes: List[str]
    dimensions: Dict[str, int]
    summary: str
    source: str = "cinedna"
    source_id: Optional[str] = None
    original_title: Optional[str] = None
    poster_url: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=6, ge=1, le=20)
    mode: Literal["auto", "vibe", "title"] = "auto"

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value):
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @model_validator(mode="after")
    def validate_vibe_query(self):
        if self.mode == "vibe" and len(self.query) < 3:
            raise ValueError("vibe searches must contain at least 3 characters")
        return self


class SearchIntent(BaseModel):
    target_dimensions: Dict[str, int]
    include_themes: List[str] = []
    exclude_themes: List[str] = []
    explanation: str = ""
    preferred_countries: List[str] = []
    excluded_countries: List[str] = []
    reference_titles: List[str] = []


class SearchResult(BaseModel):
    movie: MovieDNA
    score: float
    why: str


class SearchResponse(BaseModel):
    query: str
    intent: SearchIntent
    results: List[SearchResult]
    ai_provider: str
