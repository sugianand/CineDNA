import unittest

from app.data.movies import MOVIES
from app.models import MovieDNA, SearchIntent
from app.services.ai import build_match_reason, parse_search_intent
from app.services.scoring import rank_movies, score_movie


class SearchIntentTests(unittest.TestCase):
    def test_compound_genre_matches_requested_theme(self):
        psychological_thriller = MovieDNA(
            title="Mind Game",
            year=2026,
            country="USA",
            genres=["Psychological Thriller"],
            themes=[],
            dimensions={},
            summary="A test psychological thriller.",
        )
        drama = MovieDNA(
            title="Quiet Day",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={},
            summary="A test drama.",
        )
        intent = SearchIntent(target_dimensions={}, include_themes=["thriller"])

        self.assertGreater(
            score_movie(psychological_thriller, intent),
            score_movie(drama, intent),
        )
        self.assertIn(
            "matches thriller",
            build_match_reason(psychological_thriller, intent),
        )

    def test_excluded_compound_genre_is_removed_from_ranking(self):
        intent = parse_search_intent("A dark mystery with no thriller", MOVIES)

        ranked = rank_movies(MOVIES, intent, limit=20)
        ranked_titles = {movie.title for movie, _score in ranked}

        self.assertNotIn("Shutter Island", ranked_titles)
        self.assertNotIn("Drishyam", ranked_titles)
        self.assertTrue(
            all(
                "thriller" not in " ".join(movie.genres).lower()
                for movie, _score in ranked
            )
        )

    def test_reference_movie_is_excluded_from_recommendations(self):
        intent = parse_search_intent("Like 3 Idiots", MOVIES)

        ranked = rank_movies(MOVIES, intent, limit=6)
        ranked_titles = [movie.title for movie, _score in ranked]

        self.assertEqual(intent.reference_titles, ["3 Idiots"])
        self.assertNotIn("3 Idiots", ranked_titles)
        self.assertEqual(len(ranked), 6)

    def test_reference_movie_exclusion_normalizes_titles(self):
        reference_movie = MovieDNA(
            title="Amelie!",
            original_title="Le Fabuleux Destin d'Amélie",
            year=2001,
            country="France",
            genres=["Romance"],
            themes=["love"],
            dimensions={"romance": 85},
            summary="The selected reference movie.",
        )
        alternative = MovieDNA(
            title="Before Sunrise",
            year=1995,
            country="USA",
            genres=["Romance"],
            themes=["love"],
            dimensions={"romance": 82},
            summary="A different romantic movie.",
        )

        for reference_title in ("Amélie", "Le Fabuleux Destin d’Amélie"):
            with self.subTest(reference_title=reference_title):
                intent = SearchIntent(
                    target_dimensions={"romance": 85},
                    reference_titles=[reference_title],
                )
                ranked = rank_movies([reference_movie, alternative], intent)

                self.assertEqual(
                    [movie.title for movie, _score in ranked],
                    ["Before Sunrise"],
                )

    def test_keywords_do_not_match_inside_unrelated_words(self):
        intent = parse_search_intent(
            "A breakfast story set in Indiana about satisfaction",
            MOVIES,
        )

        self.assertNotIn("pacing", intent.target_dimensions)
        self.assertNotIn("action", intent.target_dimensions)
        self.assertNotIn("action", intent.include_themes)
        self.assertEqual(intent.preferred_countries, [])

    def test_hyphenated_phrases_still_match(self):
        intent = parse_search_intent(
            "A fast-paced Indian science-fiction action movie",
            MOVIES,
        )

        self.assertEqual(intent.target_dimensions["pacing"], 85)
        self.assertEqual(intent.target_dimensions["action"], 75)
        self.assertIn("science fiction", intent.include_themes)
        self.assertIn("India", intent.preferred_countries)
        self.assertEqual(intent.excluded_countries, [])

    def test_negated_country_preferences_are_excluded(self):
        cases = (
            ("No Indian movies", "India"),
            ("Anything but Hollywood", "USA"),
            ("No Korean movies", "South Korea"),
            ("No anime", "Japan"),
        )

        for query, excluded_country in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertIn(excluded_country, intent.excluded_countries)
                self.assertNotIn(excluded_country, intent.preferred_countries)
                self.assertTrue(ranked)
                self.assertTrue(
                    all(
                        movie.country != excluded_country
                        for movie, _score in ranked
                    )
                )

    def test_non_prefix_excludes_country_and_theme_preferences(self):
        intent = parse_search_intent("a non-Indian, non-horror movie", MOVIES)

        ranked = rank_movies(MOVIES, intent, limit=20)

        self.assertEqual(intent.preferred_countries, [])
        self.assertEqual(intent.excluded_countries, ["India"])
        self.assertIn("horror", intent.exclude_themes)
        self.assertNotIn("horror", intent.include_themes)
        self.assertTrue(ranked)
        self.assertTrue(
            all(
                movie.country != "India" and "Horror" not in movie.genres
                for movie, _score in ranked
            )
        )

    def test_korean_preference_ranks_south_korean_movies_first(self):
        intent = parse_search_intent("a Korean thriller", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=3)

        self.assertEqual(intent.preferred_countries, ["South Korea"])
        self.assertIn("thriller", intent.include_themes)
        self.assertEqual(ranked[0][0].title, "Parasite")
        self.assertEqual(ranked[0][0].country, "South Korea")

    def test_japanese_aliases_rank_japanese_movies_first(self):
        for query in ("a Japanese movie", "anime"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=3)

                self.assertEqual(intent.preferred_countries, ["Japan"])
                self.assertEqual(ranked[0][0].title, "Spirited Away")
                self.assertEqual(ranked[0][0].country, "Japan")

    def test_expanded_country_aliases_use_new_offline_coverage(self):
        cases = (
            ("a French romantic comedy", "France", "Amélie"),
            ("a Brazilian crime drama", "Brazil", "City of God"),
        )

        for query, country, expected_title in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=6)

                self.assertEqual(intent.preferred_countries, [country])
                self.assertTrue(ranked)
                self.assertEqual(ranked[0][0].title, expected_title)
                self.assertTrue(
                    all(movie.country == country for movie, _score in ranked)
                )

    def test_tmdb_country_aliases_become_search_preferences(self):
        cases = (
            ("Australian thrillers", "Australia"),
            ("Canadian mysteries", "Canada"),
            ("Chinese action movies", "China"),
            ("German dramas", "Germany"),
            ("Hong Kong cinema", "Hong Kong"),
            ("Italian comedies", "Italy"),
            ("Mexican films", "Mexico"),
            ("Spanish movies", "Spain"),
            ("British crime movies", "United Kingdom"),
        )

        for query, country in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.preferred_countries, [country])

        excluded = parse_search_intent("no Canadian or Mexican movies", MOVIES)
        self.assertEqual(excluded.preferred_countries, [])
        self.assertEqual(excluded.excluded_countries, ["Canada", "Mexico"])

    def test_canonical_country_names_filter_results(self):
        for country in ("Brazil", "France", "India", "Japan", "South Korea", "USA"):
            with self.subTest(country=country):
                intent = parse_search_intent(f"movies from {country}", MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertEqual(intent.preferred_countries, [country])
                self.assertTrue(ranked)
                self.assertTrue(
                    all(movie.country == country for movie, _score in ranked)
                )

    def test_not_from_country_excludes_that_country(self):
        intent = parse_search_intent("movies not from India", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=20)

        self.assertEqual(intent.preferred_countries, [])
        self.assertEqual(intent.excluded_countries, ["India"])
        self.assertTrue(ranked)
        self.assertTrue(
            all(movie.country != "India" for movie, _score in ranked)
        )

    def test_regional_indian_languages_are_recognized(self):
        for query in (
            "a Telugu action movie",
            "a Tamil thriller",
            "a Malayalam drama",
            "a Kannada adventure",
            "a Bengali mystery",
            "a Marathi comedy",
            "a Punjabi movie",
            "a Gujarati film",
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.preferred_countries, ["India"])

    def test_preferred_country_limits_results_when_catalog_has_matches(self):
        intent = parse_search_intent("a Bengali mystery", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=20)

        self.assertTrue(ranked)
        self.assertTrue(
            all(movie.country == "India" for movie, _score in ranked)
        )

    def test_preferred_country_falls_back_when_catalog_has_no_matches(self):
        intent = SearchIntent(
            target_dimensions={},
            preferred_countries=["Canada"],
        )

        ranked = rank_movies(MOVIES, intent, limit=3)

        self.assertEqual(len(ranked), 3)

    def test_supported_country_does_not_fall_back_after_other_filters(self):
        intent = parse_search_intent("Indian movies from the 1990s", MOVIES)

        ranked = rank_movies(MOVIES, intent, limit=6)

        self.assertEqual(ranked, [])

    def test_sci_fi_aliases_map_to_science_fiction(self):
        for query in ("A fast sci-fi movie", "A sci fi epic", "Something scifi"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=3)

                self.assertIn("science fiction", intent.include_themes)
                self.assertTrue(
                    all("Science Fiction" in movie.genres for movie, _score in ranked)
                )

    def test_fantasy_queries_rank_and_exclude_fantasy_movies(self):
        intent = parse_search_intent("a fantasy movie", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=2)

        self.assertIn("fantasy", intent.include_themes)
        self.assertTrue(
            all("Fantasy" in movie.genres for movie, _score in ranked)
        )

        excluded = parse_search_intent("anything but fantasy", MOVIES)
        excluded_ranked = rank_movies(MOVIES, excluded, limit=20)

        self.assertIn("fantasy", excluded.exclude_themes)
        self.assertTrue(
            all("Fantasy" not in movie.genres for movie, _score in excluded_ranked)
        )

    def test_animation_aliases_rank_and_exclude_animated_movies(self):
        for query in ("an animated movie", "a cartoon", "cartoons"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=1)

                self.assertIn("animation", intent.include_themes)
                self.assertEqual(ranked[0][0].title, "Spirited Away")

        excluded = parse_search_intent("anything but animated", MOVIES)
        excluded_ranked = rank_movies(MOVIES, excluded, limit=20)

        self.assertIn("animation", excluded.exclude_themes)
        self.assertTrue(
            all("Animation" not in movie.genres for movie, _score in excluded_ranked)
        )

    def test_catalog_genres_automatically_become_search_preferences(self):
        for genre in ("Adventure", "Crime", "Drama"):
            with self.subTest(genre=genre):
                intent = parse_search_intent(f"a {genre.lower()} movie", MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=1)

                self.assertIn(genre.lower(), intent.include_themes)
                self.assertIn(genre, ranked[0][0].genres)

        excluded = parse_search_intent("anything but adventure", MOVIES)
        excluded_ranked = rank_movies(MOVIES, excluded, limit=20)

        self.assertIn("adventure", excluded.exclude_themes)
        self.assertTrue(
            all("Adventure" not in movie.genres for movie, _score in excluded_ranked)
        )

    def test_tmdb_only_genre_aliases_become_search_preferences(self):
        cases = (
            ("a nature documentary", "documentary"),
            ("nonfiction movies", "documentary"),
            ("a historical film", "history"),
            ("a musical", "music"),
            ("cowboy movies", "western"),
        )

        for query, genre in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertIn(genre, intent.include_themes)

        excluded = parse_search_intent("no documentaries or westerns", MOVIES)
        self.assertEqual(excluded.include_themes, [])
        self.assertEqual(excluded.exclude_themes, ["documentary", "western"])

    def test_family_audience_aliases_become_search_preferences(self):
        for query in ("kids movies", "kid-friendly films", "children's movies"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.include_themes, ["family"])

        excluded = parse_search_intent("no kids movies", MOVIES)
        self.assertEqual(excluded.include_themes, [])
        self.assertEqual(excluded.exclude_themes, ["family"])

    def test_release_periods_filter_ranked_movies(self):
        cases = (
            ("movies from the 1970s", 1970, 1979),
            ("movies from the 1960's", 1960, 1969),
            ("movies from the 1990s", 1990, 1999),
            ("movies from the 2000’s", 2000, 2009),
            ("movies from the 2010s", 2010, 2019),
            ("movies released in 2015", 2015, 2015),
            ("movies from 2015", 2015, 2015),
            ("films from 2015", 2015, 2015),
            ("film in 2015", 2015, 2015),
            ("movies 2015", 2015, 2015),
            ("2015 films", 2015, 2015),
            ("movies released 2015", 2015, 2015),
            ("released 2015 movies", 2015, 2015),
            ("movies between 2014 and 2018", 2014, 2018),
            ("movies between 2018 and 2014", 2014, 2018),
            ("movies from 2014 to 2018", 2014, 2018),
            ("movies from 2014 through 2018", 2014, 2018),
            ("movies from 2014 until 2018", 2014, 2018),
            ("films released 2014 until 2018", 2014, 2018),
            ("released 2018 until 2014 films", 2014, 2018),
            ("films released from 2018 to 2014", 2014, 2018),
            ("movies from 2014-2018", 2014, 2018),
            ("films from 2018–2014", 2014, 2018),
            ("movies between 2014—2018", 2014, 2018),
            ("movies from 2014-18", 2014, 2018),
            ("films released 2018-14", 2014, 2018),
            ("movies between 1998 and 02", 1998, 2002),
            ("movies 2014-2018", 2014, 2018),
            ("films released 2014 to 2018", 2014, 2018),
            ("2018–2014 movies", 2014, 2018),
            ("released 2014-2018 films", 2014, 2018),
            ("movies after 2018", 2019, None),
            ("movies since 2019", 2019, None),
            ("movies before 2010", None, 2009),
            ("movies from 2015 onwards", 2015, None),
            ("movies from 2015 or later", 2015, None),
            ("2015 and newer films", 2015, None),
            ("movies not before 2015", 2015, None),
            ("movies no earlier than 2015", 2015, None),
            ("movies released on or after 2015", 2015, None),
            ("movies at least 2015", 2015, None),
            ("movies no older than 2015", 2015, None),
            ("movies not older than 2015", 2015, None),
            ("movies up to 2015", None, 2015),
            ("movies through 2015", None, 2015),
            ("2015 or earlier movies", None, 2015),
            ("movies not after 2015", None, 2015),
            ("movies no later than 2015", None, 2015),
            ("movies released on or before 2015", None, 2015),
            ("movies at most 2015", None, 2015),
            ("movies no newer than 2015", None, 2015),
            ("movies not newer than 2015", None, 2015),
        )

        for query, min_year, max_year in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)
                self.assertTrue(ranked)
                self.assertTrue(
                    all(
                        (min_year is None or movie.year >= min_year)
                        and (max_year is None or movie.year <= max_year)
                        for movie, _score in ranked
                    )
                )

    def test_compound_year_boundaries_preserve_both_limits(self):
        cases = (
            ("movies from 2010 or later but before 2019", 2010, 2018),
            ("movies after 2010 but 2019 or earlier", 2011, 2019),
            ("movies on or after 2010 and on or before 2018", 2010, 2018),
        )

        for query, min_year, max_year in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)
                self.assertTrue(ranked)
                self.assertTrue(all(
                    min_year <= movie.year <= max_year
                    for movie, _score in ranked
                ))

    def test_explicit_year_ranges_honor_additional_boundaries(self):
        cases = (
            ("movies between 2000 and 2020 but after 2010", 2011, 2020),
            ("movies from 2000 to 2020 but before 2015", 2000, 2014),
            ("movies between 2000 and 2020 but no later than 2015", 2000, 2015),
            (
                "movies from 2000 to 2020, on or after 2010 and on or before 2018",
                2010,
                2018,
            ),
        )

        for query, min_year, max_year in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)

    def test_repeated_year_boundaries_use_the_strictest_limit(self):
        cases = (
            ("movies after 2000 but after 2010", 2011, None),
            ("movies since 2000 but since 2010", 2010, None),
            ("movies from 2000 or later but 2010 or later", 2010, None),
            ("movies before 2020 but before 2015", None, 2014),
            ("movies up to 2020 but up to 2015", None, 2015),
        )

        for query, min_year, max_year in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)

    def test_year_in_title_is_not_treated_as_release_filter(self):
        intent = parse_search_intent("Blade Runner 2049", MOVIES)

        self.assertIsNone(intent.min_year)
        self.assertIsNone(intent.max_year)

    def test_abbreviated_decades_are_normalized(self):
        for query, min_year, max_year in (
            ("movies from the 90s", 1990, 1999),
            ("movies from the '90s", 1990, 1999),
            ("movies from the 90's", 1990, 1999),
            ("nineties movies", 1990, 1999),
            ("eighties movies", 1980, 1989),
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)

    def test_decade_segments_are_normalized(self):
        for query, min_year, max_year in (
            ("movies from the early 2000s", 2000, 2003),
            ("movies from the mid-2010s", 2014, 2016),
            ("movies from the late 2010's", 2017, 2019),
            ("films from the early '90s", 1990, 1993),
            ("late nineties movies", 1997, 1999),
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.min_year, min_year)
                self.assertEqual(intent.max_year, max_year)

    def test_exact_release_year_has_natural_match_reason(self):
        intent = parse_search_intent("movies released in 2015", MOVIES)

        reason = build_match_reason(MOVIES[0], intent)

        self.assertIn("released in 2015", reason)
        self.assertNotIn("from 2015 to 2015", reason)

    def test_negated_sci_fi_alias_excludes_science_fiction(self):
        intent = parse_search_intent("A fast movie with no sci-fi", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=20)

        self.assertIn("science fiction", intent.exclude_themes)
        self.assertTrue(
            all("Science Fiction" not in movie.genres for movie, _score in ranked)
        )

    def test_horror_aliases_drive_horror_ranking_and_exclusion(self):
        horror_movie = MovieDNA(
            title="Haunted House",
            year=2026,
            country="USA",
            genres=["Horror"],
            themes=[],
            dimensions={},
            summary="A scary test movie.",
        )
        drama_movie = MovieDNA(
            title="Quiet House",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={},
            summary="A calm test movie.",
        )

        for alias in ("scary", "spooky", "frightening"):
            with self.subTest(alias=alias):
                intent = parse_search_intent(f"a {alias} movie", MOVIES)
                ranked = rank_movies([drama_movie, horror_movie], intent, limit=2)

                self.assertIn("horror", intent.include_themes)
                self.assertEqual(ranked[0][0].title, "Haunted House")

        excluded_intent = parse_search_intent("anything but scary", MOVIES)
        excluded_ranked = rank_movies(
            [horror_movie, drama_movie],
            excluded_intent,
            limit=2,
        )

        self.assertIn("horror", excluded_intent.exclude_themes)
        self.assertEqual([movie.title for movie, _score in excluded_ranked], ["Quiet House"])

    def test_rom_com_aliases_combine_romance_and_comedy(self):
        romantic_comedy = MovieDNA(
            title="Date Night",
            year=2026,
            country="USA",
            genres=["Romance", "Comedy"],
            themes=[],
            dimensions={"romance": 80, "humor": 80},
            summary="A test romantic comedy.",
        )
        serious_romance = MovieDNA(
            title="Long Goodbye",
            year=2026,
            country="USA",
            genres=["Romance", "Drama"],
            themes=[],
            dimensions={"romance": 80, "humor": 10},
            summary="A serious test romance.",
        )

        for query in ("a rom-com", "a romantic comedy"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(
                    [serious_romance, romantic_comedy],
                    intent,
                    limit=2,
                )

                self.assertEqual(intent.include_themes, ["comedy", "romance"])
                self.assertEqual(intent.target_dimensions["romance"], 75)
                self.assertEqual(intent.target_dimensions["humor"], 75)
                self.assertEqual(ranked[0][0].title, "Date Night")

        for query in (
            "anything but a rom-com",
            "not a romantic comedy",
            "no romantic comedy",
            "without romantic comedy",
        ):
            with self.subTest(query=query):
                excluded = parse_search_intent(query, MOVIES)

                self.assertEqual(excluded.include_themes, [])
                self.assertEqual(excluded.exclude_themes, ["comedy", "romance"])
                self.assertEqual(excluded.target_dimensions["romance"], 10)
                self.assertEqual(excluded.target_dimensions["humor"], 10)

    def test_action_comedy_aliases_combine_action_and_comedy(self):
        for query in ("an action comedy", "action comedies"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.include_themes, ["action", "comedy"])
                self.assertEqual(intent.exclude_themes, [])
                self.assertEqual(intent.target_dimensions["action"], 75)
                self.assertEqual(intent.target_dimensions["humor"], 75)

        for query in (
            "not an action comedy",
            "no action comedy",
            "without action comedies",
        ):
            with self.subTest(query=query):
                excluded = parse_search_intent(query, MOVIES)

                self.assertEqual(excluded.include_themes, [])
                self.assertEqual(excluded.exclude_themes, ["action", "comedy"])
                self.assertEqual(excluded.target_dimensions["action"], 10)
                self.assertEqual(excluded.target_dimensions["humor"], 10)

    def test_pacing_terms_set_the_requested_speed(self):
        slow_movie = MovieDNA(
            title="Quiet Journey",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"pacing": 35},
            summary="A deliberately paced test movie.",
        )
        fast_movie = MovieDNA(
            title="Quick Escape",
            year=2026,
            country="USA",
            genres=["Action"],
            themes=[],
            dimensions={"pacing": 85},
            summary="A fast-paced test movie.",
        )

        for query, target, expected_title in (
            ("something faster", 85, "Quick Escape"),
            ("something slower", 35, "Quiet Journey"),
            ("not fast", 35, "Quiet Journey"),
            ("without fast pacing", 35, "Quiet Journey"),
            ("not slow", 85, "Quick Escape"),
            ("without slow pacing", 85, "Quick Escape"),
            ("less fast-paced", 35, "Quiet Journey"),
            ("less slow", 85, "Quick Escape"),
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies([slow_movie, fast_movie], intent, limit=2)

                self.assertEqual(intent.target_dimensions["pacing"], target)
                self.assertEqual(ranked[0][0].title, expected_title)

    def test_positive_mood_terms_request_a_light_tone(self):
        light_movie = MovieDNA(
            title="Bright Day",
            year=2026,
            country="USA",
            genres=["Comedy"],
            themes=[],
            dimensions={"darkness": 15},
            summary="A light test movie.",
        )
        dark_movie = MovieDNA(
            title="Bleak Night",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"darkness": 90},
            summary="A dark test movie.",
        )

        for query in (
            "a feel-good movie",
            "something lighthearted",
            "something lighter",
            "an uplifting film",
            "Like The Dark Knight but lighter",
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies([dark_movie, light_movie], intent, limit=2)

                self.assertEqual(intent.target_dimensions["darkness"], 20)
                self.assertEqual(ranked[0][0].title, "Bright Day")

    def test_soft_light_tone_modifiers_invert_darkness(self):
        for query, target in (
            ("something kind of lighthearted", 40),
            ("a little lighter", 40),
            ("not too lighthearted", 60),
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)

                self.assertEqual(intent.target_dimensions["darkness"], target)
                self.assertNotIn("horror", intent.exclude_themes)

    def test_reduced_light_tone_terms_request_a_darker_movie(self):
        light_movie = MovieDNA(
            title="Bright Day",
            year=2026,
            country="USA",
            genres=["Comedy"],
            themes=[],
            dimensions={"darkness": 15},
            summary="A light test movie.",
        )
        dark_movie = MovieDNA(
            title="Bleak Night",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"darkness": 90},
            summary="A dark test movie.",
        )

        for query in ("less lighthearted", "less uplifting"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies([light_movie, dark_movie], intent, limit=2)

                self.assertEqual(intent.target_dimensions["darkness"], 80)
                self.assertEqual(ranked[0][0].title, "Bleak Night")

    def test_reference_movie_matches_unique_title_before_subtitle(self):
        intent = parse_search_intent(
            "Something like Dune but funnier",
            MOVIES,
        )

        dune = next(movie for movie in MOVIES if movie.title == "Dune: Part Two")
        self.assertEqual(intent.reference_titles, ["Dune: Part Two"])
        self.assertEqual(intent.target_dimensions["visual_spectacle"], dune.dimensions["visual_spectacle"])
        self.assertGreater(intent.target_dimensions["humor"], dune.dimensions["humor"])

    def test_reference_movie_prefers_longest_overlapping_title(self):
        overlapping_movies = [
            MovieDNA(
                title="Up",
                year=2009,
                country="USA",
                genres=["Animation"],
                themes=[],
                dimensions={"emotional_intensity": 20},
                summary="A short-title test movie.",
            ),
            MovieDNA(
                title="Up in the Air",
                year=2009,
                country="USA",
                genres=["Drama"],
                themes=[],
                dimensions={"emotional_intensity": 80},
                summary="A longer-title test movie.",
            ),
        ]

        intent = parse_search_intent("Like Up in the Air", overlapping_movies)

        self.assertEqual(intent.reference_titles, ["Up in the Air"])
        self.assertEqual(intent.target_dimensions["emotional_intensity"], 80)

    def test_reference_query_blends_distinct_movie_dna_profiles(self):
        intent = parse_search_intent(
            "Like Interstellar and Arrival",
            MOVIES,
        )
        references = [
            next(movie for movie in MOVIES if movie.title == title)
            for title in ("Interstellar", "Arrival")
        ]

        self.assertEqual(intent.reference_titles, ["Interstellar", "Arrival"])
        self.assertEqual(
            intent.target_dimensions["narrative_complexity"],
            round(sum(movie.dimensions["narrative_complexity"] for movie in references) / 2),
        )
        self.assertIn("Interstellar and Arrival", intent.explanation)

    def test_negated_movie_title_is_excluded_instead_of_used_as_a_reference(self):
        for query in ("Not Titanic", "Avoid Titanic", "Anything but Titanic"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertEqual(intent.reference_titles, [])
                self.assertEqual(intent.excluded_titles, ["Titanic"])
                self.assertNotIn(
                    "Titanic",
                    [movie.title for movie, _score in ranked],
                )
                self.assertIn("Excluded Titanic", intent.explanation)

        reference_intent = parse_search_intent("Like Titanic", MOVIES)
        self.assertEqual(reference_intent.reference_titles, ["Titanic"])
        self.assertEqual(reference_intent.excluded_titles, [])

    def test_reference_movie_matching_normalizes_unicode(self):
        movies = [
            MovieDNA(
                title="Amélie",
                year=2001,
                country="France",
                genres=["Romance"],
                themes=[],
                dimensions={"romance": 85},
                summary="An accented-title test movie.",
            ),
            MovieDNA(
                title="Amaran",
                original_title="அமரன்",
                year=2024,
                country="India",
                genres=["Drama"],
                themes=[],
                dimensions={"emotional_intensity": 90},
                summary="A non-Latin-title test movie.",
            ),
        ]

        for query, expected_title in (
            ("Like Amelie", "Amélie"),
            ("Like அமரன்", "Amaran"),
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, movies)

                self.assertEqual(intent.reference_titles, [expected_title])

    def test_reference_movie_matching_tolerates_confident_typos(self):
        intent = parse_search_intent(
            "Movies like Intersteller but funnier",
            MOVIES,
        )

        interstellar = next(movie for movie in MOVIES if movie.title == "Interstellar")
        self.assertEqual(intent.reference_titles, ["Interstellar"])
        self.assertEqual(
            intent.target_dimensions["visual_spectacle"],
            interstellar.dimensions["visual_spectacle"],
        )
        self.assertGreater(
            intent.target_dimensions["humor"],
            interstellar.dimensions["humor"],
        )

        article_intent = parse_search_intent(
            "Something like Dark Knigt but lighter",
            MOVIES,
        )
        self.assertEqual(article_intent.reference_titles, ["The Dark Knight"])
        self.assertEqual(article_intent.target_dimensions["darkness"], 20)

    def test_fuzzy_reference_matching_requires_an_explicit_cue(self):
        intent = parse_search_intent(
            "An intersteller journey through grief",
            MOVIES,
        )

        self.assertEqual(intent.reference_titles, [])

    def test_reference_title_traits_do_not_override_movie_dna(self):
        reference = MovieDNA(
            title="Slow Burn",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"pacing": 80},
            summary="A fast-moving test reference movie.",
        )

        matching_intent = parse_search_intent("Like Slow Burn", [reference])
        adjusted_intent = parse_search_intent(
            "Like Slow Burn but slow",
            [reference],
        )

        self.assertEqual(matching_intent.reference_titles, ["Slow Burn"])
        self.assertEqual(matching_intent.target_dimensions["pacing"], 80)
        self.assertEqual(adjusted_intent.target_dimensions["pacing"], 35)

    def test_ambiguous_franchise_base_is_not_silently_selected(self):
        franchise_movies = [
            MovieDNA(
                title="Example: Part One",
                year=2025,
                country="USA",
                genres=["Drama"],
                themes=[],
                dimensions={"darkness": 20},
                summary="First test movie.",
            ),
            MovieDNA(
                title="Example: Part Two",
                year=2026,
                country="USA",
                genres=["Drama"],
                themes=[],
                dimensions={"darkness": 80},
                summary="Second test movie.",
            ),
        ]

        intent = parse_search_intent("Something like Example", franchise_movies)

        self.assertEqual(intent.reference_titles, [])

    def test_negated_preferences_are_excluded(self):
        intent = parse_search_intent(
            "A mystery without romance and no horror",
            MOVIES,
        )

        self.assertIn("mystery", intent.include_themes)
        self.assertIn("romance", intent.exclude_themes)
        self.assertIn("horror", intent.exclude_themes)
        self.assertNotIn("romance", intent.include_themes)
        self.assertEqual(intent.target_dimensions["romance"], 10)

    def test_natural_negation_phrases_are_excluded(self):
        cases = (
            ("I don't want a horror movie", "horror"),
            ("Anything but comedy", "comedy"),
            ("I do not like romance", "romance"),
        )

        for query, excluded_theme in cases:
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=20)

                self.assertIn(excluded_theme, intent.exclude_themes)
                self.assertNotIn(excluded_theme, intent.include_themes)
                self.assertTrue(
                    all(
                        excluded_theme not in " ".join(movie.genres + movie.themes).lower()
                        for movie, _score in ranked
                    )
                )

    def test_less_modifier_does_not_add_positive_genre_preference(self):
        action_movie = MovieDNA(
            title="Loud Escape",
            year=2026,
            country="USA",
            genres=["Action"],
            themes=[],
            dimensions={"action": 90},
            summary="A test action movie.",
        )
        quieter_movie = MovieDNA(
            title="Quiet Escape",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"action": 50},
            summary="A test drama.",
        )

        less_intent = parse_search_intent("Something with less action", MOVIES)
        more_intent = parse_search_intent("Something with more action", MOVIES)

        self.assertEqual(less_intent.target_dimensions["action"], 50)
        self.assertNotIn("action", less_intent.include_themes)
        self.assertEqual(
            rank_movies([action_movie, quieter_movie], less_intent, limit=2)[0][0].title,
            "Quiet Escape",
        )
        self.assertIn("action", more_intent.include_themes)
        self.assertEqual(
            rank_movies([action_movie, quieter_movie], more_intent, limit=2)[0][0].title,
            "Loud Escape",
        )

    def test_positive_trait_adjusts_reference_movie_dna(self):
        reference = MovieDNA(
            title="Reference Story",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"humor": 20},
            summary="A serious test reference movie.",
        )
        funny_movie = MovieDNA(
            title="Funny Story",
            year=2026,
            country="USA",
            genres=["Comedy"],
            themes=[],
            dimensions={"humor": 75},
            summary="A funny test movie.",
        )
        serious_movie = MovieDNA(
            title="Serious Story",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"humor": 20},
            summary="A serious test movie.",
        )

        funny_intent = parse_search_intent(
            "Like Reference Story but funny",
            [reference, funny_movie, serious_movie],
        )
        funnier_intent = parse_search_intent(
            "Like Reference Story but more funny",
            [reference, funny_movie, serious_movie],
        )
        ranked = rank_movies(
            [funny_movie, serious_movie],
            funny_intent,
            limit=2,
        )

        self.assertEqual(funny_intent.target_dimensions["humor"], 75)
        self.assertEqual(funnier_intent.target_dimensions["humor"], 85)
        self.assertEqual(ranked[0][0].title, "Funny Story")

    def test_complexity_synonyms_apply_one_consistent_reduction(self):
        reference = MovieDNA(
            title="Reference Story",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"narrative_complexity": 80},
            summary="A test reference movie.",
        )
        simpler_movie = MovieDNA(
            title="Simple Story",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"narrative_complexity": 55},
            summary="A straightforward test movie.",
        )
        complex_movie = MovieDNA(
            title="Complex Story",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"narrative_complexity": 80},
            summary="A complex test movie.",
        )

        for phrase in ("less complicated", "less confusing"):
            with self.subTest(phrase=phrase):
                intent = parse_search_intent(
                    f"Like Reference Story but {phrase}",
                    [reference, simpler_movie, complex_movie],
                )
                ranked = rank_movies([simpler_movie, complex_movie], intent, limit=2)

                self.assertEqual(intent.target_dimensions["narrative_complexity"], 55)
                self.assertEqual(ranked[0][0].title, "Simple Story")

    def test_negated_trait_aliases_exclude_matching_genres(self):
        intent = parse_search_intent(
            "Something mysterious but not romantic and not funny",
            MOVIES,
        )
        romantic_comedy = MovieDNA(
            title="Date Night",
            year=2026,
            country="USA",
            genres=["Romantic Comedy"],
            themes=[],
            dimensions={"mystery": 70, "romance": 80, "humor": 80},
            summary="A test romantic comedy.",
        )
        mystery_drama = MovieDNA(
            title="Hidden Clue",
            year=2026,
            country="USA",
            genres=["Mystery", "Drama"],
            themes=[],
            dimensions={"mystery": 70, "romance": 10, "humor": 10},
            summary="A test mystery drama.",
        )

        ranked = rank_movies([romantic_comedy, mystery_drama], intent, limit=2)

        self.assertEqual(intent.exclude_themes, ["comedy", "romance"])
        self.assertEqual(intent.target_dimensions["romance"], 10)
        self.assertEqual(intent.target_dimensions["humor"], 10)
        self.assertEqual([movie.title for movie, _score in ranked], ["Hidden Clue"])

    def test_positive_trait_survives_negated_alias_in_either_order(self):
        dark_drama = MovieDNA(
            title="Shadow Drama",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"darkness": 80},
            summary="A dark test drama.",
        )
        light_drama = MovieDNA(
            title="Sunny Drama",
            year=2026,
            country="USA",
            genres=["Drama"],
            themes=[],
            dimensions={"darkness": 15},
            summary="A light test drama.",
        )
        for query in ("dark but not scary", "not scary but dark"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies([light_drama, dark_drama], intent, limit=2)

                self.assertEqual(intent.target_dimensions["darkness"], 75)
                self.assertEqual(intent.exclude_themes, ["horror"])
                self.assertEqual(ranked[0][0].title, "Shadow Drama")

    def test_soft_preferences_do_not_become_hard_exclusions(self):
        intent = parse_search_intent(
            "I want something not too dark and kind of funny",
            MOVIES,
        )

        self.assertEqual(intent.target_dimensions["darkness"], 40)
        self.assertEqual(intent.target_dimensions["humor"], 60)
        self.assertNotIn("comedy", intent.exclude_themes)
        self.assertNotIn("comedy", intent.include_themes)

    def test_not_too_much_is_a_soft_preference(self):
        intent = parse_search_intent(
            "A tense thriller with not too much action",
            MOVIES,
        )

        self.assertEqual(intent.target_dimensions["action"], 40)
        self.assertNotIn("action", intent.exclude_themes)
        self.assertNotIn("action", intent.include_themes)
        self.assertIn("thriller", intent.include_themes)

    def test_negation_carries_across_coordinated_theme_list(self):
        intent = parse_search_intent("no horror or thriller movies", MOVIES)

        self.assertEqual(intent.exclude_themes, ["horror", "thriller"])
        self.assertNotIn("horror", intent.include_themes)
        self.assertNotIn("thriller", intent.include_themes)

    def test_negation_carries_across_coordinated_country_list(self):
        intent = parse_search_intent(
            "movies without Indian or Korean titles",
            MOVIES,
        )

        self.assertEqual(intent.excluded_countries, ["India", "South Korea"])
        self.assertEqual(intent.preferred_countries, [])

    def test_neither_nor_excludes_each_coordinated_preference(self):
        theme_intent = parse_search_intent(
            "neither action nor comedy",
            MOVIES,
        )
        country_intent = parse_search_intent(
            "neither Indian nor Korean movies",
            MOVIES,
        )

        self.assertEqual(theme_intent.include_themes, [])
        self.assertEqual(theme_intent.exclude_themes, ["action", "comedy"])
        self.assertEqual(theme_intent.target_dimensions["action"], 10)
        self.assertEqual(theme_intent.target_dimensions["humor"], 10)
        self.assertEqual(country_intent.preferred_countries, [])
        self.assertEqual(
            country_intent.excluded_countries,
            ["India", "South Korea"],
        )

    def test_negation_carries_across_comma_separated_lists(self):
        for query in (
            "no action, comedy, or romance movies",
            "no action, comedy, romance movies",
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                self.assertEqual(
                    intent.exclude_themes,
                    ["action", "comedy", "romance"],
                )
                self.assertEqual(intent.include_themes, [])

        for query in (
            "movies without Indian, Korean, or Japanese titles",
            "movies without Indian, Korean, Japanese titles",
        ):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                self.assertEqual(
                    intent.excluded_countries,
                    ["India", "Japan", "South Korea"],
                )
                self.assertEqual(intent.preferred_countries, [])

    def test_negation_list_does_not_absorb_a_positive_clause(self):
        intent = parse_search_intent("not horror, just comedy", MOVIES)

        self.assertEqual(intent.exclude_themes, ["horror"])
        self.assertEqual(intent.include_themes, ["comedy"])

    def test_negation_does_not_cross_contrasting_clause(self):
        intent = parse_search_intent(
            "not horror but a funny thriller",
            MOVIES,
        )

        self.assertEqual(intent.exclude_themes, ["horror"])
        self.assertIn("thriller", intent.include_themes)

    def test_natural_aliases_map_to_movie_dna(self):
        intent = parse_search_intent(
            "A suspenseful high-energy thriller with big-screen visuals and huge twists",
            MOVIES,
        )

        self.assertIn("thriller", intent.include_themes)
        self.assertEqual(intent.target_dimensions["pacing"], 85)
        self.assertEqual(intent.target_dimensions["visual_spectacle"], 75)
        self.assertEqual(intent.target_dimensions["plot_twists"], 75)

    def test_thought_provoking_maps_to_narrative_complexity(self):
        intent = parse_search_intent("something thought-provoking and smart", MOVIES)

        self.assertEqual(intent.target_dimensions["narrative_complexity"], 75)

    def test_exclusion_only_query_penalizes_matching_movies(self):
        intent = SearchIntent(
            target_dimensions={},
            exclude_themes=["horror"],
        )
        horror_movie = MovieDNA(
            title="Dark House",
            year=2026,
            country="USA",
            genres=["Horror"],
            themes=["survival"],
            dimensions={},
            summary="A test horror movie.",
        )
        comedy_movie = MovieDNA(
            title="Bright Day",
            year=2026,
            country="USA",
            genres=["Comedy"],
            themes=["friendship"],
            dimensions={},
            summary="A test comedy movie.",
        )

        self.assertLess(score_movie(horror_movie, intent), score_movie(comedy_movie, intent))


if __name__ == "__main__":
    unittest.main()
