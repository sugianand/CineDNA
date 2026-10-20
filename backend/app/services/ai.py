from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from app.models import MovieDNA, SearchIntent


FAST_PACING_TERMS = (
    "fast", "fast paced", "fast-paced", "faster",
    "high energy", "high-energy", "energetic", "quick paced", "quick-paced",
)
SLOW_PACING_TERMS = ("slow", "slow burn", "slow-burn", "slower", "deliberate", "deliberately paced")
LIGHT_TONE_TERMS = (
    "feel good", "feel-good", "lighthearted", "lighter", "lighter tone",
    "uplifting", "comforting", "easy watch",
)
ROM_COM_TERMS = ("rom com", "romantic comedy")
SUSPENSE_TERMS = (
    "suspense", "suspenseful", "tense", "thrilling", "edge of my seat", "edge-of-my-seat",
)
MILD_PREFIXES = ("a little", "a bit", "somewhat", "slightly", "kind of", "kinda")
POSITIVE_TRAIT_TARGET = 75
INTENSIFIED_TRAIT_TARGET = 85
REFERENCE_MODIFIER_TERMS = (
    "but", "with", "without", "except", "more", "less",
    "darker", "lighter", "funnier", "slower", "faster", "different",
)

DECADE_WORDS = {
    "thirties": 1930,
    "forties": 1940,
    "fifties": 1950,
    "sixties": 1960,
    "seventies": 1970,
    "eighties": 1980,
    "nineties": 1990,
}

DIMENSION_RULES: Dict[str, Tuple[str, ...]] = {
    "emotional_intensity": (
        "emotional", "moving", "heartfelt", "sad", "cry", "intense", "powerful",
        "tearjerker", "tear jerker",
    ),
    "narrative_complexity": (
        "complex", "complicated", "mind bending", "mind-bending", "cerebral", "confusing",
        "thought provoking", "thought-provoking", "intellectual", "smart",
    ),
    "visual_spectacle": (
        "beautiful", "visual", "cinematic", "spectacle", "epic", "visually stunning",
        "gorgeous", "big screen", "big-screen",
    ),
    "pacing": FAST_PACING_TERMS + SLOW_PACING_TERMS,
    "mystery": ("mystery", "mysterious", "detective", "whodunit", "suspenseful"),
    "romance": ("romance", "romantic", "love story") + ROM_COM_TERMS,
    "darkness": ("dark", "bleak", "grim", "scary", "disturbing") + LIGHT_TONE_TERMS,
    "humor": ("funny", "comedy", "humor", "hilarious", "fun") + ROM_COM_TERMS,
    "plot_twists": (
        "twist", "twists", "twisty", "unpredictable", "shocking", "surprising",
    ),
    "action": ("action", "fight", "fights", "fighting", "explosive", "combat"),
    "character_depth": (
        "character driven", "character-driven", "deep characters", "strong characters",
        "character focused", "character-focused",
    ),
    "world_building": (
        "world building", "world-building", "worldbuilding", "immersive world", "big world",
    ),
    "dialogue_density": (
        "dialogue", "talky", "conversation", "dialogue heavy", "dialogue-heavy",
    ),
    "rewatchability": (
        "rewatchable", "rewatch", "easy watch", "comfort movie", "comforting",
    ),
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
    "trauma", "truth", "dreams", "language", "grief", "communication", "action", "animation",
    "comedy", "fantasy", "horror", "mystery", "romance", "thriller", "science fiction",
}

THEME_ALIASES = {
    "adventure": ("adventurous", "adventures"),
    "animation": ("animated", "cartoon", "cartoons"),
    "comedy": ROM_COM_TERMS + ("comedies",),
    "drama": ("dramatic", "dramas"),
    "fantasy": ("magical", "magic", "fantasies"),
    "horror": ("scary", "spooky", "frightening", "horrors"),
    "mystery": ("mysteries",),
    "romance": ROM_COM_TERMS + ("romances",),
    "science fiction": ("sci fi", "scifi", "space opera"),
    "thriller": SUSPENSE_TERMS + ("thrillers",),
}

COUNTRY_ALIASES = {
    "Brazil": ("brazil", "brazilian"),
    "France": ("france", "french"),
    "India": (
        "india", "indian", "bollywood", "hindi", "telugu", "tamil", "malayalam",
        "kannada", "bengali", "marathi", "punjabi", "gujarati",
    ),
    "Japan": ("japan", "japanese", "anime"),
    "South Korea": ("south korea", "korean", "south korean"),
    "USA": ("usa", "united states", "american", "hollywood", "us movie", "u.s."),
}

NEGATION_PREFIX = (
    r"(?:without|no|non|avoid(?:ing)?|exclud(?:e|ing)|not|except|anything\s+but|"
    r"(?:do\s+not|don\s+t)\s+(?:want|like))"
)


def _normalize_text(value: str) -> str:
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


def _contains_term(query: str, term: str) -> bool:
    normalized_term = _normalize_text(term)
    return bool(normalized_term) and f" {normalized_term} " in f" {query} "


def _most_specific_term(query: str, terms: Tuple[str, ...]) -> str | None:
    normalized_query = f" {_normalize_text(query)} "
    matches = []
    for term in terms:
        normalized_term = _normalize_text(term)
        position = normalized_query.find(f" {normalized_term} ")
        if normalized_term and position >= 0:
            matches.append((position, -len(normalized_term), term))

    return min(matches)[2] if matches else None


def _contains_title(query: str, title: str) -> bool:
    return _contains_term(query, title)


def _title_base(title: str) -> str:
    return re.split(r":|\s[-–—]\s", title, maxsplit=1)[0].strip()


def _reference_hint(query: str) -> str:
    cue_patterns = (
        r"(?:^|\b(?:movie|movies|film|films|something|anything|one)\s+)like\s+",
        r"\bsimilar\s+to\s+",
        r"\bsame\s+(?:vibe|dna|feel)\s+as\s+",
    )
    for pattern in cue_patterns:
        match = re.search(pattern, query)
        if not match:
            continue
        hint = query[match.end():]
        hint = re.split(
            r"\s+(?:but|with|without|except|and|more|less)\b|[,;]",
            hint,
            maxsplit=1,
        )[0]
        return hint.strip()
    return ""


def _fuzzy_title_variants(movie: MovieDNA) -> set[str]:
    variants = {
        _normalize_text(candidate)
        for candidate in (
            movie.title,
            movie.original_title or "",
            _title_base(movie.title),
        )
        if candidate
    }
    variants.update(
        re.sub(r"^(?:a|an|the)\s+", "", variant)
        for variant in tuple(variants)
    )
    return {variant for variant in variants if len(variant) >= 4}


def _find_reference_movies(query: str, movies: List[MovieDNA]) -> List[MovieDNA]:
    normalized_query = _normalize_text(query)
    exact_matches = []
    for movie in movies:
        matched_title_lengths = [
            len(_normalize_text(candidate))
            for candidate in (movie.title, movie.original_title or "")
            if _contains_title(normalized_query, candidate)
        ]
        if matched_title_lengths:
            exact_matches.append((movie, max(matched_title_lengths)))

    if exact_matches:
        longest_match = max(length for _movie, length in exact_matches)
        return [
            movie
            for movie, length in exact_matches
            if length == longest_match
        ]

    base_matches: Dict[str, List[MovieDNA]] = {}
    for movie in movies:
        base = _title_base(movie.title)
        if base != movie.title and len(_normalize_text(base)) >= 4:
            base_matches.setdefault(_normalize_text(base), []).append(movie)

    unique_base_matches = [
        candidates[0]
        for base, candidates in base_matches.items()
        if len(candidates) == 1 and _contains_title(normalized_query, base)
    ]
    if unique_base_matches:
        return unique_base_matches

    hint = _reference_hint(normalized_query)
    if len(hint) < 4:
        return []

    fuzzy_matches = []
    for movie in movies:
        variants = _fuzzy_title_variants(movie)
        if variants:
            fuzzy_matches.append((
                max(
                    SequenceMatcher(None, hint, variant).ratio()
                    for variant in variants
                ),
                movie,
            ))
    fuzzy_matches.sort(key=lambda match: match[0])
    if not fuzzy_matches:
        return []

    best_score, best_movie = fuzzy_matches[-1]
    next_score = fuzzy_matches[-2][0] if len(fuzzy_matches) > 1 else 0.0
    if best_score < 0.8 or best_score - next_score < 0.05:
        return []
    return [best_movie]


def _without_reference_titles(
    query: str,
    references: List[MovieDNA],
) -> str:
    trait_query = query
    hint = _reference_hint(query)
    if references and hint:
        trait_query = trait_query.replace(hint, " ", 1)
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


def is_reference_recommendation(query: str, movies: List[MovieDNA]) -> bool:
    """Return whether an auto-mode query asks for a variation on a movie."""
    normalized_query = _normalize_text(query)
    references = _find_reference_movies(normalized_query, movies)
    if not references:
        return False
    if _reference_hint(normalized_query):
        return True

    trait_query = _without_reference_titles(normalized_query, references)
    return any(
        _contains_term(trait_query, term)
        for term in REFERENCE_MODIFIER_TERMS
    )


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
        return min(100, max(INTENSIFIED_TRAIT_TARGET, current + 20))
    return max(POSITIVE_TRAIT_TARGET, current)


def _soft_preference_target(query: str, term: str) -> int | None:
    escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
    if re.search(rf"\bnot\s+too(?:\s+much)?\s+{escaped}\b", query):
        return 40
    mild_prefix = "|".join(
        re.escape(prefix).replace(r"\ ", r"\s+")
        for prefix in MILD_PREFIXES
    )
    if re.search(rf"\b(?:{mild_prefix})\s+{escaped}\b", query):
        return 60
    return None


def _is_negated(query: str, term: str) -> bool:
    if _soft_preference_target(query, term) is not None:
        return False
    escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
    pattern = (
        rf"\b{NEGATION_PREFIX}\s+"
        rf"(?:(?:a|an|any|too\s+much|from)\s+)?{escaped}\b"
    )
    if re.search(pattern, query):
        return True

    # Carry a negation across short, coordinated lists such as
    # "no horror or thriller" without crossing a contrasting clause.
    for negation in re.finditer(rf"\b{NEGATION_PREFIX}\b", query):
        clause = re.split(
            r"\b(?:but|instead|although|though|yet|with)\b",
            query[negation.end():],
            maxsplit=1,
        )[0]
        term_match = re.search(rf"\b{escaped}\b", clause)
        if term_match is None:
            continue

        prefix = term_match.string[:term_match.start()].strip()
        prefix = re.sub(r"^(?:a|an|any|too\s+much)\s+", "", prefix)
        suffix = term_match.string[term_match.end():]
        if (
            len(prefix.split()) <= 8
            and (
                re.search(r"\b(?:and|or)\s*$", prefix)
                or re.search(r"\b(?:and|or)\b", suffix)
            )
        ):
            return True

    return False


def _is_reduced(query: str, term: str) -> bool:
    escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
    return bool(re.search(rf"\bless\s+{escaped}\b", query))


def _positive_dimension_term(query: str, terms: Tuple[str, ...]) -> str | None:
    """Prefer an explicit positive trait over a separate negated alias."""
    modified_spans = []
    for term in terms:
        if not (
            _is_negated(query, term)
            or _is_reduced(query, term)
            or _soft_preference_target(query, term) is not None
        ):
            continue
        escaped = re.escape(_normalize_text(term)).replace(r"\ ", r"\s+")
        modified_spans.extend(
            match.span()
            for match in re.finditer(rf"\b{escaped}\b", query)
        )

    matches = []
    for term in terms:
        if (
            _is_negated(query, term)
            or _is_reduced(query, term)
            or _soft_preference_target(query, term) is not None
        ):
            continue
        normalized_term = _normalize_text(term)
        escaped = re.escape(normalized_term).replace(r"\ ", r"\s+")
        for match in re.finditer(rf"\b{escaped}\b", query):
            start, end = match.span()
            if any(
                modified_start <= start and end <= modified_end
                for modified_start, modified_end in modified_spans
            ):
                continue
            matches.append((start, -len(normalized_term), term))
            break

    return min(matches)[2] if matches else None


def _extract_year_range(query: str) -> Tuple[int | None, int | None]:
    min_year = None
    max_year = None

    range_patterns = (
        r"\bbetween\s+((?:19|20)\d{2})\s+(?:and\s+|to\s+)?"
        r"((?:19|20)\d{2})\b",
        r"\b(?:(?:movies?|films?)\s+)?(?:released\s+)?from\s+"
        r"((?:19|20)\d{2})\s+(?:(?:to|through)\s+)?((?:19|20)\d{2})\b",
        r"\b(?:movies?|films?)\s+(?:released\s+)?"
        r"((?:19|20)\d{2})\s+(?:(?:to|through)\s+)?((?:19|20)\d{2})\b",
        r"\b(?:released\s+)?((?:19|20)\d{2})\s+(?:(?:to|through)\s+)?"
        r"((?:19|20)\d{2})\s+(?:movies?|films?)\b",
    )
    range_match = next(
        (
            match
            for pattern in range_patterns
            if (match := re.search(pattern, query)) is not None
        ),
        None,
    )
    if range_match:
        first_year = int(range_match.group(1))
        second_year = int(range_match.group(2))
        return min(first_year, second_year), max(first_year, second_year)

    inclusive_min_match = re.search(
        r"\b(?:from\s+)?((?:19|20)\d{2})\s+"
        r"(?:(?:or|and)\s+)?(?:later|newer|onwards?)\b",
        query,
    )
    if inclusive_min_match:
        return int(inclusive_min_match.group(1)), None

    inclusive_max_patterns = (
        r"\b((?:19|20)\d{2})\s+(?:or|and)\s+(?:earlier|older)\b",
        r"\b(?:up\s+to|through)\s+((?:19|20)\d{2})\b",
    )
    inclusive_max_match = next(
        (
            match
            for pattern in inclusive_max_patterns
            if (match := re.search(pattern, query)) is not None
        ),
        None,
    )
    if inclusive_max_match:
        return None, int(inclusive_max_match.group(1))

    exact_patterns = (
        r"\b(?:movies?|films?)\s+(?:released\s+)?(?:from\s+|in\s+)?"
        r"((?:19|20)\d{2})\b",
        r"\breleased\s+(?:in\s+)?((?:19|20)\d{2})\b",
        r"\b((?:19|20)\d{2})\s+(?:movies?|films?)\b",
    )
    exact_match = next(
        (
            match
            for pattern in exact_patterns
            if (match := re.search(pattern, query)) is not None
        ),
        None,
    )
    if exact_match:
        year = int(exact_match.group(1))
        return year, year

    # Apostrophes normalize to spaces, so accept both "1990s" and the common
    # (though nonstandard) spellings "1990's" and "1990’s".
    decade_match = re.search(r"\b((?:19|20)\d{2})\s*s\b", query)
    if decade_match:
        min_year = int(decade_match.group(1))
        max_year = min_year + 9
    else:
        short_decade_match = re.search(
            r"(?<!\w)(?:the\s+)?([3-9]\d)\s*s\b",
            query,
        )
        if short_decade_match:
            min_year = 1900 + int(short_decade_match.group(1))
            max_year = min_year + 9
        else:
            for word, start_year in DECADE_WORDS.items():
                if _contains_term(query, word):
                    min_year = start_year
                    max_year = start_year + 9
                    break

    after_match = re.search(r"\b(?:after|newer\s+than)\s+((?:19|20)\d{2})\b", query)
    if after_match:
        min_year = int(after_match.group(1)) + 1

    since_match = re.search(r"\bsince\s+((?:19|20)\d{2})\b", query)
    if since_match:
        min_year = int(since_match.group(1))

    before_match = re.search(r"\b(?:before|older\s+than)\s+((?:19|20)\d{2})\b", query)
    if before_match:
        max_year = int(before_match.group(1)) - 1

    return min_year, max_year


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
    min_year, max_year = _extract_year_range(trait_query)

    for country, aliases in COUNTRY_ALIASES.items():
        matches = [alias for alias in aliases if _contains_term(trait_query, alias)]
        if any(_is_negated(trait_query, alias) for alias in matches):
            excluded_countries.append(country)
        elif matches:
            preferred_countries.append(country)

    catalog_genres = {
        normalized
        for movie in movies
        for genre in movie.genres
        if (normalized := _normalize_text(genre)) and normalized != "movie"
    }
    for theme in THEME_VOCAB | catalog_genres:
        matched = _most_specific_term(
            trait_query,
            (theme, *THEME_ALIASES.get(theme, ())),
        )
        if not matched:
            continue
        if _is_reduced(trait_query, matched):
            continue
        if _soft_preference_target(trait_query, matched) is not None:
            continue
        if _is_negated(trait_query, matched):
            exclude_themes.append(theme)
        else:
            include_themes.append(theme)

    for dimension, keywords in DIMENSION_RULES.items():
        matched = _most_specific_term(trait_query, keywords)
        if not matched:
            continue

        if (
            _is_negated(trait_query, matched)
            or _is_reduced(trait_query, matched)
            or _soft_preference_target(trait_query, matched) is not None
        ):
            matched = _positive_dimension_term(trait_query, keywords) or matched

        current = target.get(dimension, 75)
        soft_target = _soft_preference_target(trait_query, matched)
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
            if soft_target is not None:
                current = 55 if matched in FAST_PACING_TERMS else 60
            elif reversed_pacing:
                current = 85 if reversed_pacing in SLOW_PACING_TERMS else 35
            else:
                current = 35 if matched in SLOW_PACING_TERMS else 85
        elif soft_target is not None:
            current = (
                100 - soft_target
                if dimension == "darkness" and matched in LIGHT_TONE_TERMS
                else soft_target
            )
        elif dimension == "darkness" and matched in LIGHT_TONE_TERMS:
            current = 80 if negated or _is_reduced(trait_query, matched) else 20
        elif negated:
            current = 10
            if excluded_theme := NEGATED_THEME_ALIASES.get(matched):
                exclude_themes.append(excluded_theme)
        else:
            current = _apply_modifier(trait_query, matched, current)

        target[dimension] = current

    if "darker" in trait_query:
        target["darkness"] = min(100, target.get("darkness", 65) + 25)

    if "funnier" in trait_query:
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
        min_year=min_year,
        max_year=max_year,
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

    if (
        intent.min_year is not None
        and intent.min_year == intent.max_year
    ):
        reasons.append(f"released in {intent.min_year}")
    elif intent.min_year is not None and intent.max_year is not None:
        reasons.append(f"released from {intent.min_year} to {intent.max_year}")
    elif intent.min_year is not None:
        reasons.append(f"released in {intent.min_year} or later")
    elif intent.max_year is not None:
        reasons.append(f"released in {intent.max_year} or earlier")

    return "; ".join(reasons) or "overall Movie DNA similarity"
