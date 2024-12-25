import unittest
from unittest.mock import patch, MagicMock
from app import app, TEDUAssistant, CourseRecommender, ChromaDBManager, UserPreference


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch("app.genai.GenerativeModel.generate_content")
    def test_get_recommendations_integration(self, mock_generate_content):
        recommender = CourseRecommender(json_path="test_courses.json")

        mock_generate_content.return_value.text = '[{"code": "CMPE 113", "name": "Intro to Programming", "explanation": "Great course for beginners."}]'

        user_pref = UserPreference(interests="Programming", academic_level="undergraduate")
        recommendations = recommender.get_recommendations(user_pref, temperature=0.7)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["code"], "CMPE 113")
        self.assertEqual(recommendations[0]["name"], "Fundamentals of Programming I")
        self.assertEqual(recommendations[0]["relevance_explanation"], "Great course for beginners.")

    @patch("app.ChromaDBManager.query_documents")
    @patch("app.assistant_model.start_chat")
    def test_get_response_integration(self, mock_start_chat, mock_query_documents):
        mock_query_documents.return_value = {
            "documents": [["Mocked document 1", "Mocked document 2"]],
            "metadatas": [[]],
            "distances": [[]]
        }

        mock_chat_instance = MagicMock()
        mock_chat_instance.send_message.return_value.text = "Mocked response"
        mock_start_chat.return_value = mock_chat_instance

        chroma_manager = MagicMock()
        assistant = TEDUAssistant(chroma_manager)
        response = assistant.get_response("Tell me about TEDU")

        self.assertEqual(response, "Mocked response")
