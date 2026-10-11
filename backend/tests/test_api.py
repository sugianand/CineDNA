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
