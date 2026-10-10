from __future__ import annotations

import re
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


def rank_movies(
    movies: Iterable[MovieDNA],
    intent: SearchIntent,
    limit: int = 6,
) -> List[Tuple[MovieDNA, float]]:
    reference_titles = {title.casefold() for title in intent.reference_titles}
    excluded_countries = {
        country.casefold() for country in intent.excluded_countries
    }
    ranked = [
        (movie, score_movie(movie, intent))
        for movie in movies
        if movie.title.casefold() not in reference_titles
        and movie.country.casefold() not in excluded_countries
        and not _matching_preferences(movie, intent.exclude_themes)
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]
