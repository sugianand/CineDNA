import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.data.movies import MOVIES
from app.main import app
from app.models import MovieDNA


class CineDNAAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertGreater(response.json()["movies"], 0)
        self.assertIn("tmdb_enabled", response.json())

    def test_search_returns_ranked_movies(self):
        response = self.client.post(
            "/api/search",
            json={"query": "A twisty Indian mystery with dark humor", "limit": 3},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertLessEqual(len(body["results"]), 3)
        self.assertGreater(len(body["results"]), 0)
        scores = [item["score"] for item in body["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0 <= score <= 100 for score in scores))

    def test_empty_search_rejected(self):
        response = self.client.post("/api/search", json={"query": ""})
        self.assertEqual(response.status_code, 422)

    def test_whitespace_only_search_rejected(self):
        response = self.client.post("/api/search", json={"query": " \n\t "})
        self.assertEqual(response.status_code, 422)

    def test_short_vibe_search_rejected(self):
        response = self.client.post(
            "/api/search",
            json={"query": "x", "mode": "vibe"},
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_short_title_search_is_normalized(self, _configured, search_tmdb):
        search_tmdb.return_value = [
            MovieDNA(
                title="Up",
                year=2009,
                country="USA",
                genres=["Animation", "Adventure"],
                themes=["grief", "friendship"],
                dimensions={"emotional_intensity": 88},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="14160",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "  Up \n", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_called_once_with("Up", 6)
        self.assertEqual(response.json()["query"], "Up")
        self.assertEqual(response.json()["results"][0]["movie"]["title"], "Up")

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_title_search_uses_tmdb_catalog(self, _configured, search_tmdb):
        search_tmdb.return_value = [
            MovieDNA(
                title="Baahubali: The Beginning",
                original_title="బాహుబలి:ద బిగినింగ్",
                year=2015,
                country="India",
                genres=["Action", "Drama"],
                themes=["power", "family"],
                dimensions={"action": 90, "visual_spectacle": 95},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="256040",
                poster_url="https://image.tmdb.org/t/p/w500/example.jpg",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "Baahubali", "limit": 5},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ai_provider"], "tmdb-catalog+heuristic-dna")
        self.assertEqual(body["results"][0]["movie"]["title"], "Baahubali: The Beginning")
        self.assertEqual(body["results"][0]["movie"]["source"], "tmdb")

    def test_vibe_query_does_not_require_tmdb(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "dark Indian mystery with huge plot twists", "limit": 3},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()

    def test_auto_mode_routes_scary_description_to_horror(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "scary movie", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertIn("horror", body["intent"]["include_themes"])
        self.assertIn("Horror", body["results"][0]["movie"]["genres"])

    def test_auto_mode_routes_feel_good_description_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "feel-good movie", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["target_dimensions"]["darkness"], 20)
        self.assertEqual(body["results"][0]["movie"]["title"], "3 Idiots")

    def test_auto_mode_routes_rom_com_description_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "rom-com", "limit": 3},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["include_themes"], ["comedy", "romance"])
        self.assertEqual(body["intent"]["target_dimensions"]["romance"], 75)
        self.assertEqual(body["intent"]["target_dimensions"]["humor"], 75)

    def test_auto_mode_routes_korean_thriller_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "Korean thriller", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["preferred_countries"], ["South Korea"])
        self.assertEqual(body["results"][0]["movie"]["title"], "Parasite")

    def test_auto_mode_limits_bengali_mystery_to_indian_catalog(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "Bengali mystery", "limit": 6},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["preferred_countries"], ["India"])
        self.assertTrue(body["results"])
        self.assertTrue(
            all(result["movie"]["country"] == "India" for result in body["results"])
        )

    def test_auto_mode_routes_anime_to_japanese_catalog(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "anime", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["preferred_countries"], ["Japan"])
        self.assertEqual(body["results"][0]["movie"]["title"], "Spirited Away")

    def test_auto_mode_routes_fantasy_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "fantasy movie", "limit": 2},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertIn("fantasy", body["intent"]["include_themes"])
        self.assertTrue(
            all("Fantasy" in result["movie"]["genres"] for result in body["results"])
        )

    def test_auto_mode_routes_animated_movie_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "animated movie", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertIn("animation", body["intent"]["include_themes"])
        self.assertEqual(body["results"][0]["movie"]["title"], "Spirited Away")

    def test_auto_mode_routes_catalog_genres_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "adventure movie", "limit": 3},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertIn("adventure", body["intent"]["include_themes"])
        self.assertTrue(
            all("Adventure" in result["movie"]["genres"] for result in body["results"])
        )

    def test_auto_mode_routes_decade_request_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "movies from the 2010s", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["min_year"], 2010)
        self.assertEqual(body["intent"]["max_year"], 2019)
        self.assertTrue(body["results"])
        self.assertTrue(
            all(2010 <= result["movie"]["year"] <= 2019 for result in body["results"])
        )

    def test_auto_mode_routes_abbreviated_decade_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "movies from the '90s", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["min_year"], 1990)
        self.assertEqual(body["intent"]["max_year"], 1999)
        self.assertTrue(body["results"])
        self.assertIn(
            "The Matrix",
            {result["movie"]["title"] for result in body["results"]},
        )
        self.assertTrue(
            all(
                1990 <= result["movie"]["year"] <= 1999
                for result in body["results"]
            )
        )

    def test_auto_mode_routes_film_release_year_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "films from 2015", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["min_year"], 2015)
        self.assertEqual(body["intent"]["max_year"], 2015)
        self.assertTrue(body["results"])
        self.assertTrue(
            all(result["movie"]["year"] == 2015 for result in body["results"])
        )

    def test_auto_mode_routes_from_to_year_range_to_vibe_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "movies from 2013 to 2016", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["min_year"], 2013)
        self.assertEqual(body["intent"]["max_year"], 2016)
        self.assertTrue(body["results"])
        self.assertTrue(
            all(
                2013 <= result["movie"]["year"] <= 2016
                for result in body["results"]
            )
        )

    def test_auto_mode_uses_parsed_themes_to_avoid_title_search(self):
        for query, theme in (
            ("space movie", "space"),
            ("family movie", "family"),
            ("war movie", "war"),
        ):
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 3},
                )

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                self.assertIn(theme, response.json()["intent"]["include_themes"])

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_title_mode_bypasses_title_guessing(self, _configured, search_tmdb):
        search_tmdb.return_value = [
            MovieDNA(
                title="The Dark Knight",
                year=2008,
                country="USA",
                genres=["Action", "Crime"],
                themes=["justice"],
                dimensions={"action": 94, "darkness": 89},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="155",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "The Dark Knight", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_called_once_with("The Dark Knight", 6)
        self.assertEqual(response.json()["results"][0]["movie"]["source"], "tmdb")

    def test_vibe_mode_never_triggers_title_search(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "Arrival", "mode": "vibe"},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()

    def test_external_movie_dna_drives_more_like_this_search(self):
        interstellar = next(movie for movie in MOVIES if movie.title == "Interstellar")
        external_reference = MovieDNA(
            title="Remote Space Story",
            year=2026,
            country="International",
            genres=["Science Fiction"],
            themes=["space", "family"],
            dimensions=dict(interstellar.dimensions),
            summary="A fictional expanded-catalog reference movie.",
            source="tmdb",
            source_id="987654",
        )

        response = self.client.post(
            "/api/search",
            json={
                "query": "Like Remote Space Story, but show me a different movie with similar DNA",
                "mode": "vibe",
                "reference_movie": external_reference.model_dump(mode="json"),
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["reference_titles"], ["Remote Space Story"])
        self.assertEqual(body["intent"]["target_dimensions"], interstellar.dimensions)
        self.assertEqual(body["results"][0]["movie"]["title"], "Interstellar")

    @patch("app.main.search_tmdb_movies", return_value=[])
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_title_mode_falls_back_to_local_catalog(self, _configured, _search_tmdb):
        response = self.client.post(
            "/api/search",
            json={"query": "Interstelar", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")
        self.assertEqual(body["results"][0]["movie"]["title"], "Interstellar")

    @patch("app.main.search_tmdb_movies", return_value=[])
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_title_mode_does_not_return_unrelated_vibe_results(
        self, _configured, _search_tmdb
    ):
        response = self.client.post(
            "/api/search",
            json={"query": "A Movie That Does Not Exist", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"], [])
        self.assertIn("No movie title matched", body["intent"]["explanation"])

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_title_mode_uses_local_catalog_without_tmdb(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "Dune", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"][0]["movie"]["title"], "Dune: Part Two")
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_bahubali_spelling_falls_back_to_local_catalog(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "bahubali"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"][0]["movie"]["title"], "Baahubali: The Beginning")
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_rrr_is_available_in_local_catalog(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "rrr"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        movie = body["results"][0]["movie"]
        self.assertEqual(movie["title"], "RRR")
        self.assertEqual(movie["country"], "India")
        self.assertIn("Action", movie["genres"])
        self.assertGreaterEqual(movie["dimensions"]["action"], 95)
        self.assertGreaterEqual(movie["dimensions"]["visual_spectacle"], 95)
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_matrix_expands_offline_1990s_coverage(self, _configured):
        title_response = self.client.post(
            "/api/search",
            json={"query": "the matrix"},
        )

        self.assertEqual(title_response.status_code, 200)
        title_body = title_response.json()
        movie = title_body["results"][0]["movie"]
        self.assertEqual(movie["title"], "The Matrix")
        self.assertEqual(movie["year"], 1999)
        self.assertIn("Science Fiction", movie["genres"])
        self.assertGreaterEqual(movie["dimensions"]["action"], 90)
        self.assertEqual(title_body["ai_provider"], "cinedna-title-catalog")

        period_response = self.client.post(
            "/api/search",
            json={"query": "movies from the 1990s", "limit": 20},
        )

        self.assertEqual(period_response.status_code, 200)
        period_body = period_response.json()
        self.assertTrue(period_body["results"])
        self.assertIn(
            "The Matrix",
            {result["movie"]["title"] for result in period_body["results"]},
        )
        self.assertTrue(
            all(
                1990 <= result["movie"]["year"] <= 1999
                for result in period_body["results"]
            )
        )

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_godfather_expands_offline_1970s_coverage(self, _configured):
        title_response = self.client.post(
            "/api/search",
            json={"query": "the godfather"},
        )

        self.assertEqual(title_response.status_code, 200)
        title_body = title_response.json()
        movie = title_body["results"][0]["movie"]
        self.assertEqual(movie["title"], "The Godfather")
        self.assertEqual(movie["year"], 1972)
        self.assertIn("Crime", movie["genres"])
        self.assertGreaterEqual(movie["dimensions"]["character_depth"], 95)
        self.assertEqual(title_body["ai_provider"], "cinedna-title-catalog")

        period_response = self.client.post(
            "/api/search",
            json={"query": "seventies crime movies", "limit": 20},
        )

        self.assertEqual(period_response.status_code, 200)
        period_body = period_response.json()
        self.assertTrue(period_body["results"])
        self.assertIn(
            "The Godfather",
            {result["movie"]["title"] for result in period_body["results"]},
        )
        self.assertTrue(
            all(
                1970 <= result["movie"]["year"] <= 1979
                for result in period_body["results"]
            )
        )

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_parasite_is_available_in_local_catalog_by_both_titles(self, _configured):
        for query in ("parasite", "기생충"):
            with self.subTest(query=query):
                response = self.client.post(
                    "/api/search",
                    json={"query": query},
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                movie = body["results"][0]["movie"]
                self.assertEqual(movie["title"], "Parasite")
                self.assertEqual(movie["original_title"], "기생충")
                self.assertEqual(movie["country"], "South Korea")
                self.assertIn("Thriller", movie["genres"])
                self.assertGreaterEqual(movie["dimensions"]["plot_twists"], 90)
                self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_spirited_away_is_available_by_both_titles(self, _configured):
        for query in ("spirited away", "千と千尋の神隠し"):
            with self.subTest(query=query):
                response = self.client.post(
                    "/api/search",
                    json={"query": query},
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                movie = body["results"][0]["movie"]
                self.assertEqual(movie["title"], "Spirited Away")
                self.assertEqual(movie["original_title"], "千と千尋の神隠し")
                self.assertEqual(movie["country"], "Japan")
                self.assertIn("Animation", movie["genres"])
                self.assertGreaterEqual(movie["dimensions"]["world_building"], 95)
                self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_recognizes_exact_title_with_vibe_word(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "The Dark Knight"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"][0]["movie"]["title"], "The Dark Knight")
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_auto_mode_recognizes_title_cased_external_title_with_vibe_word(
        self,
        _configured,
        search_tmdb,
    ):
        search_tmdb.return_value = [
            MovieDNA(
                title="Fast Five",
                year=2011,
                country="USA",
                genres=["Action"],
                themes=["family"],
                dimensions={"action": 90, "pacing": 88},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="51497",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "Fast Five"},
        )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_called_once_with("Fast Five", 6)
        self.assertEqual(
            response.json()["results"][0]["movie"]["title"],
            "Fast Five",
        )

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_short_title_does_not_match_inside_unrelated_words(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "It", "mode": "title"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])


if __name__ == "__main__":
    unittest.main()
