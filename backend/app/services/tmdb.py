from __future__ import annotations

import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Sequence

import httpx

from app.models import MovieDNA, SearchIntent


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

GENRE_IDS = {name.casefold(): genre_id for genre_id, name in GENRES.items()}
ORIGIN_COUNTRY_CODES = {
    "Australia": "AU",
    "Brazil": "BR",
    "Canada": "CA",
    "China": "CN",
    "France": "FR",
    "Germany": "DE",
    "Hong Kong": "HK",
    "India": "IN",
    "Italy": "IT",
    "Japan": "JP",
    "Mexico": "MX",
    "South Korea": "KR",
    "Spain": "ES",
    "United Kingdom": "GB",
    "USA": "US",
}

INDIAN_LANGUAGES = {"hi", "te", "ta", "ml", "kn", "bn", "mr", "pa", "gu"}

COUNTRY_NAMES = {
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "CN": "China",
    "DE": "Germany",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "HK": "Hong Kong",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "MX": "Mexico",
    "US": "USA",
}

TITLE_BLOCKERS = {
    "like ", "dark", "funny", "comedy", "mystery", "romance", "romantic",
    "action", "emotional", "sad", "thriller", "horror", "sci-fi", "science fiction",
    "scary", "spooky", "frightening", "fast", "slow", "twist",
    "indian movie", "american movie", "something",
    "movie with", "film with", "less ", "more ",
}
TITLE_QUERY_STRUCTURE = {
    "like ", "movie with", "film with", "less ", "more ",
}
TITLE_CONNECTORS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from",
    "in", "nor", "of", "on", "or", "the", "to", "with", "yet",
}


def tmdb_is_configured() -> bool:
    return bool(os.getenv("TMDB_READ_TOKEN", "").strip())


def _looks_title_cased(query: str) -> bool:
    words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    cased_words = [word for word in words if any(char.isalpha() for char in word)]
    if not cased_words:
        return False

    return all(
        word.casefold() in TITLE_CONNECTORS or word[:1].isupper()
        for word in cased_words
    )


def looks_like_title_query(
    query: str,
    has_vibe_preferences: bool = False,
) -> bool:
    cleaned = " ".join(query.casefold().split())
    if not cleaned or len(cleaned.split()) > 7:
        return False
    if any(term in cleaned for term in TITLE_QUERY_STRUCTURE):
        return False
    if _looks_title_cased(query):
        return True
    if has_vibe_preferences:
        return False
    return not any(
        _contains_term(cleaned, term.strip())
        for term in TITLE_BLOCKERS
    )


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


def _country_label(
    origin_countries: object,
    language: str,
    country_hint: str | None = None,
) -> str:
    if isinstance(origin_countries, list):
        for country_code in origin_countries:
            if isinstance(country_code, str):
                country = COUNTRY_NAMES.get(country_code.upper())
                if country:
                    return country
    if country_hint:
        return country_hint
    if language in INDIAN_LANGUAGES:
        return "India"
    if language == "ja":
        return "Japan"
    if language == "ko":
        return "South Korea"
    return "International"


def _origin_country_codes(item: dict) -> List[str]:
    """Collect country codes from TMDB list and detail response shapes."""
    codes = []
    origin_countries = item.get("origin_country")
    if isinstance(origin_countries, list):
        codes.extend(
            code for code in origin_countries
            if isinstance(code, str)
        )

    production_countries = item.get("production_countries")
    if isinstance(production_countries, list):
        codes.extend(
            country["iso_3166_1"]
            for country in production_countries
            if isinstance(country, dict)
            and isinstance(country.get("iso_3166_1"), str)
        )

    return list(dict.fromkeys(codes))


def _clean_title(value: object) -> str | None:
    """Return a display-safe title or None for blank/non-string values."""
    if not isinstance(value, str):
        return None
    title = value.strip()
    return title or None


def _from_tmdb(item: dict, country_hint: str | None = None) -> MovieDNA:
    genres = [GENRES[genre_id] for genre_id in item.get("genre_ids", []) if genre_id in GENRES]
    overview = _clean_title(item.get("overview")) or ""
    release_date = item.get("release_date") or ""
    year = int(release_date[:4]) if re.match(r"^\d{4}", release_date) else 0
    rating = float(item.get("vote_average") or 0)

    poster_path = item.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

    original_title = _clean_title(item.get("original_title"))

    return MovieDNA(
        title=_clean_title(item.get("title")) or original_title or "Untitled",
        original_title=original_title,
        year=year,
        country=_country_label(
            _origin_country_codes(item),
            item.get("original_language") or "",
            country_hint,
        ),
        genres=genres or ["Movie"],
        themes=_themes_for(overview, genres),
        dimensions=_dimensions_for(genres, overview, rating),
        summary=overview or "Movie metadata supplied by TMDB.",
        source="tmdb",
        source_id=str(item.get("id")) if item.get("id") is not None else None,
        poster_url=poster_url,
    )


def _is_usable_catalog_item(item: dict) -> bool:
    """Return whether a TMDB result can support a stable profile link."""
    movie_id = item.get("id")
    title = _clean_title(item.get("title")) or _clean_title(item.get("original_title"))
    return (
        isinstance(movie_id, int)
        and not isinstance(movie_id, bool)
        and movie_id > 0
        and item.get("adult") is not True
        and title is not None
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
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    if not isinstance(payload, dict):
        return []

    results = payload.get("results", [])
    if not isinstance(results, list):
        return []

    movies = []
    for item in results:
        if len(movies) >= limit:
            break
        if not isinstance(item, dict) or not _is_usable_catalog_item(item):
            continue
        try:
            movie = _from_tmdb(item)
        except (TypeError, ValueError):
            continue
        # TMDB can return loose keyword matches. Do not let an unrelated item
        # consume the bounded result limit or suppress a later credible title
        # match. This also checks original titles through search_local_movies.
        if not search_local_movies(query, [movie], limit=1):
            continue
        movies.append(movie)
    return movies



def get_tmdb_movie(movie_id: str) -> MovieDNA | None:
    """Load an exact TMDB movie for a shareable details link."""
    token = os.getenv("TMDB_READ_TOKEN", "").strip()
    if not token or not movie_id.isdecimal() or len(movie_id) > 12:
        return None
    requested_id = int(movie_id)
    if requested_id <= 0:
        return None
    try:
        response = httpx.get(
            f"{TMDB_API_URL}/movie/{movie_id}",
            params={"language": "en-US"},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=6.0,
        )
        response.raise_for_status()
        item = response.json()
        if (
            not isinstance(item, dict)
            or not _is_usable_catalog_item(item)
            or item["id"] != requested_id
        ):
            return None
        genre_ids = [
            genre["id"] for genre in item.get("genres", [])
            if isinstance(genre, dict) and isinstance(genre.get("id"), int)
        ]
        return _from_tmdb({**item, "genre_ids": genre_ids})
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def _normalize_title(value: str) -> str:
    output = []
    last_base_is_latin = False
    for char in unicodedata.normalize("NFKD", value.casefold()):
        category = unicodedata.category(char)
        if category.startswith("M"):
            if not last_base_is_latin:
                output.append(char)
        elif category.startswith(("L", "N")):
            output.append(char)
            last_base_is_latin = "LATIN" in unicodedata.name(char, "")
        else:
            output.append(" ")
            last_base_is_latin = False

    return " ".join("".join(output).split())


def _normalized_title_variants(value: str) -> List[str]:
    variants = [_normalize_title(value)]
    if ":" in value:
        variants.append(_normalize_title(value.split(":", 1)[0]))
    return list(dict.fromkeys(variant for variant in variants if variant))


def has_exact_local_title(query: str, movies: Sequence[MovieDNA]) -> bool:
    normalized_query = _normalize_title(query)
    if not normalized_query:
        return False

    return any(
        normalized_query in _normalized_title_variants(candidate)
        for movie in movies
        for candidate in (movie.title, movie.original_title or "")
        if candidate
    )


def search_local_movies(
    query: str,
    movies: Sequence[MovieDNA],
    limit: int = 6,
) -> List[MovieDNA]:
    """Return credible title matches from the bundled catalog.

    Phrase matches support shortened titles such as "Dune", while the
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
            variant
            for candidate in candidates
            if candidate
            for variant in _normalized_title_variants(candidate)
        ]
        best_similarity = max(
            SequenceMatcher(None, normalized_query, candidate).ratio()
            for candidate in normalized_candidates
        )
        contains_title = any(
            f" {normalized_query} " in f" {candidate} "
            or f" {candidate} " in f" {normalized_query} "
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
            variant,
        ).ratio()
        for candidate in candidates
        if candidate
        for variant in _normalized_title_variants(candidate)
    )
    return round(55 + best * 45, 1)


def discover_tmdb_movies(intent: SearchIntent, limit: int = 20) -> List[MovieDNA]:
    """Expand vibe searches using one bounded page of TMDB movie discovery.

    Filters narrow the external candidate set; CineDNA still ranks and
    enforces all final constraints across the combined candidate catalog.
    Failures never prevent recommendations from the curated offline catalog.
    """
    token = os.getenv("TMDB_READ_TOKEN", "").strip()
    if not token:
        return []

    params = {
        "language": "en-US",
        "include_adult": "false",
        "include_video": "false",
        "sort_by": "popularity.desc",
        "page": 1,
    }
    genres = [
        GENRE_IDS[theme.casefold()]
        for theme in intent.include_themes
        if theme.casefold() in GENRE_IDS
    ]
    excluded_genres = [
        GENRE_IDS[theme.casefold()]
        for theme in intent.exclude_themes
        if theme.casefold() in GENRE_IDS
    ]
    if genres:
        params["with_genres"] = "|".join(map(str, dict.fromkeys(genres)))
    if excluded_genres:
        # TMDB treats commas as AND and pipes as OR. Exclude movies matching
        # any unwanted genre so the bounded discovery page is not filled with
        # candidates CineDNA will discard during final ranking.
        params["without_genres"] = "|".join(map(str, dict.fromkeys(excluded_genres)))
    country_filters = list(dict.fromkeys(
        (country, ORIGIN_COUNTRY_CODES[country])
        for country in intent.preferred_countries
        if country in ORIGIN_COUNTRY_CODES
    ))
    if country_filters:
        # A pipe asks TMDB for movies from any requested origin country while
        # keeping multi-country discovery to the same single bounded page.
        params["with_origin_country"] = "|".join(
            country_code for _country, country_code in country_filters
        )
    if intent.min_year is not None:
        params["primary_release_date.gte"] = f"{intent.min_year:04d}-01-01"
    if intent.max_year is not None:
        params["primary_release_date.lte"] = f"{intent.max_year:04d}-12-31"

    try:
        response = httpx.get(
            f"{TMDB_API_URL}/discover/movie",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=4.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return []

    movies = []
    country_hint = country_filters[0][0] if len(country_filters) == 1 else None
    for item in payload["results"]:
        if len(movies) >= limit:
            break
        if not isinstance(item, dict) or not _is_usable_catalog_item(item):
            continue
        try:
            # TMDB applies with_origin_country to discovery but list results do
            # not consistently include origin_country. A single requested
            # country is therefore a safe fallback for the generated profile.
            movie = _from_tmdb(item, country_hint=country_hint)
        except (TypeError, ValueError):
            continue
        if movie.year > 0 and movie.title != "Untitled":
            movies.append(movie)
    return movies
