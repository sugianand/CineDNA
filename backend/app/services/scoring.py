from __future__ import annotations

import re
import unicodedata
from math import sqrt
from typing import Dict, Iterable, List, Tuple

from app.models import MovieDNA, SearchIntent


DIMENSION_WEIGHTS = {
    "emotional_intensity": 1.15,
    "narrative_complexity": 1.05,
    "visual_spectacle": 0.95,
    "pacing": 1.0,
    "mystery": 1.1,
    "romance": 0.75,
    "darkness": 0.9,
    "humor": 0.85,
    "plot_twists": 1.1,
    "action": 0.9,
    "character_depth": 1.05,
    "world_building": 0.9,
    "dialogue_density": 0.7,
    "rewatchability": 0.7,
}


def _normalize_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


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


def _matching_preferences(movie: MovieDNA, preferences: Iterable[str]) -> set[str]:
    movie_terms = [_normalize_term(term) for term in movie.themes + movie.genres]
    matches = set()
    for preference in preferences:
        normalized = _normalize_term(preference)
        if normalized and any(
            f" {normalized} " in f" {movie_term} " for movie_term in movie_terms
        ):
            matches.add(normalized)
    return matches


def _dimension_similarity(movie: MovieDNA, target: Dict[str, int]) -> float:
    if not target:
        return 0.5

    weighted_error = 0.0
    total_weight = 0.0

    for name, desired in target.items():
        if name not in movie.dimensions:
            continue

        weight = DIMENSION_WEIGHTS.get(name, 1.0)
        actual = movie.dimensions[name]
        weighted_error += weight * ((actual - desired) / 100.0) ** 2
        total_weight += weight

    if total_weight == 0:
        return 0.5

    rmse = sqrt(weighted_error / total_weight)
    return max(0.0, 1.0 - rmse)


def _theme_similarity(movie: MovieDNA, intent: SearchIntent) -> float:
    include = {_normalize_term(term) for term in intent.include_themes}
    exclude = {_normalize_term(term) for term in intent.exclude_themes}

    if not include and not exclude:
        return 0.5

    excluded = len(_matching_preferences(movie, exclude))
    exclusion_score = 1.0 - (excluded / max(1, len(exclude))) if exclude else 1.0

    if not include:
        return max(0.0, min(1.0, exclusion_score))

    included = len(_matching_preferences(movie, include))
    include_score = included / len(include)

    return max(0.0, min(1.0, include_score * 0.8 + exclusion_score * 0.2))


def _country_bonus(movie: MovieDNA, intent: SearchIntent) -> float:
    if not intent.preferred_countries:
        return 0.0

    preferred = {country.lower() for country in intent.preferred_countries}
    return 0.08 if movie.country.lower() in preferred else -0.05


def score_movie(movie: MovieDNA, intent: SearchIntent) -> float:
    dimension_score = _dimension_similarity(movie, intent.target_dimensions)
    theme_score = _theme_similarity(movie, intent)

    score = dimension_score * 0.72 + theme_score * 0.28
    score += _country_bonus(movie, intent)

    return round(max(0.0, min(1.0, score)) * 100, 1)


def _matches_year_range(movie: MovieDNA, intent: SearchIntent) -> bool:
    if intent.min_year is None and intent.max_year is None:
        return True
    if movie.year <= 0:
        return False
    if intent.min_year is not None and movie.year < intent.min_year:
        return False
    if intent.max_year is not None and movie.year > intent.max_year:
        return False
    return True


def rank_movies(
    movies: Iterable[MovieDNA],
    intent: SearchIntent,
    limit: int = 6,
) -> List[Tuple[MovieDNA, float]]:
    catalog_movies = list(movies)
    reference_titles = {
        normalized
        for title in intent.reference_titles
        if (normalized := _normalize_title(title))
    }
    excluded_countries = {
        country.casefold() for country in intent.excluded_countries
    }
    eligible_movies = [
        movie
        for movie in catalog_movies
        if not any(
            _normalize_title(candidate) in reference_titles
            for candidate in (movie.title, movie.original_title or "")
            if candidate
        )
        and movie.country.casefold() not in excluded_countries
        and not _matching_preferences(movie, intent.exclude_themes)
        and _matches_year_range(movie, intent)
    ]

    preferred_countries = {
        country.casefold() for country in intent.preferred_countries
    }
    preferred_movies = [
        movie
        for movie in eligible_movies
        if movie.country.casefold() in preferred_countries
    ]
    has_preferred_country_coverage = any(
        movie.country.casefold() in preferred_countries
        for movie in catalog_movies
    )
    if has_preferred_country_coverage:
        eligible_movies = preferred_movies

    ranked = [
        (movie, score_movie(movie, intent))
        for movie in eligible_movies
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]
