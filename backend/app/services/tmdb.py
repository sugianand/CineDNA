from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Sequence

import httpx

from app.models import MovieDNA


TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

INDIAN_LANGUAGES = {"hi", "te", "ta", "ml", "kn", "bn", "mr", "pa", "gu"}

TITLE_BLOCKERS = {
    "like ", "dark", "funny", "comedy", "mystery", "romance", "romantic",
    "action", "emotional", "sad", "thriller", "horror", "sci-fi", "science fiction",
    "fast", "slow", "twist", "indian movie", "american movie", "something",
    "movie with", "film with", "less ", "more ",
}


def tmdb_is_configured() -> bool:
    return bool(os.getenv("TMDB_READ_TOKEN", "").strip())


def looks_like_title_query(query: str) -> bool:
    cleaned = " ".join(query.lower().split())
    if not cleaned or len(cleaned.split()) > 7:
        return False
    return not any(term in cleaned for term in TITLE_BLOCKERS)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE))


def _dimensions_for(genres: List[str], overview: str, rating: float) -> Dict[str, int]:
    dimensions = {
        "emotional_intensity": 50,
        "narrative_complexity": 50,
        "visual_spectacle": 50,
        "pacing": 50,
        "mystery": 35,
        "romance": 25,
        "darkness": 40,
        "humor": 25,
        "plot_twists": 35,
        "action": 30,
        "character_depth": 55,
        "world_building": 45,
        "dialogue_density": 50,
        "rewatchability": _clamp(int(35 + rating * 6)),
    }

    boosts = {
        "Action": {"action": 55, "pacing": 35, "visual_spectacle": 25},
        "Adventure": {"world_building": 35, "visual_spectacle": 30, "action": 20},
        "Animation": {"visual_spectacle": 30, "world_building": 20},
        "Comedy": {"humor": 60, "darkness": -15},
        "Crime": {"darkness": 25, "mystery": 20, "plot_twists": 15},
        "Drama": {"emotional_intensity": 35, "character_depth": 35},
        "Fantasy": {"world_building": 50, "visual_spectacle": 30},
        "History": {"narrative_complexity": 15, "dialogue_density": 10},
        "Horror": {"darkness": 55, "mystery": 25, "emotional_intensity": 20},
        "Mystery": {"mystery": 60, "plot_twists": 35, "narrative_complexity": 20},
        "Romance": {"romance": 60, "emotional_intensity": 25},
        "Science Fiction": {"world_building": 45, "narrative_complexity": 25, "visual_spectacle": 35},
        "Thriller": {"pacing": 30, "darkness": 30, "mystery": 25, "plot_twists": 25},
        "War": {"action": 35, "darkness": 25, "emotional_intensity": 20},
    }

    for genre in genres:
        for trait, delta in boosts.get(genre, {}).items():
            dimensions[trait] = _clamp(dimensions[trait] + delta)

    text_boosts = {
        "family": ("emotional_intensity", 12),
        "murder": ("darkness", 14),
        "secret": ("mystery", 12),
        "conspiracy": ("narrative_complexity", 12),
        "war": ("action", 10),
        "love": ("romance", 12),
        "revenge": ("darkness", 10),
        "survive": ("pacing", 10),
        "survival": ("pacing", 10),
    }
    for word, (trait, delta) in text_boosts.items():
        if _contains_term(overview, word):
            dimensions[trait] = _clamp(dimensions[trait] + delta)

    return dimensions


def _themes_for(overview: str, genres: List[str]) -> List[str]:
    vocabulary = (
        "family", "love", "revenge", "war", "crime", "murder", "identity",
        "friendship", "survival", "power", "justice", "greed", "destiny",
        "history", "memory", "truth",
    )
    themes = [theme for theme in vocabulary if _contains_term(overview, theme)]
    if len(themes) < 3:
        themes.extend(genre.lower() for genre in genres[:3])
    return list(dict.fromkeys(themes))[:6]


def _country_label(language: str) -> str:
    if language in INDIAN_LANGUAGES:
        return "India"
    return "International"


def _from_tmdb(item: dict) -> MovieDNA:
    genres = [GENRES[genre_id] for genre_id in item.get("genre_ids", []) if genre_id in GENRES]
    overview = (item.get("overview") or "").strip()
    release_date = item.get("release_date") or ""
    year = int(release_date[:4]) if re.match(r"^\d{4}", release_date) else 0
    rating = float(item.get("vote_average") or 0)

    poster_path = item.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

    return MovieDNA(
        title=item.get("title") or item.get("original_title") or "Untitled",
        original_title=item.get("original_title"),
        year=year,
        country=_country_label(item.get("original_language") or ""),
        genres=genres or ["Movie"],
        themes=_themes_for(overview, genres),
        dimensions=_dimensions_for(genres, overview, rating),
        summary=overview or "Movie metadata supplied by TMDB.",
        source="tmdb",
        source_id=str(item.get("id")) if item.get("id") is not None else None,
        poster_url=poster_url,
    )


def search_tmdb_movies(query: str, limit: int = 6) -> List[MovieDNA]:
    token = os.getenv("TMDB_READ_TOKEN", "").strip()
    if not token:
        return []

    try:
        response = httpx.get(
            f"{TMDB_API_URL}/search/movie",
            params={
                "query": query,
                "include_adult": "false",
                "language": "en-US",
                "page": 1,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=6.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []

    results = response.json().get("results", [])
    return [_from_tmdb(item) for item in results[:limit]]


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def search_local_movies(
    query: str,
    movies: Sequence[MovieDNA],
    limit: int = 6,
) -> List[MovieDNA]:
    """Return credible title matches from the bundled catalog.

    Substring matches support shortened titles such as "Dune", while the
    similarity threshold tolerates small spelling mistakes without turning a
    failed title lookup into unrelated vibe recommendations.
    """
    normalized_query = _normalize_title(query)
    if not normalized_query:
        return []

    matches = []
    for movie in movies:
        candidates = [movie.title, movie.original_title or ""]
        normalized_candidates = [
            _normalize_title(candidate) for candidate in candidates if candidate
        ]
        best_similarity = max(
            SequenceMatcher(None, normalized_query, candidate).ratio()
            for candidate in normalized_candidates
        )
        contains_title = any(
            normalized_query in candidate or candidate in normalized_query
            for candidate in normalized_candidates
        )
        if contains_title or best_similarity >= 0.72:
            matches.append((movie, title_match_score(query, movie)))

    matches.sort(key=lambda item: item[1], reverse=True)
    return [movie for movie, _score in matches[:limit]]


def title_match_score(query: str, movie: MovieDNA) -> float:
    normalized_query = _normalize_title(query)
    candidates = [movie.title, movie.original_title or ""]
    best = max(
        SequenceMatcher(
            None,
            normalized_query,
            _normalize_title(candidate),
        ).ratio()
        for candidate in candidates
        if candidate
    )
    return round(55 + best * 45, 1)
