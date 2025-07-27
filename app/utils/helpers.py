# app/utils/helpers.py

import json
from typing import List
import os
import uuid

from app.core.models import Question

# Get the absolute path to the static directory
# This makes it robust, regardless of where the script is run from.
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
QUESTIONS_FILE = os.path.join(STATIC_DIR, 'questions.json')

def load_questions() -> List[Question]:
    """
    Loads interview questions from the JSON file and validates them
    using the Question Pydantic model.
    """
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            questions_data = json.load(f)
        
        # Validate each question object against the Pydantic model
        return [Question(**q_data) for q_data in questions_data]
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as e:
        print(f"Error loading questions: {e}")
        return []

def generate_session_id() -> str:
    """Generates a new unique session ID."""
    return str(uuid.uuid4())