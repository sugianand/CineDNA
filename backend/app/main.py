from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data.movies import MOVIES
from app.models import SearchRequest, SearchResponse, SearchResult
from app.services.ai import build_match_reason, parse_search_intent
from app.services.scoring import rank_movies

app = FastAPI(title="CineDNA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "movies": len(MOVIES)}


@app.get("/movies")
def list_movies():
    return MOVIES


@app.post("/search", response_model=SearchResponse)
def search_movies(request: SearchRequest):
    intent = parse_search_intent(request.query, MOVIES)
    ranked = rank_movies(MOVIES, intent, request.limit)

    results = [
        SearchResult(
            movie=movie,
            score=score,
            why=build_match_reason(movie, intent),
        )
        for movie, score in ranked
    ]

    return SearchResponse(
        query=request.query,
        intent=intent,
        results=results,
        ai_provider="rule-based-v0.1",
    )
