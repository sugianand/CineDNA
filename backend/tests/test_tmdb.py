import unittest

from app.services.tmdb import _from_tmdb


class TMDBProfileTests(unittest.TestCase):
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
