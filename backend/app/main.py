import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.data.movies import MOVIES
from app.models import SearchIntent, SearchRequest, SearchResponse, SearchResult
from app.services.ai import build_match_reason, parse_search_intent
from app.services.scoring import rank_movies
from app.services.tmdb import (
    looks_like_title_query,
    search_tmdb_movies,
    title_match_score,
    tmdb_is_configured,
)

app = FastAPI(title="CineDNA API", version="0.2.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
@app.get("/health")
def health():
    return {
        "status": "ok",
        "movies": len(MOVIES),
        "tmdb_enabled": tmdb_is_configured(),
    }


@app.get("/api/movies")
@app.get("/movies")
def list_movies():
    return MOVIES


@app.post("/api/search", response_model=SearchResponse)
@app.post("/search", response_model=SearchResponse)
def search_movies(request: SearchRequest):
    should_search_titles = request.mode == "title" or (
        request.mode == "auto" and looks_like_title_query(request.query)
    )
    if tmdb_is_configured() and should_search_titles:
        external_movies = search_tmdb_movies(request.query, request.limit)
        if external_movies:
            intent = SearchIntent(
                target_dimensions={},
                explanation="Matched your title against TMDB's movie catalog, including alternate and translated titles.",
            )
            results = [
                SearchResult(
                    movie=movie,
                    score=title_match_score(request.query, movie),
                    why="Title match from the TMDB catalog. Open the movie to inspect its generated CineDNA profile.",
                )
                for movie in external_movies
            ]
            results.sort(key=lambda item: item.score, reverse=True)
            return SearchResponse(
                query=request.query,
                intent=intent,
                results=results,
                ai_provider="tmdb-catalog+heuristic-dna",
            )

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


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"name": "CineDNA API", "status": "online", "docs": "/docs"}
