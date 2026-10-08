import unittest

from fastapi.testclient import TestClient

from app.main import app


class CineDNAAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertGreater(response.json()["movies"], 0)

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


if __name__ == "__main__":
    unittest.main()
