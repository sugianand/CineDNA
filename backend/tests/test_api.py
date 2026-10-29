import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.data.movies import MOVIES
from app.main import app
from app.models import MovieDNA


class CineDNAAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)


    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_movie_profile_resolves_local_title(self, _configured):
        response = self.client.get("/api/movie", params={"title": "Interstellar"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Interstellar")

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_movie_profile_uses_same_fuzzy_matching_as_search(self, _configured):
        cases = {
            "Amelie": "Amélie",
            "avengers endgame": "Avengers: Endgame",
            "dark knigt": "The Dark Knight",
            "Dune": "Dune: Part Two",
        }

        for title, expected_title in cases.items():
            with self.subTest(title=title):
                response = self.client.get(
                    "/api/movie",
                    params={"title": title, "source": "cinedna"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["title"], expected_title)

    @patch("app.main.get_tmdb_movie")
    def test_movie_profile_resolves_external_id(self, get_movie):
        get_movie.return_value = MovieDNA(
            title="Baahubali: The Beginning",
            year=2015, country="India", genres=["Action"], themes=["family"],
            dimensions={"action": 95}, summary="An epic movie.",
            source="tmdb", source_id="256040",
        )
        response = self.client.get("/api/movie", params={
            "title": "Baahubali: The Beginning", "source": "tmdb",
            "source_id": "256040",
        })
        self.assertEqual(response.status_code, 200)
        get_movie.assert_called_once_with("256040")
        self.assertEqual(response.json()["source_id"], "256040")

    @patch("app.main.get_tmdb_movie", return_value=None)
    def test_missing_external_id_does_not_fall_back_to_local_title(self, get_movie):
        response = self.client.get("/api/movie", params={
            "title": "Dune", "source": "tmdb", "source_id": "999999",
        })

        self.assertEqual(response.status_code, 404)
        get_movie.assert_called_once_with("999999")

    @patch("app.main.get_tmdb_movie")
    def test_external_profile_without_id_does_not_fall_back_to_local_title(
        self,
        get_movie,
    ):
        response = self.client.get("/api/movie", params={
            "title": "Dune", "source": "tmdb",
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Movie profile not found")
        get_movie.assert_not_called()

    @patch("app.main.search_local_movies")
    def test_movie_profile_rejects_unknown_source(self, search_local_movies):
        response = self.client.get("/api/movie", params={
            "title": "Dune", "source": "bogus",
        })

        self.assertEqual(response.status_code, 422)
        search_local_movies.assert_not_called()

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_missing_movie_profile_returns_404(self, _configured):
        response = self.client.get("/api/movie", params={"title": "No Such Movie"})
        self.assertEqual(response.status_code, 404)

    @patch.dict(os.environ, {"RENDER_GIT_COMMIT": "abc123"})
    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertGreater(response.json()["movies"], 0)
        self.assertIn("tmdb_enabled", response.json())
        self.assertEqual(response.json()["revision"], "abc123")

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

    def test_multi_reference_search_excludes_every_source_movie(self):
        response = self.client.post(
            "/api/search",
            json={
                "query": "Like Interstellar and Arrival",
                "limit": 20,
                "mode": "auto",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            body["intent"]["reference_titles"],
            ["Interstellar", "Arrival"],
        )
        result_titles = {result["movie"]["title"] for result in body["results"]}
        self.assertNotIn("Interstellar", result_titles)
        self.assertNotIn("Arrival", result_titles)

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_excludes_a_negated_movie_title(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "Not Titanic", "limit": 20, "mode": "auto"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["reference_titles"], [])
        self.assertEqual(body["intent"]["excluded_titles"], ["Titanic"])
        self.assertNotEqual(body["ai_provider"], "cinedna-title-catalog")
        self.assertNotIn(
            "Titanic",
            {result["movie"]["title"] for result in body["results"]},
        )


    @patch("app.main.discover_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_vibe_discovery_expands_country_and_decade_coverage(
        self, _configured, discover
    ):
        discover.return_value = [
            MovieDNA(
                title="New Regional Drama",
                year=1997,
                country="India",
                genres=["Drama"],
                themes=["family"],
                dimensions={"emotional_intensity": 85},
                summary="A representative 1990s movie from the external catalog.",
                source="tmdb",
                source_id="987321",
            ),
            MovieDNA(
                title="Wrong Country Movie",
                year=1997,
                country="USA",
                genres=["Drama"],
                themes=["family"],
                dimensions={},
                summary="Must be filtered out.",
                source="tmdb",
                source_id="112233",
            ),
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "Indian movies from the 1990s", "limit": 20},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ai_provider"], "tmdb-discover+rule-based-dna")
        self.assertIn(
            "New Regional Drama",
            [result["movie"]["title"] for result in body["results"]],
        )
        self.assertTrue(all(
            result["movie"]["country"] == "India"
            and 1990 <= result["movie"]["year"] <= 1999
            for result in body["results"]
        ))
        discover.assert_called_once()

    @patch("app.main.discover_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_discovery_deduplicates_curated_titles(self, _configured, discover):
        discover.return_value = [MOVIES[0]]
        response = self.client.post(
            "/api/search",
            json={"query": "emotional science fiction", "mode": "vibe", "limit": 20},
        )

        self.assertEqual(response.status_code, 200)
        titles = [item["movie"]["title"] for item in response.json()["results"]]
        self.assertEqual(titles.count(MOVIES[0].title), 1)

    @patch("app.main.discover_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_discovery_deduplicates_normalized_title_variants(
        self,
        _configured,
        discover,
    ):
        discover.return_value = [
            MovieDNA(
                title="Amelie",
                original_title="Le Fabuleux Destin d'Amelie Poulain",
                year=2001,
                country="France",
                genres=["Comedy", "Romance"],
                themes=["love"],
                dimensions={"romance": 85, "humor": 65},
                summary="The same movie returned without title diacritics.",
                source="tmdb",
                source_id="194",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={
                "query": "a French romantic comedy",
                "mode": "vibe",
                "limit": 20,
            },
        )

        self.assertEqual(response.status_code, 200)
        titles = [item["movie"]["title"] for item in response.json()["results"]]
        self.assertEqual(sum(title in {"Amélie", "Amelie"} for title in titles), 1)

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

    def test_reference_movie_rejects_out_of_range_dna_dimensions(self):
        reference_movie = {
            "title": "Corrupt Movie",
            "year": 2026,
            "country": "USA",
            "genres": ["Drama"],
            "themes": ["family"],
            "dimensions": {"action": 50},
            "summary": "A malformed persisted reference movie.",
        }

        for score in (-1, 101):
            with self.subTest(score=score):
                reference_movie["dimensions"]["action"] = score
                response = self.client.post(
                    "/api/search",
                    json={
                        "query": "Like Corrupt Movie, but different",
                        "mode": "vibe",
                        "reference_movie": reference_movie,
                    },
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

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_honors_non_prefixed_exclusions(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "a non-Indian, non-horror movie", "limit": 20},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["excluded_countries"], ["India"])
        self.assertIn("horror", body["intent"]["exclude_themes"])
        self.assertNotIn("horror", body["intent"]["include_themes"])
        self.assertTrue(body["results"])
        self.assertTrue(
            all(
                result["movie"]["country"] != "India"
                and "Horror" not in result["movie"]["genres"]
                for result in body["results"]
            )
        )

    def test_vibe_mode_honors_coordinated_exclusions(self):
        response = self.client.post(
            "/api/search",
            json={
                "query": "no action, comedy, or romance movies",
                "limit": 20,
                "mode": "vibe",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            body["intent"]["exclude_themes"],
            ["action", "comedy", "romance"],
        )
        self.assertTrue(body["results"])
        self.assertTrue(
            all(
                not {"Action", "Comedy", "Romance"}.intersection(
                    result["movie"]["genres"]
                )
                for result in body["results"]
            )
        )

    def test_vibe_mode_honors_neither_nor_exclusions(self):
        response = self.client.post(
            "/api/search",
            json={
                "query": "neither action nor comedy",
                "limit": 20,
                "mode": "vibe",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["include_themes"], [])
        self.assertEqual(
            body["intent"]["exclude_themes"],
            ["action", "comedy"],
        )
        self.assertTrue(body["results"])
        self.assertTrue(
            all(
                not {"Action", "Comedy"}.intersection(result["movie"]["genres"])
                for result in body["results"]
            )
        )

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_preserves_dark_request_while_excluding_scary_movies(
        self,
        _configured,
    ):
        for query in ("dark but not scary", "not scary but dark"):
            with self.subTest(query=query):
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 6},
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["intent"]["target_dimensions"]["darkness"], 75)
                self.assertEqual(body["intent"]["exclude_themes"], ["horror"])
                self.assertTrue(body["results"])
                self.assertTrue(
                    all(
                        "Horror" not in result["movie"]["genres"]
                        for result in body["results"]
                    )
                )
                self.assertGreaterEqual(
                    body["results"][0]["movie"]["dimensions"]["darkness"],
                    65,
                )

    def test_auto_mode_keeps_not_too_much_as_a_soft_preference(self):
        response = self.client.post(
            "/api/search",
            json={"query": "a tense thriller with not too much action", "limit": 6},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["target_dimensions"]["action"], 40)
        self.assertNotIn("action", body["intent"]["exclude_themes"])
        self.assertTrue(body["results"])

    def test_auto_mode_routes_feel_good_description_to_vibe_search(self):
        for query in ("feel-good movie", "something lighter"):
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 1},
                )

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                body = response.json()
                self.assertEqual(
                    body["intent"]["target_dimensions"]["darkness"],
                    20,
                )
                self.assertLessEqual(
                    body["results"][0]["movie"]["dimensions"]["darkness"],
                    35,
                )

    def test_auto_mode_routes_less_lighthearted_to_darker_results(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "less lighthearted", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["target_dimensions"]["darkness"], 80)
        self.assertGreaterEqual(
            body["results"][0]["movie"]["dimensions"]["darkness"],
            70,
        )

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

    @patch("app.main.discover_tmdb_movies", return_value=[])
    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_auto_mode_routes_tmdb_only_genres_to_discovery(
        self,
        _configured,
        search_tmdb,
        discover,
    ):
        response = self.client.post(
            "/api/search",
            json={"query": "a nature documentary", "limit": 6},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"]["include_themes"], ["documentary"])
        search_tmdb.assert_not_called()
        discover.assert_called_once()

    def test_auto_mode_excludes_complete_romantic_comedy_phrase(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "not a romantic comedy", "limit": 6},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["include_themes"], [])
        self.assertEqual(body["intent"]["exclude_themes"], ["comedy", "romance"])
        self.assertEqual(body["intent"]["target_dimensions"]["romance"], 10)
        self.assertEqual(body["intent"]["target_dimensions"]["humor"], 10)
        self.assertTrue(body["results"])
        for result in body["results"]:
            movie = result["movie"]
            terms = {term.casefold() for term in movie["genres"] + movie["themes"]}
            self.assertTrue({"comedy", "romance"}.isdisjoint(terms))

    def test_auto_mode_excludes_complete_action_comedy_phrase(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "not an action comedy", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["include_themes"], [])
        self.assertEqual(body["intent"]["exclude_themes"], ["action", "comedy"])
        self.assertEqual(body["intent"]["target_dimensions"]["action"], 10)
        self.assertEqual(body["intent"]["target_dimensions"]["humor"], 10)
        self.assertTrue(body["results"])
        for result in body["results"]:
            movie = result["movie"]
            terms = {term.casefold() for term in movie["genres"] + movie["themes"]}
            self.assertTrue({"action", "comedy"}.isdisjoint(terms))

    def test_auto_mode_honors_comma_only_exclusion_lists(self):
        with patch("app.main.tmdb_is_configured", return_value=True), patch(
            "app.main.search_tmdb_movies"
        ) as search_tmdb:
            response = self.client.post(
                "/api/search",
                json={"query": "no horror, comedy, romance movies", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_not_called()
        body = response.json()
        self.assertEqual(body["intent"]["include_themes"], [])
        self.assertEqual(
            body["intent"]["exclude_themes"],
            ["comedy", "horror", "romance"],
        )
        self.assertTrue(body["results"])
        for result in body["results"]:
            movie = result["movie"]
            terms = {term.casefold() for term in movie["genres"] + movie["themes"]}
            self.assertTrue({"comedy", "horror", "romance"}.isdisjoint(terms))

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

    @patch("app.main.discover_tmdb_movies", return_value=[])
    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_auto_mode_routes_tmdb_country_aliases_to_discovery(
        self,
        _configured,
        search_tmdb,
        discover,
    ):
        response = self.client.post(
            "/api/search",
            json={"query": "Canadian mystery", "limit": 6},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"]["preferred_countries"], ["Canada"])
        search_tmdb.assert_not_called()
        discover.assert_called_once()

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

    def test_country_and_year_filters_do_not_leak_other_countries(self):
        response = self.client.post(
            "/api/search",
            json={"query": "Indian movies from the 1990s", "limit": 6},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["intent"]["preferred_countries"], ["India"])
        self.assertEqual(body["intent"]["min_year"], 1990)
        self.assertEqual(body["intent"]["max_year"], 1999)
        self.assertEqual(body["results"], [])

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_canonical_country_names_are_applied_by_the_api(self, _configured):
        french = self.client.post(
            "/api/search",
            json={"query": "movies from France", "limit": 6},
        )
        without_india = self.client.post(
            "/api/search",
            json={"query": "movies not from India", "limit": 20},
        )

        self.assertEqual(french.status_code, 200)
        self.assertEqual(french.json()["intent"]["preferred_countries"], ["France"])
        self.assertTrue(french.json()["results"])
        self.assertTrue(all(
            result["movie"]["country"] == "France"
            for result in french.json()["results"]
        ))

        self.assertEqual(without_india.status_code, 200)
        self.assertEqual(
            without_india.json()["intent"]["excluded_countries"],
            ["India"],
        )
        self.assertTrue(without_india.json()["results"])
        self.assertTrue(all(
            result["movie"]["country"] != "India"
            for result in without_india.json()["results"]
        ))

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
                json={"query": "movies from the 2010's", "limit": 20},
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

    def test_auto_mode_routes_decade_segments_to_vibe_search(self):
        for query, min_year, max_year in (
            ("movies from the early 2000s", 2000, 2003),
            ("movies from the mid-2010s", 2014, 2016),
            ("movies from the late 2010s", 2017, 2019),
        ):
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 20},
                )

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                body = response.json()
                self.assertEqual(body["intent"]["min_year"], min_year)
                self.assertEqual(body["intent"]["max_year"], max_year)
                self.assertTrue(body["results"])
                self.assertTrue(
                    all(
                        min_year <= result["movie"]["year"] <= max_year
                        for result in body["results"]
                    )
                )

    def test_auto_mode_routes_natural_release_years_to_vibe_search(self):
        for query in (
            "films from 2015",
            "movies 2015",
            "2015 films",
            "movies released 2015",
        ):
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 20},
                )

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                body = response.json()
                self.assertEqual(body["intent"]["min_year"], 2015)
                self.assertEqual(body["intent"]["max_year"], 2015)
                self.assertTrue(body["results"])
                self.assertTrue(
                    all(
                        result["movie"]["year"] == 2015
                        for result in body["results"]
                    )
                )

    def test_auto_mode_routes_natural_year_ranges_to_vibe_search(self):
        for query in (
            "movies from 2013 to 2016",
            "movies from 2013 through 2016",
            "movies from 2013-2016",
            "movies from 2013–2016",
            "movies from 2013-16",
            "movies from 2016-13",
            "movies 2013-2016",
            "2013 to 2016 films",
        ):
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 20},
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

    def test_auto_mode_routes_inclusive_year_boundaries_to_vibe_search(self):
        cases = (
            ("movies from 2015 onwards", 2015, None),
            ("movies 2015 or later", 2015, None),
            ("movies not before 2015", 2015, None),
            ("movies no earlier than 2015", 2015, None),
            ("movies released on or after 2015", 2015, None),
            ("movies at least 2015", 2015, None),
            ("movies no older than 2015", 2015, None),
            ("movies not older than 2015", 2015, None),
            ("movies up to 2015", None, 2015),
            ("2015 or earlier films", None, 2015),
            ("movies not after 2015", None, 2015),
            ("movies no later than 2015", None, 2015),
            ("movies released on or before 2015", None, 2015),
            ("movies at most 2015", None, 2015),
            ("movies no newer than 2015", None, 2015),
            ("movies not newer than 2015", None, 2015),
        )

        for query, min_year, max_year in cases:
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb:
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "limit": 20},
                )

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                body = response.json()
                self.assertEqual(body["intent"]["min_year"], min_year)
                self.assertEqual(body["intent"]["max_year"], max_year)
                self.assertTrue(body["results"])
                self.assertTrue(
                    all(
                        (min_year is None or result["movie"]["year"] >= min_year)
                        and (max_year is None or result["movie"]["year"] <= max_year)
                        for result in body["results"]
                    )
                )

    def test_auto_mode_uses_parsed_themes_to_avoid_title_search(self):
        for query, theme in (
            ("space movie", "space"),
            ("family movie", "family"),
            ("kids movies", "family"),
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

    def test_auto_mode_keeps_reference_recommendations_out_of_title_search(self):
        interstellar = next(movie for movie in MOVIES if movie.title == "Interstellar")
        cases = (
            ("Like Interstellar, but darker and less complicated", "darkness"),
            ("Interstellar but funnier", "humor"),
        )

        for query, adjusted_dimension in cases:
            with self.subTest(query=query), patch(
                "app.main.tmdb_is_configured", return_value=True
            ), patch("app.main.search_tmdb_movies") as search_tmdb, patch(
                "app.main.discover_tmdb_movies", return_value=[]
            ) as discover_tmdb:
                response = self.client.post("/api/search", json={"query": query})

                self.assertEqual(response.status_code, 200)
                search_tmdb.assert_not_called()
                discover_tmdb.assert_called_once()
                intent = response.json()["intent"]
                self.assertEqual(intent["reference_titles"], ["Interstellar"])
                self.assertNotEqual(
                    intent["target_dimensions"][adjusted_dimension],
                    interstellar.dimensions[adjusted_dimension],
                )

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
    def test_expanded_catalog_resolves_popular_titles_without_tmdb(self, _configured):
        cases = {
            "titanic": ("Titanic", "USA"),
            "shawshank redemption": ("The Shawshank Redemption", "USA"),
            "avatar": ("Avatar", "USA"),
            "avengers endgame": ("Avengers: Endgame", "USA"),
            "दंगल": ("Dangal", "India"),
            "pk": ("PK", "India"),
            "ಕಾಂತಾರ": ("Kantara", "India"),
            "올드보이": ("Oldboy", "South Korea"),
            "부산행": ("Train to Busan", "South Korea"),
            "君の名は。": ("Your Name", "Japan"),
            "amelie": ("Amélie", "France"),
            "cidade de deus": ("City of God", "Brazil"),
        }

        for query, (expected_title, expected_country) in cases.items():
            with self.subTest(query=query):
                response = self.client.post(
                    "/api/search",
                    json={"query": query, "mode": "title"},
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertTrue(body["results"])
                self.assertEqual(body["results"][0]["movie"]["title"], expected_title)
                self.assertEqual(body["results"][0]["movie"]["country"], expected_country)
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
    def test_2001_expands_offline_1960s_coverage(self, _configured):
        title_response = self.client.post(
            "/api/search",
            json={"query": "2001: A Space Odyssey"},
        )

        self.assertEqual(title_response.status_code, 200)
        title_body = title_response.json()
        movie = title_body["results"][0]["movie"]
        self.assertEqual(movie["title"], "2001: A Space Odyssey")
        self.assertEqual(movie["year"], 1968)
        self.assertIn("Science Fiction", movie["genres"])
        self.assertGreaterEqual(movie["dimensions"]["narrative_complexity"], 90)
        self.assertEqual(title_body["ai_provider"], "cinedna-title-catalog")

        period_response = self.client.post(
            "/api/search",
            json={"query": "sixties sci-fi movies", "limit": 20},
        )

        self.assertEqual(period_response.status_code, 200)
        period_body = period_response.json()
        self.assertTrue(period_body["results"])
        self.assertIn(
            "2001: A Space Odyssey",
            {result["movie"]["title"] for result in period_body["results"]},
        )
        self.assertTrue(
            all(
                1960 <= result["movie"]["year"] <= 1969
                for result in period_body["results"]
            )
        )

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_back_to_the_future_expands_offline_1980s_coverage(self, _configured):
        title_response = self.client.post(
            "/api/search",
            json={"query": "back to the future"},
        )

        self.assertEqual(title_response.status_code, 200)
        title_body = title_response.json()
        movie = title_body["results"][0]["movie"]
        self.assertEqual(movie["title"], "Back to the Future")
        self.assertEqual(movie["year"], 1985)
        self.assertIn("Science Fiction", movie["genres"])
        self.assertGreaterEqual(movie["dimensions"]["rewatchability"], 95)
        self.assertEqual(title_body["ai_provider"], "cinedna-title-catalog")

        period_response = self.client.post(
            "/api/search",
            json={"query": "eighties sci-fi movies", "limit": 20},
        )

        self.assertEqual(period_response.status_code, 200)
        period_body = period_response.json()
        self.assertTrue(period_body["results"])
        self.assertIn(
            "Back to the Future",
            {result["movie"]["title"] for result in period_body["results"]},
        )
        self.assertTrue(
            all(
                1980 <= result["movie"]["year"] <= 1989
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

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_recognizes_misspelled_title_with_vibe_word(self, _configured):
        response = self.client.post(
            "/api/search",
            json={"query": "dark knigt"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"][0]["movie"]["title"], "The Dark Knight")
        self.assertEqual(body["ai_provider"], "cinedna-title-catalog")
        self.assertEqual(body["intent"]["target_dimensions"], {})

    @patch("app.main.tmdb_is_configured", return_value=False)
    def test_auto_mode_recognizes_misspelled_multiword_titles(self, _configured):
        queries = {
            "avenger end game": "Avengers: Endgame",
            "shawshank redemtion": "The Shawshank Redemption",
            "spirited awy": "Spirited Away",
        }

        for query, expected_title in queries.items():
            with self.subTest(query=query):
                response = self.client.post(
                    "/api/search",
                    json={"query": query},
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["results"][0]["movie"]["title"], expected_title)
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

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_auto_mode_recognizes_title_cased_something_title(
        self,
        _configured,
        search_tmdb,
    ):
        search_tmdb.return_value = [
            MovieDNA(
                title="Something Borrowed",
                year=2011,
                country="USA",
                genres=["Comedy", "Romance"],
                themes=["friendship", "love"],
                dimensions={"humor": 70, "romance": 80},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="49022",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "Something Borrowed"},
        )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_called_once_with("Something Borrowed", 6)
        self.assertEqual(
            response.json()["results"][0]["movie"]["title"],
            "Something Borrowed",
        )

    @patch("app.main.search_tmdb_movies")
    @patch("app.main.tmdb_is_configured", return_value=True)
    def test_auto_mode_recognizes_lowercase_title_containing_vibe_word(
        self,
        _configured,
        search_tmdb,
    ):
        search_tmdb.return_value = [
            MovieDNA(
                title="Darkman",
                year=1990,
                country="USA",
                genres=["Action", "Science Fiction"],
                themes=["revenge"],
                dimensions={"action": 85, "darkness": 70},
                summary="A fictional TMDB-backed test movie.",
                source="tmdb",
                source_id="9556",
            )
        ]

        response = self.client.post(
            "/api/search",
            json={"query": "darkman"},
        )

        self.assertEqual(response.status_code, 200)
        search_tmdb.assert_called_once_with("darkman", 6)
        self.assertEqual(
            response.json()["results"][0]["movie"]["title"],
            "Darkman",
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
