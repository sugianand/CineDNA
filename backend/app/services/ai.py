from __future__ import annotations

import re
from typing import Dict, List, Tuple

from app.models import MovieDNA, SearchIntent


DIMENSION_RULES: Dict[str, Tuple[str, ...]] = {
    "emotional_intensity": ("emotional", "moving", "heartfelt", "sad", "cry"),
    "narrative_complexity": ("complex", "mind bending", "mind-bending", "cerebral", "confusing"),
    "visual_spectacle": ("beautiful", "visual", "cinematic", "spectacle", "epic"),
    "pacing": ("fast", "fast paced", "fast-paced", "slow", "slow burn", "slow-burn"),
    "mystery": ("mystery", "mysterious", "detective", "whodunit"),
    "romance": ("romance", "romantic", "love story"),
    "darkness": ("dark", "bleak", "grim"),
    "humor": ("funny", "comedy", "humor", "hilarious"),
    "plot_twists": ("twist", "twisty", "unpredictable", "shocking"),
    "action": ("action", "fight", "explosive"),
    "character_depth": ("character driven", "character-driven", "deep characters"),
    "world_building": ("world building", "world-building", "immersive world"),
    "dialogue_density": ("dialogue", "talky", "conversation"),
    "rewatchability": ("rewatchable", "rewatch"),
}

THEME_VOCAB = {
    "family", "time", "space", "survival", "identity", "memory", "guilt", "reality",
    "morality", "justice", "crime", "deception", "murder", "greed", "friendship",
    "education", "mythology", "power", "destiny", "religion", "war", "love",
    "trauma", "truth", "dreams", "language", "grief", "communication", "action",
    "comedy", "horror", "mystery", "romance", "thriller", "science fiction",
}

NEGATION_PREFIX = r"(?:without|no|avoid(?:ing)?|exclud(?:e|ing)|not)"


def _find_reference_movies(query: str, movies: List[MovieDNA]) -> List[MovieDNA]:
    lowered = query.lower()
    return [movie for movie in movies if movie.title.lower() in lowered]


def _apply_modifier(query: str, keyword: str, current: int) -> int:
    escaped = re.escape(keyword)
    less_patterns = (
        rf"less\s+{escaped}",
        rf"not\s+(?:too\s+)?{escaped}",
        rf"without\s+(?:too\s+much\s+)?{escaped}",
    )
    more_patterns = (
        rf"more\s+{escaped}",
        rf"very\s+{escaped}",
        rf"really\s+{escaped}",
    )

    if any(re.search(pattern, query) for pattern in less_patterns):
        return max(5, current - 25)
    if any(re.search(pattern, query) for pattern in more_patterns):
        return min(100, current + 20)
    return current


def _is_negated(query: str, term: str) -> bool:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    pattern = rf"\b{NEGATION_PREFIX}\s+(?:(?:any|too\s+much)\s+)?{escaped}\b"
    return bool(re.search(pattern, query))


def parse_search_intent(query: str, movies: List[MovieDNA]) -> SearchIntent:
    lowered = " ".join(query.lower().split())
    references = _find_reference_movies(lowered, movies)

    if references:
        target = dict(references[0].dimensions)
    else:
        target = {}

    include_themes: List[str] = []
    exclude_themes: List[str] = []
    preferred_countries: List[str] = []

    if any(word in lowered for word in ("indian", "bollywood", "hindi")):
        preferred_countries.append("India")
    if any(word in lowered for word in ("american", "hollywood", "us movie", "u.s.")):
        preferred_countries.append("USA")

    for theme in THEME_VOCAB:
        if theme not in lowered:
            continue
        if _is_negated(lowered, theme):
            exclude_themes.append(theme)
        else:
            include_themes.append(theme)

    for dimension, keywords in DIMENSION_RULES.items():
        matched = next((keyword for keyword in keywords if keyword in lowered), None)
        if not matched:
            continue

        current = target.get(dimension, 75)
        if _is_negated(lowered, matched):
            current = 10
        else:
            current = _apply_modifier(lowered, matched, current)

        if dimension == "pacing":
            if any(term in lowered for term in ("slow", "slow burn", "slow-burn")):
                current = 35
            elif any(term in lowered for term in ("fast", "fast paced", "fast-paced")):
                current = 85

        target[dimension] = current

    if "less complicated" in lowered or "less confusing" in lowered:
        target["narrative_complexity"] = max(20, target.get("narrative_complexity", 70) - 30)

    if "darker" in lowered:
        target["darkness"] = min(100, target.get("darkness", 65) + 25)

    if "funnier" in lowered or "more funny" in lowered:
        target["humor"] = min(100, target.get("humor", 55) + 25)

    reference_titles = [movie.title for movie in references]
    explanation = (
        f"Started from the Movie DNA of {reference_titles[0]} and adjusted it using your request."
        if reference_titles
        else "Converted your natural-language request into Movie DNA traits and themes."
    )

    return SearchIntent(
        target_dimensions=target,
        include_themes=sorted(set(include_themes)),
        exclude_themes=sorted(set(exclude_themes)),
        preferred_countries=preferred_countries,
        reference_titles=reference_titles,
        explanation=explanation,
    )


def build_match_reason(movie: MovieDNA, intent: SearchIntent) -> str:
    reasons: List[str] = []

    matched_themes = [
        theme for theme in intent.include_themes
        if theme.lower() in {item.lower() for item in movie.themes + movie.genres}
    ]
    if matched_themes:
        reasons.append("matches " + ", ".join(matched_themes[:3]))

    if intent.target_dimensions:
        closest = sorted(
            intent.target_dimensions,
            key=lambda name: abs(
                movie.dimensions.get(name, 50) - intent.target_dimensions[name]
            ),
        )[:2]
        if closest:
            pretty = [name.replace("_", " ") for name in closest]
            reasons.append("strong fit for " + " and ".join(pretty))

    if intent.preferred_countries and movie.country in intent.preferred_countries:
        reasons.append(f"fits your {movie.country} preference")

    return "; ".join(reasons) or "overall Movie DNA similarity"
