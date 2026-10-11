import os
import unittest
from unittest.mock import Mock, patch

from app.data.movies import MOVIES
from app.models import MovieDNA
from app.services.tmdb import (
    _from_tmdb,
    has_exact_local_title,
    looks_like_title_query,
    search_local_movies,
    search_tmdb_movies,
)


class TMDBProfileTests(unittest.TestCase):
    def test_local_title_search_normalizes_unicode(self):
        amelie = MovieDNA(
            title="Amélie",
            year=2001,
            country="France",
            genres=["Comedy", "Romance"],
            themes=["love"],
            dimensions={},
            summary="A test movie with an accented title.",
        )
        baahubali = next(
            movie for movie in MOVIES
            if movie.title == "Baahubali: The Beginning"
        )

        self.assertTrue(has_exact_local_title("Amelie", [amelie]))
        self.assertEqual(search_local_movies("Amelie", [amelie]), [amelie])
        self.assertTrue(has_exact_local_title("బాహుబలి", [baahubali]))
        self.assertEqual(search_local_movies("బాహుబలి", [baahubali]), [baahubali])

    def test_title_casing_disambiguates_titles_with_vibe_words(self):
        for title in (
            "Fast Five",
            "Dark City",
            "Scary Movie",
            "The Fast and the Furious",
        ):
            with self.subTest(title=title):
                self.assertTrue(looks_like_title_query(title))

        for description in (
            "fast action movie",
            "A dark mystery",
            "Like Interstellar",
            "scary movie",
            "something funny and romantic",
        ):
            with self.subTest(description=description):
                self.assertFalse(looks_like_title_query(description))

    def test_parsed_vibe_preferences_override_lowercase_title_guessing(self):
        self.assertTrue(looks_like_title_query("space movie"))
        self.assertFalse(looks_like_title_query("space movie", True))
        self.assertTrue(looks_like_title_query("Space Movie", True))

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
