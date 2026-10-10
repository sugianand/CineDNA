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

    def test_sci_fi_aliases_map_to_science_fiction(self):
        for query in ("A fast sci-fi movie", "A sci fi epic", "Something scifi"):
            with self.subTest(query=query):
                intent = parse_search_intent(query, MOVIES)
                ranked = rank_movies(MOVIES, intent, limit=3)

                self.assertIn("science fiction", intent.include_themes)
                self.assertTrue(
                    all("Science Fiction" in movie.genres for movie, _score in ranked)
                )

    def test_negated_sci_fi_alias_excludes_science_fiction(self):
        intent = parse_search_intent("A fast movie with no sci-fi", MOVIES)
        ranked = rank_movies(MOVIES, intent, limit=20)

        self.assertIn("science fiction", intent.exclude_themes)
        self.assertTrue(
            all("Science Fiction" not in movie.genres for movie, _score in ranked)
        )

    def test_negated_and_reduced_pacing_terms_reverse_the_requested_speed(self):
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

    def test_reference_movie_matches_unique_title_before_subtitle(self):
        intent = parse_search_intent(
            "Something like Dune but funnier",
            MOVIES,
        )

        dune = next(movie for movie in MOVIES if movie.title == "Dune: Part Two")
        self.assertEqual(intent.reference_titles, ["Dune: Part Two"])
        self.assertEqual(intent.target_dimensions["visual_spectacle"], dune.dimensions["visual_spectacle"])
        self.assertGreater(intent.target_dimensions["humor"], dune.dimensions["humor"])

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
