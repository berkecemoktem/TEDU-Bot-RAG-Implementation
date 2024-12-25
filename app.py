import json
import os
import shutil
from dataclasses import dataclass
from functools import wraps
from typing import List, Dict, Optional, Tuple
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from pypdf import PdfReader

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://127.0.0.1:5500", "http://localhost:5500"],  # Allow frontend origin
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Origin"],
        "supports_credentials": True
    }
})


# Configure Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=GOOGLE_API_KEY)

# Get Gemini models
course_model = genai.GenerativeModel('gemini-pro')
assistant_model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Intent classification system prompt
INTENT_SYSTEM_PROMPT = """You are an intent classifier for the TED University assistant system.
Your task is to classify user queries into two categories:
1. "course_suggestion" - for queries about course recommendations, subject interests, or class selection
2. "tedu_assistant" - for queries about university life, regulations, facilities, or general information

Respond only with the intent category, nothing else."""


class IntentManager:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')

    def classify_intent(self, query: str) -> str:
        """Classify the user's intent based on their query."""
        prompt = f"{INTENT_SYSTEM_PROMPT}\n\nQuery: {query}"
        response = self.model.generate_content(prompt)
        intent = response.text.strip().lower()

        if intent not in ["course_suggestion", "tedu_assistant"]:
            return "tedu_assistant"
        return intent


@dataclass
class Course:
    code: str
    name: str
    description: str
    prerequisites: List[str]
    credits: int
    department: str
    lecturer: str


@dataclass
class UserPreference:
    interests: str
    academic_level: str = "undergraduate"
    department: str = None
    preferred_credits: int = None


class DocumentProcessor:
    @staticmethod
    def convert_pdf_to_text(pdf_path: str) -> List[str]:
        """Convert PDF file to text chunks."""
        reader = PdfReader(pdf_path)
        pdf_texts = [p.extract_text().strip() for p in reader.pages]
        pdf_texts = [text for text in pdf_texts if text]
        logger.info(f"Document: {pdf_path} chunk size: {len(pdf_texts)}")
        return pdf_texts

    @staticmethod
    def split_text_to_chunks(pdf_texts: List[str], chunk_size: int = 1500, chunk_overlap: int = 0) -> List[str]:
        """Split text into chunks using character-based splitting."""
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = splitter.split_text('\n\n'.join(pdf_texts))
        logger.info(f"Total chunks (char-based): {len(chunks)}")
        return chunks

    @staticmethod
    def convert_chunks_to_tokens(chunks: List[str], model_name: str, tokens_per_chunk: int = 128) -> List[str]:
        """Convert text chunks to token-based chunks."""
        token_splitter = SentenceTransformersTokenTextSplitter(
            chunk_overlap=0,
            model_name=model_name,
            tokens_per_chunk=tokens_per_chunk
        )
        token_chunks = []
        for chunk in chunks:
            token_chunks.extend(token_splitter.split_text(chunk))
        logger.info(f"Total chunks (token-based): {len(token_chunks)}")
        return token_chunks


class ChromaDBManager:
    def __init__(self, path: str, collection_name: str = "tedu_docs"):
        self.path = path
        self.collection_name = collection_name
        self.embedding_model = "distiluse-base-multilingual-cased-v1"
        self.client = PersistentClient(
            path=path,
            settings=Settings(),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE
        )
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )
        self.collection = self.client.get_or_create_collection(
            collection_name,
            embedding_function=self.embedding_function
        )

    def process_and_add_documents(self, pdf_dir: str):
        """Process and add all PDF documents from a directory to the collection."""
        processor = DocumentProcessor()
        current_id = self.collection.count()

        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_dir, filename)
                logger.info(f"Processing document: {pdf_path}")

                # Convert PDF to text and chunk it
                pdf_texts = processor.convert_pdf_to_text(pdf_path)
                char_chunks = processor.split_text_to_chunks(pdf_texts)
                token_chunks = processor.convert_chunks_to_tokens(char_chunks, self.embedding_model)

                # Create metadata
                ids = [str(i + current_id) for i in range(len(token_chunks))]
                metadatas = [{
                    'document': pdf_path,
                    'category': 'LIFE IN TEDU'
                } for _ in range(len(token_chunks))]

                # Add to collection
                self.collection.add(
                    ids=ids,
                    metadatas=metadatas,
                    documents=token_chunks
                )
                current_id += len(token_chunks)
                logger.info(f"Added document: {pdf_path}, collection size: {self.collection.count()}")

    def query_documents(self, query: str, n_results: int = 5, distance_threshold: float = 1.15) -> Dict:
        """Query the document collection and filter by distance threshold."""
        results = self.collection.query(
            query_texts=[query],
            include=["documents", "metadatas", "distances"],
            n_results=n_results
        )

        # Filter results by distance threshold
        filtered_results = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        for i, distance in enumerate(results["distances"][0]):
            if distance <= distance_threshold:
                filtered_results["documents"][0].append(results["documents"][0][i])
                filtered_results["metadatas"][0].append(results["metadatas"][0][i])
                filtered_results["distances"][0].append(distance)

        return filtered_results


class CourseRecommender:
    def __init__(self, json_path: str):
        self.courses = self._load_courses_from_json(json_path)

    def _load_courses_from_json(self, json_path) -> List[Course]:
        with open(json_path, 'r') as file:
            courses_data = json.load(file)
            return [Course(
                code=c['code'],
                name=c['name'],
                description=c['description'],
                prerequisites=c.get('pre-requisite', '').split(', ') if c.get('pre-requisite') else [],
                credits=c['credit'],
                department=c['department'],
                lecturer=c['lecturer']
            ) for c in courses_data]

    def get_recommendation_count(self, temperature: float) -> Tuple[int, str]:
        """Determines the number of recommendations based on temperature."""
        if temperature < 0.0 or temperature > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

        if 0.0 <= temperature <= 0.2:
            return (2, "Low temperature: highly focused recommendations")
        elif 0.2 < temperature <= 0.5:
            return (4, "Moderate temperature: balanced recommendations")
        else:
            return (5, "Higher temperature: diverse recommendations")

    def get_recommendations(self, user_pref: UserPreference, temperature: float = 0.7) -> List[Dict]:
        rec_count, rec_explanation = self.get_recommendation_count(temperature)

        courses_info = "\n".join([
            f"Code: {c.code}\nName: {c.name}\nDescription: {c.description}\n"
            f"Credits: {c.credits}\nDepartment: {c.department}\n---"
            for c in self.courses
        ])

        prompt = f"""Based on the user's preferences, recommend university courses. Consider the following details:
        - Interests: {user_pref.interests}
        - Academic Level: {user_pref.academic_level} (e.g., undergraduate, graduate)
        - Department: {user_pref.department or 'Any'}
        - Preferred Credits: {user_pref.preferred_credits or 'Any'}

        Temperature Context: {rec_explanation} (guides recommendation style)
        Expected Number of Recommendations: {rec_count}

        Available Courses:
        {courses_info}

        Generate exactly {rec_count} recommendations, each with the following format:
        [
            {{
                "code": "COURSE_CODE",
                "name": "COURSE_NAME",
                "explanation": "Why this course fits the user's preferences"
            }}
        ]
        """

        response = course_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature
            )
        )
        recommendations = eval(response.text)

        return [{
            **next((vars(c) for c in self.courses if c.code == rec['code']), {}),
            "relevance_explanation": rec['explanation']
        } for rec in recommendations]


class TEDUAssistant:
    def __init__(self, chroma_manager: ChromaDBManager):
        self.chroma = chroma_manager
        system_prompt = """You are a digital assistant for TED University. Your role is to provide accurate, concise, and context-relevant answers to user queries. 
        Guidelines:
        1. Answer strictly based on the provided context. 
        2. If the context does not include the requested information, respond with: "I don't have enough information to answer that question."
        3. Ensure your answers are both comprehensive and concise.
        """
        self.chat = assistant_model.start_chat(history=[])

    def get_response(self, query: str) -> str:
        results = self.chroma.query_documents(query)
        if not results['documents'][0]:
            return "I don't have enough information to answer that question."

        context = f"Context:\n" + "\n".join(results['documents'][0])
        response = self.chat.send_message(f"Question: {query}\n{context}")
        return response.text


def initialize_system(pdf_dir: str, courses_json: str, chroma_db_path: str):
    """Initialize the entire system with all components."""
    # Create ChromaDB manager and process documents
    chroma_manager = ChromaDBManager(chroma_db_path)
    if os.path.exists(pdf_dir):
        chroma_manager.process_and_add_documents(pdf_dir)

    # Initialize other components
    intent_manager = IntentManager()
    course_recommender = CourseRecommender(courses_json)
    tedu_assistant = TEDUAssistant(chroma_manager)

    return intent_manager, course_recommender, tedu_assistant


# Initialize components
PDF_DIR = "pdfs"  # Directory containing PDF files
COURSES_JSON = "courses.json"  # Path to courses JSON file
CHROMA_DB_PATH = "chroma_db"  # Path for ChromaDB storage

intent_manager, course_recommender, tedu_assistant = initialize_system(
    PDF_DIR, COURSES_JSON, CHROMA_DB_PATH
)

# Authentication middleware
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        logger.info(f"Authorization Header: {auth_header}")
        if not auth_header:
            logger.error("No authorization header provided")
            return jsonify({"error": "No authorization header"}), 403
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(" ")[1]
            logger.info(f"Token extracted: {token}")
        except Exception as e:
            logger.error(f"Invalid authorization header: {e}")
            return jsonify({"error": "Invalid authorization header"}), 403
        return f(*args, **kwargs)
    return decorated


# Chat API endpoint
@require_auth
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query"}), 400

        # Classify intent
        intent = intent_manager.classify_intent(data['query'])

        if intent == "course_suggestion":
            # Handle course suggestion
            temperature = float(data.get('temperature', 0.7))
            if temperature < 0.0 or temperature > 2.0:
                return jsonify({"error": "Temperature must be between 0.0 and 2.0"}), 400

            user_pref = UserPreference(
                interests=data['query'],
                academic_level=data.get('academic_level', 'undergraduate'),
                department=data.get('department'),
                preferred_credits=data.get('preferred_credits')
            )
            recommendations = course_recommender.get_recommendations(user_pref, temperature)
            return jsonify({
                "intent": intent,
                "temperature": temperature,
                "recommendations": recommendations
            })
        else:
            # Handle general assistant
            response = tedu_assistant.get_response(data['query'])
            return jsonify({
                "intent": intent,
                "response": response
            })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)