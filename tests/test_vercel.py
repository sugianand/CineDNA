"""Smoke-test the serverless entrypoint from the repository root."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.index import app


class VercelEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_vercel_dependencies_are_self_contained_and_match_backend(self):
        root = Path(__file__).resolve().parents[1]

        def requirements(path):
            return [
                line.strip() for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]

        deployed = requirements(root / "requirements.txt")
        self.assertFalse(any(line.startswith("-") for line in deployed))
        self.assertEqual(deployed, requirements(root / "backend/requirements.txt"))

    def test_health_revision_uses_vercel_then_render_then_local(self):
        cases = [
            ({"VERCEL_GIT_COMMIT_SHA": "vercel-sha", "RENDER_GIT_COMMIT": "render-sha"}, "vercel-sha"),
            ({"RENDER_GIT_COMMIT": "render-sha"}, "render-sha"),
            ({}, "local"),
        ]
        for env, revision in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                response = self.client.get("/api/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["revision"], revision)

    @patch.dict(os.environ, {"TMDB_READ_TOKEN": ""})
    def test_movie_query_and_search_body_reach_existing_routes(self):
        response = self.client.get("/api/movie", params={"title": "Interstellar"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Interstellar")
        response = self.client.post(
            "/api/search", json={"query": "Interstellar", "mode": "title"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["movie"]["title"], "Interstellar")

    def test_docs_and_schema_are_available(self):
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/openapi.json", response.text)
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/search", response.json()["paths"])

    def test_unknown_api_path_does_not_return_spa(self):
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not Found"})
