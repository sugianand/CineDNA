from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
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
ACTION_COMEDY_TERMS = ("action comedy", "action comedies")
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

DECADE_SEGMENTS = {
    "early": (0, 3),
    "mid": (4, 6),
    "late": (7, 9),
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
    "humor": (
        "funny", "comedy", "humor", "hilarious", "fun",
    ) + ROM_COM_TERMS + ACTION_COMEDY_TERMS,
    "plot_twists": (
        "twist", "twists", "twisty", "unpredictable", "shocking", "surprising",
    ),
    "action": (
        "action", "fight", "fights", "fighting", "explosive", "combat",
    ) + ACTION_COMEDY_TERMS,
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
    "comedy", "documentary", "fantasy", "history", "horror", "music", "mystery",
    "romance", "thriller", "science fiction", "western",
}

THEME_ALIASES = {
    "action": ACTION_COMEDY_TERMS,
    "adventure": ("adventurous", "adventures"),
    "animation": ("animated", "cartoon", "cartoons"),
    "comedy": ROM_COM_TERMS + ACTION_COMEDY_TERMS + ("comedies",),
    "documentary": ("documentaries", "nonfiction", "non fiction"),
    "drama": ("dramatic", "dramas"),
    "family": (
        "family friendly", "kid friendly", "kids movie", "kids movies",
        "children's movie", "children's movies",
    ),
    "fantasy": ("magical", "magic", "fantasies"),
    "history": ("historical",),
    "horror": ("scary", "spooky", "frightening", "horrors"),
    "music": ("musical", "musicals"),
    "mystery": ("mysteries",),
    "romance": ROM_COM_TERMS + ("romances",),
    "science fiction": ("sci fi", "scifi", "space opera"),
    "thriller": SUSPENSE_TERMS + ("thrillers",),
    "western": ("westerns", "cowboy movie", "cowboy movies"),
}

COUNTRY_ALIASES = {
    "Australia": ("australia", "australian"),
    "Brazil": ("brazil", "brazilian"),
    "Canada": ("canada", "canadian"),
    "China": ("china", "chinese"),
    "France": ("france", "french"),
    "Germany": ("germany", "german"),
    "Hong Kong": ("hong kong",),
    "India": (
        "india", "indian", "bollywood", "hindi", "telugu", "tamil", "malayalam",
        "kannada", "bengali", "marathi", "punjabi", "gujarati",
    ),
    "Italy": ("italy", "italian"),
    "Japan": ("japan", "japanese", "anime"),
    "Mexico": ("mexico", "mexican"),
    "South Korea": ("south korea", "korean", "south korean"),
    "Spain": ("spain", "spanish"),
    "United Kingdom": (
        "united kingdom", "uk", "u.k.", "britain", "british",
    ),
    "USA": ("usa", "united states", "american", "hollywood", "us movie", "u.s."),
}

NEGATION_PREFIX = (
    r"(?:without|no|non|neither|avoid(?:ing)?|exclud(?:e|ing)|not|except|anything\s+but|"
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


def _term_spans(query: str, term: str) -> List[Tuple[int, int]]:
    normalized_term = _normalize_text(term)
    if not normalized_term:
        return []
    pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
    return [match.span() for match in re.finditer(pattern, query)]


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


def _find_title_matches(
    normalized_query: str,
    movies: List[MovieDNA],
) -> List[Tuple[MovieDNA, int, int, str]]:
    exact_matches = []
    for movie in movies:
        for candidate in (movie.title, movie.original_title or ""):
            normalized_title = _normalize_text(candidate)
            exact_matches.extend(
                (movie, start, end, len(normalized_title), normalized_title)
                for start, end in _term_spans(normalized_query, candidate)
            )

    title_matches = []
    for movie, start, end, length, normalized_title in exact_matches:
        is_part_of_longer_title = any(
            other_start <= start
            and end <= other_end
            and other_length > length
            for _other_movie, other_start, other_end, other_length, _term in exact_matches
        )
        if not is_part_of_longer_title:
            title_matches.append((movie, start, end, normalized_title))

    base_matches: Dict[str, List[MovieDNA]] = {}
    for movie in movies:
        base = _title_base(movie.title)
        if base != movie.title and len(_normalize_text(base)) >= 4:
            base_matches.setdefault(_normalize_text(base), []).append(movie)

    for base, candidates in base_matches.items():
        if len(candidates) != 1:
            continue
        for start, end in _term_spans(normalized_query, base):
            if any(
                exact_start <= start and end <= exact_end
                for _movie, exact_start, exact_end, _term in title_matches
            ):
                continue
            title_matches.append((candidates[0], start, end, base))

    return title_matches


def _find_excluded_movies(query: str, movies: List[MovieDNA]) -> List[MovieDNA]:
    normalized_query = _normalize_text(query)
    excluded = []
    seen = set()
    for movie, _start, _end, matched_title in sorted(
        _find_title_matches(normalized_query, movies),
        key=lambda match: match[1],
    ):
        identity = (movie.title.casefold(), movie.year)
        if _is_negated(normalized_query, matched_title) and identity not in seen:
            excluded.append(movie)
            seen.add(identity)
    return excluded


def _find_reference_movies(query: str, movies: List[MovieDNA]) -> List[MovieDNA]:
    normalized_query = _normalize_text(query)
    excluded_identities = {
        (movie.title.casefold(), movie.year)
        for movie in _find_excluded_movies(normalized_query, movies)
    }
    reference_matches = [
        match
        for match in _find_title_matches(normalized_query, movies)
        if (match[0].title.casefold(), match[0].year) not in excluded_identities
    ]

    if reference_matches:
        references = []
        seen = set()
        for movie, _start, _end, _term in sorted(reference_matches, key=lambda match: match[1]):
            identity = (movie.title.casefold(), movie.year)
            if identity not in seen:
                references.append(movie)
                seen.add(identity)
        return references

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


@lru_cache(maxsize=1)
def _preference_list_terms() -> Tuple[str, ...]:
    raw_terms = set(THEME_VOCAB) | set(THEME_ALIASES)
    raw_terms.update(
        term
        for aliases in THEME_ALIASES.values()
        for term in aliases
    )
    raw_terms.update(
        term
        for aliases in COUNTRY_ALIASES.values()
        for term in aliases
    )
    raw_terms.update(
        term
        for keywords in DIMENSION_RULES.values()
        for term in keywords
    )
    normalized_terms = {_normalize_text(term) for term in raw_terms}
    return tuple(sorted(
        (term for term in normalized_terms if term),
        key=lambda term: (len(term.split()), len(term)),
        reverse=True,
    ))


def _is_preference_list_prefix(prefix: str) -> bool:
    """Recognize earlier items in a punctuation-stripped preference list."""
    remaining = prefix.strip()
    if not remaining:
        return False

    filler = re.compile(
        r"^(?:a|an|any|and|or|nor|movie|movies|film|films|"
        r"title|titles|genre|genres)\b\s*"
    )
    while remaining:
        filler_match = filler.match(remaining)
        if filler_match:
            remaining = remaining[filler_match.end():].strip()
            continue

        matched = next(
            (
                term
                for term in _preference_list_terms()
                if remaining == term or remaining.startswith(f"{term} ")
            ),
            None,
        )
        if matched is None:
            return False
        remaining = remaining[len(matched):].strip()

    return True


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
                re.search(r"\b(?:and|or|nor)\s*$", prefix)
                or re.search(r"\b(?:and|or|nor)\b", suffix)
                or _is_preference_list_prefix(prefix)
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


def _expand_abbreviated_year(anchor_year: int, value: str) -> int:
    """Expand a two-digit range endpoint to the nearest supported full year."""
    if len(value) == 4:
        return int(value)

    suffix = int(value)
    century = (anchor_year // 100) * 100
    candidates = (
        century - 100 + suffix,
        century + suffix,
        century + 100 + suffix,
    )
    supported = (year for year in candidates if 1900 <= year <= 2099)
    return min(supported, key=lambda year: (abs(year - anchor_year), year))


def _decade_bounds(query: str, match: re.Match, start_year: int) -> Tuple[int, int]:
    segment_match = re.search(
        r"\b(?:the\s+)?(early|mid|late)\s*$",
        query[:match.start()],
    )
    if segment_match is None:
        return start_year, start_year + 9

    start_offset, end_offset = DECADE_SEGMENTS[segment_match.group(1)]
    return start_year + start_offset, start_year + end_offset


def _matching_years(query: str, patterns: Tuple[str, ...]) -> List[int]:
    return [
        int(match.group(1))
        for pattern in patterns
        for match in re.finditer(pattern, query)
    ]


def _extract_year_range(query: str) -> Tuple[int | None, int | None]:
    min_year = None
    max_year = None

    range_patterns = (
        r"\bbetween\s+((?:19|20)\d{2})\s+(?:and\s+|to\s+)?"
        r"((?:19|20)\d{2}|\d{2})\b",
        r"\b(?:(?:movies?|films?)\s+)?(?:released\s+)?from\s+"
        r"((?:19|20)\d{2})\s+(?:(?:to|through|until)\s+)?"
        r"((?:19|20)\d{2}|\d{2})\b",
        r"\b(?:movies?|films?)\s+(?:released\s+)?"
        r"((?:19|20)\d{2})\s+(?:(?:to|through|until)\s+)?"
        r"((?:19|20)\d{2}|\d{2})\b",
        r"\b(?:released\s+)?((?:19|20)\d{2})\s+(?:(?:to|through|until)\s+)?"
        r"((?:19|20)\d{2}|\d{2})\s+(?:movies?|films?)\b",
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
        second_year = _expand_abbreviated_year(first_year, range_match.group(2))
        min_year = min(first_year, second_year)
        max_year = max(first_year, second_year)

    inclusive_min_patterns = (
        r"\b(?:from\s+)?((?:19|20)\d{2})\s+"
        r"(?:(?:or|and)\s+)?(?:later|newer|onwards?)\b",
        r"\b(?:not\s+before|no\s+earlier\s+than|on\s+or\s+after|at\s+least|"
        r"(?:no|not)\s+older\s+than)\s+"
        r"((?:19|20)\d{2})\b",
    )
    inclusive_min_years = _matching_years(query, inclusive_min_patterns)
    if inclusive_min_years:
        min_year = max(min_year or 0, *inclusive_min_years)

    inclusive_max_patterns = (
        r"\b((?:19|20)\d{2})\s+(?:or|and)\s+(?:earlier|older)\b",
        r"\b(?:up\s+to|through)\s+((?:19|20)\d{2})\b",
        r"\b(?:not\s+after|no\s+later\s+than|on\s+or\s+before|at\s+most|"
        r"(?:no|not)\s+newer\s+than)\s+"
        r"((?:19|20)\d{2})\b",
    )
    inclusive_max_years = _matching_years(query, inclusive_max_patterns)
    if inclusive_max_years:
        strictest_max = min(inclusive_max_years)
        max_year = min(
            max_year if max_year is not None else strictest_max,
            strictest_max,
        )

    exact_patterns = (
        r"\b(?:movies?|films?)\s+(?:released\s+)?(?:from\s+|in\s+)?"
        r"((?:19|20)\d{2})\b",
        r"\breleased\s+(?:in\s+)?((?:19|20)\d{2})\b",
        r"\b((?:19|20)\d{2})\s+(?:movies?|films?)\b",
    )
    if min_year is None and max_year is None:
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

        # Apostrophes normalize to spaces, so accept both "1990s" and the
        # common (though nonstandard) spellings "1990's" and "1990’s".
        decade_match = re.search(r"\b((?:19|20)\d{2})\s*s\b", query)
        if decade_match:
            min_year, max_year = _decade_bounds(
                query,
                decade_match,
                int(decade_match.group(1)),
            )
        else:
            short_decade_match = re.search(
                r"(?<!\w)(?:the\s+)?([3-9]\d)\s*s\b",
                query,
            )
            if short_decade_match:
                min_year, max_year = _decade_bounds(
                    query,
                    short_decade_match,
                    1900 + int(short_decade_match.group(1)),
                )
            else:
                for word, start_year in DECADE_WORDS.items():
                    word_match = re.search(rf"\b{word}\b", query)
                    if word_match:
                        min_year, max_year = _decade_bounds(
                            query,
                            word_match,
                            start_year,
                        )
                        break

    after_pattern = (
        r"(?<!not )(?<!no )(?<!or )\b(?:after|newer\s+than)\s+"
        r"((?:19|20)\d{2})\b"
    )
    after_years = [
        int(match.group(1)) + 1
        for match in re.finditer(after_pattern, query)
    ]
    if after_years:
        min_year = max(min_year or 0, *after_years)

    since_years = _matching_years(
        query,
        (r"\bsince\s+((?:19|20)\d{2})\b",),
    )
    if since_years:
        min_year = max(min_year or 0, *since_years)

    before_pattern = (
        r"(?<!not )(?<!no )(?<!or )\b(?:before|older\s+than)\s+"
        r"((?:19|20)\d{2})\b"
    )
    before_years = [
        int(match.group(1)) - 1
        for match in re.finditer(before_pattern, query)
    ]
    if before_years:
        strictest_before = min(before_years)
        max_year = min(max_year or strictest_before, strictest_before)

    return min_year, max_year


def parse_search_intent(query: str, movies: List[MovieDNA]) -> SearchIntent:
    lowered = _normalize_text(query)
    excluded_movies = _find_excluded_movies(lowered, movies)
    references = _find_reference_movies(lowered, movies)
    trait_query = _without_reference_titles(lowered, references)

    if references:
        dimension_names = sorted({
            name
            for movie in references
            for name in movie.dimensions
        })
        target = {
            name: round(sum(values) / len(values))
            for name in dimension_names
            if (values := [
                movie.dimensions[name]
                for movie in references
                if name in movie.dimensions
            ])
        }
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
    excluded_titles = [movie.title for movie in excluded_movies]
    reference_label = (
        reference_titles[0]
        if len(reference_titles) == 1
        else f"{', '.join(reference_titles[:-1])} and {reference_titles[-1]}"
    ) if reference_titles else ""
    excluded_label = (
        excluded_titles[0]
        if len(excluded_titles) == 1
        else f"{', '.join(excluded_titles[:-1])} and {excluded_titles[-1]}"
    ) if excluded_titles else ""
    explanation = (
        f"Started from the Movie DNA of {reference_label} and adjusted it using your request."
        if reference_titles
        else f"Excluded {excluded_label} and converted the rest of your request into Movie DNA."
        if excluded_titles
        else "Converted your natural-language request into Movie DNA traits and themes."
    )

    return SearchIntent(
        target_dimensions=target,
        include_themes=sorted(set(include_themes)),
        exclude_themes=sorted(set(exclude_themes)),
        preferred_countries=preferred_countries,
        excluded_countries=excluded_countries,
        reference_titles=reference_titles,
        excluded_titles=excluded_titles,
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
