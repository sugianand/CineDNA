import os
import unittest
from unittest.mock import Mock, patch

from app.data.movies import MOVIES
from app.models import MovieDNA, SearchIntent
from app.services.tmdb import (
    _from_tmdb,
    discover_tmdb_movies,
    has_exact_local_title,
    looks_like_title_query,
    search_local_movies,
    search_tmdb_movies,
)


class TMDBProfileTests(unittest.TestCase):

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_movie_detail_fetch_by_id(self, get):
        from app.services.tmdb import get_tmdb_movie
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "id": 256040, "title": "Baahubali: The Beginning",
            "genres": [{"id": 28, "name": "Action"}],
            "origin_country": ["IN"], "release_date": "2015-07-10",
            "overview": "An epic story.", "vote_average": 7.5,
        }
        get.return_value = response
        movie = get_tmdb_movie("256040")
        self.assertEqual(movie.title, "Baahubali: The Beginning")
        self.assertEqual(movie.genres, ["Action"])
        self.assertEqual(movie.source_id, "256040")

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    def test_invalid_movie_id_does_not_trigger_network(self):
        from app.services.tmdb import get_tmdb_movie
        with patch("app.services.tmdb.httpx.get") as get:
            self.assertIsNone(get_tmdb_movie("../search"))
            self.assertIsNone(get_tmdb_movie("bad"))
            self.assertIsNone(get_tmdb_movie("0"))
            get.assert_not_called()

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_movie_detail_requires_the_requested_identity(self, get):
        from app.services.tmdb import get_tmdb_movie
        response = Mock()
        response.raise_for_status.return_value = None
        get.return_value = response

        invalid_payloads = (
            {"title": "Missing ID"},
            {"id": 0, "title": "Invalid ID"},
            {"id": "256040", "title": "String ID"},
            {"id": 999, "title": "Different Movie"},
            {"id": 256040, "title": "   ", "original_title": ""},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response.json.return_value = payload

                self.assertIsNone(get_tmdb_movie("256040"))


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
            "Something Borrowed",
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

    def test_title_blockers_do_not_match_inside_larger_words(self):
        for title in ("darkman", "darkness falls", "breakfast at tiffanys"):
            with self.subTest(title=title):
                self.assertTrue(looks_like_title_query(title))

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

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_catalog_items_require_a_stable_profile_identity(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {"title": "Missing ID"},
                {"id": 0, "title": "Invalid ID"},
                {"id": "123", "title": "String ID"},
                {"id": 4, "title": "   ", "original_title": ""},
                {"id": 5, "original_title": "Stable Original Title"},
            ]
        }
        get.return_value = response

        movies = search_tmdb_movies("Stable Original Title", limit=1)

        self.assertEqual([movie.title for movie in movies], ["Stable Original Title"])
        self.assertEqual(movies[0].source_id, "5")


    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_discovery_filters_country_year_genres_and_exclusions(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [{
                "id": 101,
                "title": "Regional Thriller",
                "release_date": "2015-03-01",
                "genre_ids": [53],
                "origin_country": ["IN"],
            }]
        }
        get.return_value = response
        intent = SearchIntent(
            target_dimensions={},
            include_themes=["thriller", "mystery"],
            exclude_themes=["comedy"],
            preferred_countries=["India"],
            min_year=2010,
            max_year=2019,
        )

        movies = discover_tmdb_movies(intent)

        self.assertEqual([movie.title for movie in movies], ["Regional Thriller"])
        self.assertEqual(movies[0].country, "India")
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://api.themoviedb.org/3/discover/movie")
        self.assertEqual(kwargs["params"]["with_genres"], "53|9648")
        self.assertEqual(kwargs["params"]["without_genres"], "35")
        self.assertEqual(kwargs["params"]["with_origin_country"], "IN")
        self.assertEqual(kwargs["params"]["primary_release_date.gte"], "2010-01-01")
        self.assertEqual(kwargs["params"]["primary_release_date.lte"], "2019-12-31")
        self.assertEqual(kwargs["timeout"], 4.0)

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_discovery_excludes_any_requested_genre(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"results": []}
        get.return_value = response

        discover_tmdb_movies(SearchIntent(
            target_dimensions={},
            exclude_themes=["horror", "comedy", "horror"],
        ))

        self.assertEqual(
            get.call_args.kwargs["params"]["without_genres"],
            "27|35",
        )

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get")
    def test_discovery_filters_newly_supported_countries(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"results": []}
        get.return_value = response

        for country, country_code in (("Brazil", "BR"), ("France", "FR")):
            with self.subTest(country=country):
                discover_tmdb_movies(SearchIntent(
                    target_dimensions={},
                    preferred_countries=[country],
                ))

                self.assertEqual(
                    get.call_args.kwargs["params"]["with_origin_country"],
                    country_code,
                )

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": "test-token"})
    @patch("app.services.tmdb.httpx.get", side_effect=__import__("httpx").TimeoutException("slow"))
    def test_discovery_timeout_preserves_offline_fallback(self, _get):
        self.assertEqual(discover_tmdb_movies(SearchIntent(target_dimensions={})), [])

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": ""})
    @patch("app.services.tmdb.httpx.get")
    def test_discovery_requires_token(self, get):
        self.assertEqual(discover_tmdb_movies(SearchIntent(target_dimensions={})), [])
        get.assert_not_called()

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

    def test_origin_country_is_preserved_in_generated_profiles(self):
        cases = (
            ({"origin_country": ["US"], "original_language": "en"}, "USA"),
            (
                {"origin_country": ["GB", "US"], "original_language": "en"},
                "United Kingdom",
            ),
            ({"origin_country": ["IN"], "original_language": "en"}, "India"),
            ({"origin_country": [], "original_language": "ja"}, "Japan"),
            ({"original_language": "ko"}, "South Korea"),
            (
                {"origin_country": ["ZZ"], "original_language": "en"},
                "International",
            ),
        )

        for metadata, expected_country in cases:
            with self.subTest(metadata=metadata):
                movie = _from_tmdb(
                    {
                        "id": 4,
                        "title": "Country Test",
                        "genre_ids": [18],
                        "overview": "A test movie.",
                        "vote_average": 7.0,
                        "release_date": "2026-01-01",
                        **metadata,
                    }
                )

                self.assertEqual(movie.country, expected_country)


if __name__ == "__main__":
    unittest.main()
