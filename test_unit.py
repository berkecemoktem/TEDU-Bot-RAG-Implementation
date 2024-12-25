import unittest
from unittest.mock import patch, MagicMock
from app import app, IntentManager, CourseRecommender, TEDUAssistant, UserPreference

class TestBackend(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch("app.IntentManager.classify_intent")
    def test_chat_course_suggestion(self, mock_classify_intent):
        mock_classify_intent.return_value = "course_suggestion"

        mock_recommendations = [
            {
                "code": "CMPE101",
                "name": "Intro to Programming",
                "description": "Learn the basics of programming.",
                "credits": 3,
                "department": "Computer Science",
                "lecturer": "Dr. Smith",
                "prerequisites": [],
                "relevance_explanation": "Great course for beginners."
            }
        ]
        with patch("app.CourseRecommender.get_recommendations", return_value=mock_recommendations):
            response = self.app.post('/api/chat', json={
                "query": "What courses should I take?",
                "temperature": 0.7,
                "academic_level": "undergraduate"
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn("recommendations", response.json)

    @patch("app.IntentManager.classify_intent")
    def test_chat_tedu_assistant(self, mock_classify_intent):
        mock_classify_intent.return_value = "tedu_assistant"

        with patch("app.TEDUAssistant.get_response", return_value="Welcome to TEDU!") as mock_get_response:
            response = self.app.post('/api/chat', json={
                "query": "Tell me about TEDU."
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn("response", response.json)
            self.assertEqual(response.json["response"], "Welcome to TEDU!")
            mock_get_response.assert_called_once()

    def test_missing_query(self):
        response = self.app.post('/api/chat', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)
        self.assertEqual(response.json["error"], "Missing query")

    def test_invalid_temperature(self):
        response = self.app.post('/api/chat', json={
            "query": "What courses should I take?",
            "temperature": 2.5
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)
        self.assertEqual(response.json["error"], "Temperature must be between 0.0 and 2.0")

    def test_get_recommendation_count(self):
        recommender = CourseRecommender(json_path="test_courses.json")

        # Test low temperature
        count, explanation = recommender.get_recommendation_count(0.1)
        self.assertEqual(count, 2)
        self.assertEqual(explanation, "Low temperature: highly focused recommendations")

        # Test moderate temperature
        count, explanation = recommender.get_recommendation_count(0.4)
        self.assertEqual(count, 4)
        self.assertEqual(explanation, "Moderate temperature: balanced recommendations")

        # Test high temperature
        count, explanation = recommender.get_recommendation_count(0.9)
        self.assertEqual(count, 5)
        self.assertEqual(explanation, "Higher temperature: diverse recommendations")

        # Test invalid temperature
        with self.assertRaises(ValueError):
            recommender.get_recommendation_count(2.5)

if __name__ == "__main__":
    unittest.main()
