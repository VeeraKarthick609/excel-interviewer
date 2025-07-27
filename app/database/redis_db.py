# app/database/redis_db.py

import redis
import json
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.models import Question, Evaluation

# --- Initialize Redis Connection ---
# We use connection pooling for efficiency.
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=0, # Default Redis database
    decode_responses=True # Decode responses from bytes to utf-8 strings
)

def get_redis_connection():
    """Returns an active Redis connection from the pool."""
    return redis.Redis(connection_pool=redis_pool)


class SessionManager:
    """
    Manages user interview sessions using Redis.
    """
    def __init__(self, session_id: str):
        self.redis_conn = get_redis_connection()
        self.session_id = session_id
        self.session_key = f"interview_session:{self.session_id}"

    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serializes session data to a JSON string."""
        # Pydantic models need to be converted to dicts for JSON serialization
        def default_serializer(o):
            if hasattr(o, 'model_dump'):
                return o.model_dump()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
        
        return json.dumps(data, default=default_serializer)

    def _deserialize_data(self, json_str: str) -> Dict[str, Any]:
        """Deserializes JSON string back to a Python dictionary."""
        data = json.loads(json_str)
        # Re-hydrate Pydantic models from dicts
        if 'questions' in data:
            data['questions'] = [Question(**q) for q in data['questions']]
        if 'evaluations' in data:
            data['evaluations'] = [Evaluation(**e) for e in data['evaluations']]
        return data

    def get_session_state(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the entire session state from Redis.
        Returns None if the session does not exist.
        """
        stored_state = self.redis_conn.get(self.session_key)
        if stored_state:
            return self._deserialize_data(stored_state)
        return None

    def save_session_state(self, state: Dict[str, Any]):
        """
        Saves the entire session state to Redis.
        The state is set to expire after 24 hours.
        """
        serialized_state = self._serialize_data(state)
        self.redis_conn.set(self.session_key, serialized_state, ex=86400) # 24-hour expiry

    def create_new_session(self, questions: List[Question]) -> Dict[str, Any]:
        """
        Initializes a new session with the provided questions.
        """
        initial_state = {
            "session_id": self.session_id,
            "current_question_index": 0,
            "questions": questions,
            "user_answers": [],
            "evaluations": [],
            "interview_started": False,
            "interview_finished": False
        }
        self.save_session_state(initial_state)
        return initial_state