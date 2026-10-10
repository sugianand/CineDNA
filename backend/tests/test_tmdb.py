import os
import unittest
from unittest.mock import Mock, patch

from app.services.tmdb import _from_tmdb, search_tmdb_movies


class TMDBProfileTests(unittest.TestCase):
    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_invalid_catalog_json_fails_closed(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("invalid JSON")
        get.return_value = response

        self.assertEqual(search_tmdb_movies("Dune"), [])

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_invalid_catalog_items_do_not_discard_valid_movies(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                None,
                {"title": "Broken", "vote_average": "not-a-number"},
                {
                    "id": 3,
                    "title": "Valid Movie",
                    "genre_ids": [18],
                    "overview": "A family faces a difficult choice.",
                    "vote_average": 7.5,
                    "release_date": "2026-01-01",
                },
            ]
        }
        get.return_value = response

        movies = search_tmdb_movies("Valid Movie", limit=1)

        self.assertEqual([movie.title for movie in movies], ["Valid Movie"])

    def test_overview_keywords_do_not_match_inside_unrelated_words(self):
        movie = _from_tmdb(
            {
                "id": 1,
                "title": "The Artisan",
                "genre_ids": [],
                "overview": "An award-winning artist designs gloves for a celebration.",
                "vote_average": 7.0,
                "release_date": "2026-01-01",
            }
        )

        self.assertEqual(movie.dimensions["action"], 30)
        self.assertEqual(movie.dimensions["romance"], 25)
        self.assertNotIn("war", movie.themes)
        self.assertNotIn("love", movie.themes)

    def test_whole_overview_keywords_still_shape_movie_dna(self):
        movie = _from_tmdb(
            {
                "id": 2,
                "title": "Home Front",
                "genre_ids": [],
                "overview": "A family faces survival during a war, confronts murder, and finds love.",
                "vote_average": 7.0,
                "release_date": "2026-01-01",
            }
        )

        self.assertEqual(movie.dimensions["emotional_intensity"], 62)
        self.assertEqual(movie.dimensions["pacing"], 60)
        self.assertEqual(movie.dimensions["action"], 40)
        self.assertEqual(movie.dimensions["romance"], 37)
        self.assertEqual(movie.dimensions["darkness"], 54)
        self.assertTrue({"family", "survival", "war", "murder", "love"} <= set(movie.themes))


if __name__ == "__main__":
    unittest.main()
