from application.models import User, Course, Lecture, Registration, AIUsage, GlobalAIUsage
from application import db, api, faiss_cache
from flask import jsonify, request, render_template, make_response
from flask_restful import Resource, fields, marshal
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
import secrets
from dotenv import load_dotenv
import os
import datetime
import json
import pickle
try:
    import faiss
except ImportError:
    faiss = None

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    HuggingFaceEmbeddings = None
    EMBEDDINGS_AVAILABLE = False
    print("Warning: langchain_huggingface not available. Mock question embeddings disabled.")

# ---------------------------------------------------------------------------
# Load environment variables BEFORE initialising the Gemini client
# ---------------------------------------------------------------------------
base_dir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(base_dir, '..', '..', '.env')
load_dotenv(env_path)

# Explicitly push the key into os.environ so google-genai picks it up
gemini_api_key = os.getenv("GEMINI_API_KEY", "")
os.environ["GEMINI_API_KEY"] = gemini_api_key

DAILY_CHAT_LIMIT   = int(os.getenv("DAILY_CHAT_LIMIT",   10))
DAILY_MOCK_LIMIT   = int(os.getenv("DAILY_MOCK_LIMIT",    3))
DAILY_GLOBAL_LIMIT = int(os.getenv("DAILY_GLOBAL_LIMIT", 20))

# ---------------------------------------------------------------------------
# New google-genai SDK
# ---------------------------------------------------------------------------
from google import genai
from google.genai import types as genai_types

# Single shared client — reads GEMINI_API_KEY from env automatically
gemini_client = genai.Client()
GEMINI_MODEL  = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Datastore (avoid circular import)
# ---------------------------------------------------------------------------
from application import create_datastore
datastore = create_datastore()

# ---------------------------------------------------------------------------
# Rate Limiting Helpers
# ---------------------------------------------------------------------------

def _get_today():
    return datetime.date.today()


def check_global_budget():
    """Returns (allowed: bool, used: int). Increments global counter if allowed."""
    today = _get_today()
    row = GlobalAIUsage.query.filter_by(date=today).first()
    if row is None:
        row = GlobalAIUsage(date=today, count=0)
        db.session.add(row)

    if row.count >= DAILY_GLOBAL_LIMIT:
        return False, row.count

    row.count += 1
    db.session.commit()
    return True, row.count


def check_user_limit(user_id, feature, limit):
    """Returns (allowed: bool, used: int, remaining: int). Increments per-user counter if allowed."""
    today = _get_today()
    row = AIUsage.query.filter_by(user_id=user_id, feature=feature, date=today).first()
    if row is None:
        row = AIUsage(user_id=user_id, feature=feature, date=today, count=0)
        db.session.add(row)

    if row.count >= limit:
        return False, row.count, 0

    row.count += 1
    db.session.commit()
    return True, row.count, limit - row.count


def rate_limit_response(feature, user_limit, used):
    label = "chat messages" if feature == "chat" else "mock question sets"
    return make_response(jsonify({
        "error": f"Daily limit reached. You can use {user_limit} {label} per day. Try again tomorrow.",
        "code": 429,
        "feature": feature,
        "limit": user_limit,
        "used": used,
        "resets": "tomorrow"
    }), 429)


def global_limit_response(used):
    return make_response(jsonify({
        "error": "The platform's daily AI request budget has been reached. Please try again tomorrow.",
        "code": 429,
        "global_limit": DAILY_GLOBAL_LIMIT,
        "global_used": used,
        "resets": "tomorrow"
    }), 429)


# ===========================================================================
# HOME
# ===========================================================================

class Home(Resource):
    def get(self):
        html = render_template('index.html')
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html'
        return response


# ===========================================================================
# USER PROFILE
# ===========================================================================

class User(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return make_response(jsonify({'error': 'Request body required', 'code': 400}), 400)

            name     = data.get('name')
            email    = data.get('email')
            password = data.get('password')

            if not (name and email and password):
                return make_response(jsonify({'error': 'Name, Email and Password are required', 'code': 400}), 400)

            user = datastore.find_user(email=email)
            if user:
                return make_response(jsonify({'error': 'Email already exists', 'code': 400}), 400)

            user = datastore.create_user(
                name=name, email=email,
                password=generate_password_hash(password), roles=['user']
            )
            db.session.commit()

            available_courses = Course.query.with_entities(Course.id).all()
            registrations = [Registration(user_id=user.id, course_id=c.id) for c in available_courses]
            db.session.bulk_save_objects(registrations)
            db.session.commit()

            return make_response(jsonify({'message': 'User registered successfully', 'code': 201}), 201)

        except Exception as e:
            return make_response(jsonify({'error': str(e), 'code': 500}), 500)

    def put(self, mode):
        try:
            data = request.get_json()
            if not data:
                return make_response(jsonify({'error': 'Request body required', 'code': 400}), 400)

            if mode == 'profile':
                user_id   = data.get('userId')
                new_name  = data.get('name')
                new_email = data.get('email')

                if not user_id:
                    return make_response(jsonify({'error': 'User ID is required', 'code': 400}), 400)

                user = datastore.find_user(id=user_id)
                if not user:
                    return make_response(jsonify({'error': 'User not found', 'code': 404}), 404)

                if new_name:
                    user.name = new_name
                if new_email:
                    existing = datastore.find_user(email=new_email)
                    if existing and existing.id != user_id:
                        return make_response(jsonify({'error': 'Email already exists', 'code': 400}), 400)
                    user.email = new_email

                db.session.commit()
                return make_response(jsonify({'message': 'User profile updated successfully', 'code': 200}), 200)

            elif mode == 'password':
                user_id      = data.get('userId')
                old_password = data.get('oldPassword')
                new_password = data.get('newPassword')

                if not (user_id and old_password and new_password):
                    return make_response(jsonify({'error': 'All fields are required', 'code': 400}), 400)

                user = datastore.find_user(id=user_id)
                if not user:
                    return make_response(jsonify({'error': 'User not found', 'code': 404}), 404)
                if not check_password_hash(user.password, old_password):
                    return make_response(jsonify({'error': 'Incorrect old password', 'code': 400}), 400)

                user.password = generate_password_hash(new_password)
                db.session.commit()
                return make_response(jsonify({'message': 'Password changed successfully', 'code': 200}), 200)

        except Exception as e:
            return make_response(jsonify({'error': str(e), 'code': 500}), 500)


# ===========================================================================
# LOGIN
# ===========================================================================

user_fields = {
    "id":    fields.Integer,
    "email": fields.String,
    "name":  fields.String,
}

class Login(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return make_response(jsonify({'error': 'Request body required', 'code': 400}), 400)

            email    = data.get('email')
            password = data.get('password')

            if not (email and password):
                return make_response(jsonify({'error': 'Email and Password are required', 'code': 400}), 400)

            user = datastore.find_user(email=email)
            if not user or not check_password_hash(user.password, password):
                return make_response(jsonify({'error': 'Invalid Credentials', 'code': 400}), 400)

            marshalled = marshal(user, user_fields)
            return make_response(jsonify(**marshalled, **{'token': secrets.token_urlsafe(32), 'code': 200}), 200)

        except Exception as e:
            return make_response(jsonify({'error': 'Something went wrong', 'code': 500, 'message': str(e)}), 500)


# ===========================================================================
# USER DASHBOARD
# ===========================================================================

class UserDashboard(Resource):
    def get(self):
        html = render_template('dashboard.html')
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html'
        return response


# ===========================================================================
# REGISTERED COURSES
# ===========================================================================

class UserCurrentCourses(Resource):
    def get(self, user_id):
        try:
            subq    = select(Registration.course_id).where(Registration.user_id == user_id)
            courses = Course.query.with_entities(Course.id, Course.name).filter(Course.id.in_(subq)).all()
            return make_response(jsonify([{"id": c[0], "name": c[1]} for c in courses]), 200)
        except Exception as e:
            return make_response(jsonify({'error': 'Something went wrong', 'code': 500, 'message': str(e)}), 500)


# ===========================================================================
# LECTURES
# ===========================================================================

class GetAllLectures(Resource):
    def get(self, id):
        try:
            lectures = Lecture.query.filter_by(course_id=id).all()
            data = [
                {
                    'lecturenumber': l.lectureNumber,
                    'title':         l.title,
                    'link':          l.link,
                    'weeknumber':    l.weekNumber,
                }
                for l in lectures
            ]
            return make_response(jsonify(data), 200)
        except Exception as e:
            return make_response(jsonify({'error': 'Something went wrong', 'code': 500, 'message': str(e)}), 500)


# ===========================================================================
# MOCK QUESTIONS  (RAG + Gemini)
# ===========================================================================

MCQ_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "question_statement": {"type": "string"},
            "option_a":           {"type": "string"},
            "option_b":           {"type": "string"},
            "option_c":           {"type": "string"},
            "option_d":           {"type": "string"},
            "correct_answer":     {"type": "string"},
        },
        "required": [
            "question_statement", "option_a", "option_b",
            "option_c", "option_d", "correct_answer"
        ],
    },
}


class MockQuestions(Resource):
    def __init__(self):
        if EMBEDDINGS_AVAILABLE and HuggingFaceEmbeddings is not None:
            self.embedding_function = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        else:
            self.embedding_function = None

    def _retrieve_context(self, week):
        faiss_vector_store = faiss_cache.get(week)
        if not faiss_vector_store:
            return "No data available for this week."
        return "\n".join(
            doc.page_content for doc in faiss_vector_store.docstore._dict.values()
        )

    def _generate_rag_prompt(self, context, num_questions):
        return f"""
You are Lumi, an AI assistant for the IIT Madras Business Analytics course.
Generate {num_questions} different, random multiple-choice questions (MCQ) from the context below.

Format output as a JSON list where each MCQ has:
- "question_statement": the question text
- "option_a", "option_b", "option_c", "option_d": the answer choices
- "correct_answer": the correct option letter ("A", "B", "C", or "D")

CONTEXT: '{context}'
"""

    def generate(self, week, num_questions):
        if not EMBEDDINGS_AVAILABLE:
            return {"error": "AI features are not available in this demo deployment."}
        context = self._retrieve_context(week)
        if context == "No data available for this week.":
            return context

        prompt = self._generate_rag_prompt(context, num_questions)
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MCQ_SCHEMA,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}

    def get(self):
        try:
            week          = request.args.get('week',          default=1, type=int)
            num_questions = request.args.get('num_questions', default=3, type=int)
            user_id       = request.args.get('user_id',       default=None, type=int)

            # ── Per-user rate limit ───────────────────────────────────────
            if user_id is not None:
                allowed, used, _ = check_user_limit(user_id, 'mock', DAILY_MOCK_LIMIT)
                if not allowed:
                    return rate_limit_response('mock', DAILY_MOCK_LIMIT, used)

            # ── Global budget ─────────────────────────────────────────────
            global_ok, global_used = check_global_budget()
            if not global_ok:
                return global_limit_response(global_used)

            result = self.generate(week, num_questions)
            return make_response(jsonify({"mcqs": result, "code": 200}), 200)

        except Exception as e:
            return make_response(jsonify({"error": str(e), "code": 500}), 500)


# ===========================================================================
# CHAT SUPPORT  (Lumi)
# ===========================================================================

class ChatSupport(Resource):
    def post(self):
        try:
            data        = request.get_json()
            message     = data.get("message")
            chat_history = data.get("chat_history", [])
            user_id     = data.get("userId")

            if not message:
                return make_response(jsonify({"error": "Message is required", "code": 400}), 400)

            # ── Per-user rate limit ───────────────────────────────────────
            if user_id is not None:
                allowed, used, _ = check_user_limit(user_id, 'chat', DAILY_CHAT_LIMIT)
                if not allowed:
                    return rate_limit_response('chat', DAILY_CHAT_LIMIT, used)

            # ── Global budget ─────────────────────────────────────────────
            global_ok, global_used = check_global_budget()
            if not global_ok:
                return global_limit_response(global_used)

            history = "\n".join(
                f"{item['role']}: {item['content']}" for item in chat_history
            )

            prompt = f"""
You are Lumi, an intelligent and ethical educational assistant and learning companion.
Your primary goal is to help students **understand concepts deeply** by guiding them to
recall, reason, and connect ideas — not by directly giving answers.

Core behaviour guidelines:
- Do NOT directly provide answers to assignments, quizzes, or exams.
- Instead, ask guiding questions that lead students to think critically.
- When a user asks a factual or problem-based question, first respond with a reflection
  prompt, then if needed gently explain the underlying idea.
- Keep responses concise (≤ 5 sentences unless a deeper explanation is essential).
- Use real-world or business-oriented examples when illustrating abstract ideas.
- Maintain a warm, supportive, encouraging tone — patient tutor, not a lecturer.
- Focus only on: Business Analytics, Software Engineering, Software Testing, Deep Learning.
- Uphold academic integrity and promote independent learning.

{history}
User: {message}
Assistant:"""

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )

            if response.text:
                reply = response.text.strip()
            else:
                reply = "I'm sorry, I couldn't generate a proper response right now."

            return make_response(jsonify({"response": reply, "code": 200}), 200)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return make_response(jsonify({"error": str(e), "code": 500}), 500)


# ===========================================================================
# AI USAGE STATUS
# ===========================================================================

class AIUsageStatus(Resource):
    def get(self, user_id):
        try:
            today = datetime.date.today()

            chat_row   = AIUsage.query.filter_by(user_id=user_id, feature='chat', date=today).first()
            mock_row   = AIUsage.query.filter_by(user_id=user_id, feature='mock', date=today).first()
            global_row = GlobalAIUsage.query.filter_by(date=today).first()

            chat_used   = chat_row.count   if chat_row   else 0
            mock_used   = mock_row.count   if mock_row   else 0
            global_used = global_row.count if global_row else 0

            return make_response(jsonify({
                "chat": {
                    "used":      chat_used,
                    "limit":     DAILY_CHAT_LIMIT,
                    "remaining": max(0, DAILY_CHAT_LIMIT - chat_used),
                },
                "mock": {
                    "used":      mock_used,
                    "limit":     DAILY_MOCK_LIMIT,
                    "remaining": max(0, DAILY_MOCK_LIMIT - mock_used),
                },
                "global": {
                    "used":      global_used,
                    "limit":     DAILY_GLOBAL_LIMIT,
                    "remaining": max(0, DAILY_GLOBAL_LIMIT - global_used),
                },
                "code": 200,
            }), 200)

        except Exception as e:
            return make_response(jsonify({'error': str(e), 'code': 500}), 500)


# ===========================================================================
# LOGOUT
# ===========================================================================

class Logout(Resource):
    def post(self):
        try:
            return make_response(jsonify({"message": "Successfully logged out", "code": 200}), 200)
        except Exception as e:
            return make_response(jsonify({"error": str(e), "code": 500}), 500)


# ===========================================================================
# ROUTES
# ===========================================================================

api.add_resource(Home,               "/")
api.add_resource(User,               "/user", "/user/<string:mode>")
api.add_resource(Login,              "/login")
api.add_resource(UserCurrentCourses, "/user/<int:user_id>/currentcourses")
api.add_resource(GetAllLectures,     "/get_all_lectures/<int:id>")
api.add_resource(MockQuestions,      "/mock")
api.add_resource(ChatSupport,        "/chat")
api.add_resource(AIUsageStatus,      "/user/<int:user_id>/ai-usage")
api.add_resource(Logout,             "/logout")