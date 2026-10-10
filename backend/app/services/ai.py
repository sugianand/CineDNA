from __future__ import annotations

import re
from typing import Dict, List, Tuple

from app.models import MovieDNA, SearchIntent


FAST_PACING_TERMS = ("fast", "fast paced", "fast-paced")
SLOW_PACING_TERMS = ("slow", "slow burn", "slow-burn")

DIMENSION_RULES: Dict[str, Tuple[str, ...]] = {
    "emotional_intensity": ("emotional", "moving", "heartfelt", "sad", "cry"),
    "narrative_complexity": (
        "complex", "complicated", "mind bending", "mind-bending", "cerebral", "confusing",
    ),
    "visual_spectacle": ("beautiful", "visual", "cinematic", "spectacle", "epic"),
    "pacing": FAST_PACING_TERMS + SLOW_PACING_TERMS,
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

NEGATED_THEME_ALIASES = {
    "mysterious": "mystery",
    "detective": "mystery",
    "whodunit": "mystery",
    "romantic": "romance",
    "love story": "romance",
    "funny": "comedy",
    "humor": "comedy",
    "hilarious": "comedy",
}

THEME_VOCAB = {
    "family", "time", "space", "survival", "identity", "memory", "guilt", "reality",
    "morality", "justice", "crime", "deception", "murder", "greed", "friendship",
    "education", "mythology", "power", "destiny", "religion", "war", "love",
    "trauma", "truth", "dreams", "language", "grief", "communication", "action",
    "comedy", "horror", "mystery", "romance", "thriller", "science fiction",
}

THEME_ALIASES = {
    "science fiction": ("sci fi", "scifi"),
}

COUNTRY_ALIASES = {
    "India": ("indian", "bollywood", "hindi"),
    "USA": ("american", "hollywood", "us movie", "u.s."),
}

NEGATION_PREFIX = (
    r"(?:without|no|avoid(?:ing)?|exclud(?:e|ing)|not|except|anything\s+but|"
    r"(?:do\s+not|don\s+t)\s+(?:want|like))"
)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _contains_term(query: str, term: str) -> bool:
    normalized_term = _normalize_text(term)
    return bool(normalized_term) and f" {normalized_term} " in f" {query} "


def _contains_title(query: str, title: str) -> bool:
    return _contains_term(query, title)


def _title_base(title: str) -> str:
    return re.split(r":|\s[-–—]\s", title, maxsplit=1)[0].strip()


def _find_reference_movies(query: str, movies: List[MovieDNA]) -> List[MovieDNA]:
    normalized_query = _normalize_text(query)
    exact_matches = [
        movie
        for movie in movies
        if any(
            _contains_title(normalized_query, candidate)
            for candidate in (movie.title, movie.original_title or "")
        )
    ]
    if exact_matches:
        return exact_matches

    base_matches: Dict[str, List[MovieDNA]] = {}
    for movie in movies:
        base = _title_base(movie.title)
        if base != movie.title and len(_normalize_text(base)) >= 4:
            base_matches.setdefault(_normalize_text(base), []).append(movie)

    return [
        candidates[0]
        for base, candidates in base_matches.items()
        if len(candidates) == 1 and _contains_title(normalized_query, base)
    ]


def _without_reference_titles(
    query: str,
    references: List[MovieDNA],
) -> str:
    trait_query = query
    for movie in references:
        candidates = {
            _normalize_text(candidate)
            for candidate in (
                movie.title,
                movie.original_title or "",
                _title_base(movie.title),
            )
            if candidate
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            pattern = rf"\b{re.escape(candidate)}\b"
            trait_query, replacements = re.subn(
                pattern,
                " ",
                trait_query,
                count=1,
            )
            if replacements:
                break

    return " ".join(trait_query.split())


def _apply_modifier(query: str, keyword: str, current: int) -> int:
    escaped = re.escape(_normalize_text(keyword))
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
    escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
    pattern = rf"\b{NEGATION_PREFIX}\s+(?:(?:a|an|any|too\s+much)\s+)?{escaped}\b"
    return bool(re.search(pattern, query))


def _is_reduced(query: str, term: str) -> bool:
    escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
    return bool(re.search(rf"\bless\s+{escaped}\b", query))


def parse_search_intent(query: str, movies: List[MovieDNA]) -> SearchIntent:
    lowered = _normalize_text(query)
    references = _find_reference_movies(lowered, movies)
    trait_query = _without_reference_titles(lowered, references)

    if references:
        target = dict(references[0].dimensions)
    else:
        target = {}

    include_themes: List[str] = []
    exclude_themes: List[str] = []
    preferred_countries: List[str] = []
    excluded_countries: List[str] = []

    for country, aliases in COUNTRY_ALIASES.items():
        matches = [alias for alias in aliases if _contains_term(trait_query, alias)]
        if any(_is_negated(trait_query, alias) for alias in matches):
            excluded_countries.append(country)
        elif matches:
            preferred_countries.append(country)

    for theme in THEME_VOCAB:
        matched = next(
            (
                term
                for term in (theme, *THEME_ALIASES.get(theme, ()))
                if _contains_term(trait_query, term)
            ),
            None,
        )
        if not matched:
            continue
        if _is_reduced(trait_query, matched):
            continue
        if _is_negated(trait_query, matched):
            exclude_themes.append(theme)
        else:
            include_themes.append(theme)

    for dimension, keywords in DIMENSION_RULES.items():
        matched = next(
            (
                keyword
                for keyword in keywords
                if _contains_term(trait_query, keyword)
            ),
            None,
        )
        if not matched:
            continue

        current = target.get(dimension, 75)
        negated = _is_negated(trait_query, matched)
        if dimension == "pacing":
            negated_pacing = next(
                (
                    keyword
                    for keyword in keywords
                    if _contains_term(trait_query, keyword)
                    and _is_negated(trait_query, keyword)
                ),
                None,
            )
            reduced_pacing = next(
                (
                    keyword
                    for keyword in keywords
                    if _contains_term(trait_query, keyword)
                    and _is_reduced(trait_query, keyword)
                ),
                None,
            )
            reversed_pacing = negated_pacing or reduced_pacing
            if reversed_pacing:
                current = 85 if reversed_pacing in SLOW_PACING_TERMS else 35
            else:
                current = 35 if matched in SLOW_PACING_TERMS else 85
        elif negated:
            current = 10
            if excluded_theme := NEGATED_THEME_ALIASES.get(matched):
                exclude_themes.append(excluded_theme)
        else:
            current = _apply_modifier(trait_query, matched, current)

        target[dimension] = current

    if "darker" in trait_query:
        target["darkness"] = min(100, target.get("darkness", 65) + 25)

    if "funnier" in trait_query or "more funny" in trait_query:
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
        excluded_countries=excluded_countries,
        reference_titles=reference_titles,
        explanation=explanation,
    )


def build_match_reason(movie: MovieDNA, intent: SearchIntent) -> str:
    reasons: List[str] = []

    movie_terms = [
        _normalize_text(item)
        for item in movie.themes + movie.genres
    ]
    matched_themes = [
        theme for theme in intent.include_themes
        if any(_contains_term(movie_term, theme) for movie_term in movie_terms)
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
