import unittest

from app.data.movies import MOVIES
from app.models import MovieDNA, SearchIntent
from app.services.ai import parse_search_intent
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

    def test_reference_movie_matches_unique_title_before_subtitle(self):
        intent = parse_search_intent(
            "Something like Dune but funnier",
            MOVIES,
        )

        dune = next(movie for movie in MOVIES if movie.title == "Dune: Part Two")
        self.assertEqual(intent.reference_titles, ["Dune: Part Two"])
        self.assertEqual(intent.target_dimensions["visual_spectacle"], dune.dimensions["visual_spectacle"])
        self.assertGreater(intent.target_dimensions["humor"], dune.dimensions["humor"])

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
