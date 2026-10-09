import unittest

from app.data.movies import MOVIES
from app.models import MovieDNA, SearchIntent
from app.services.ai import parse_search_intent
from app.services.scoring import score_movie


class SearchIntentTests(unittest.TestCase):
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
