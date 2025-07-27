# app/main.py

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# --- Import Project Modules ---
# These are the components we've built in the previous steps.
from core.config import settings
from core.models import Question
from core.agent import excel_agent
from database.redis_db import SessionManager
from database.postgres_db import init_db, save_interview_report
from utils.helpers import load_questions # We'll create this helper next

# --- Page Configuration ---
st.set_page_config(
    page_title=settings.APP_TITLE,
    page_icon="🤖",
    layout="wide"
)

# --- Database Initialization ---
# This runs once when the app starts.
@st.cache_resource
def initialize_database():
    init_db()
    
initialize_database()

# --- Main Application Logic ---
def main():
    st.title(f"🤖 {settings.APP_TITLE}")
    st.write("Welcome! This is an automated interview to assess your Excel skills. Please complete the tasks as instructed.")

    # --- Session Management ---
    # Use session_id from URL query params if it exists, otherwise generate a new one.
    query_params = st.query_params
    session_id = query_params.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())
        st.query_params["session_id"] = session_id
    
    session_manager = SessionManager(session_id)
    session_state = session_manager.get_session_state()

    # --- Interview Flow ---
    # 1. Initialization: If no session exists, show the start screen.
    if session_state is None:
        start_screen(session_manager)
        return

    # 2. Completion: If the interview is marked as finished, show the report.
    if session_state.get("interview_finished"):
        final_report_screen(session_state)
        return

    # 3. In Progress: If started but not finished, show the current question.
    if session_state.get("interview_started"):
        interview_screen(session_manager, session_state)


def start_screen(session_manager: SessionManager):
    """Displays the initial screen and the 'Start Interview' button."""
    st.subheader("Instructions")
    st.write(
        """
        - You will be presented with a series of data manipulation tasks.
        - For each task, you'll see a data table. You can edit it directly.
        - After performing the task, you must provide the primary Excel formula you used.
        - The interview will begin once you click the 'Start' button below.
        """
    )
    if st.button("Start Interview", type="primary"):
        all_questions = load_questions() # Load questions from JSON
        session_state = session_manager.create_new_session(questions=all_questions)
        session_state["interview_started"] = True
        session_state["start_time"] = datetime.now().isoformat()
        session_manager.save_session_state(session_state)
        st.rerun()


def interview_screen(session_manager: SessionManager, state: dict):
    """Displays the current question, data editor, and formula input."""
    q_index = state["current_question_index"]
    questions: list[Question] = state["questions"]
    current_question = questions[q_index]

    st.info(f"Task {q_index + 1} of {len(questions)}: {current_question.topic}")
    st.markdown(f"**Instructions:** {current_question.task_description}")
    
    # --- Data Editor ---
    # We use a copy of the starting dataframe for the editor.
    if 'current_df' not in st.session_state or st.session_state.get('question_id') != current_question.id:
        st.session_state['current_df'] = current_question.get_starting_df()
        st.session_state['question_id'] = current_question.id

    edited_df = st.data_editor(
        st.session_state['current_df'], 
        num_rows="dynamic",
        key=f"data_editor_{current_question.id}"
    )

    # --- Formula Input ---
    formula = st.text_input("Enter the primary formula you used:", key=f"formula_input_{current_question.id}")

    if st.button("Submit and Next Task", key=f"submit_{current_question.id}"):
        with st.spinner("Evaluating your submission..."):
            # --- 1. State Analysis (Programmatic Check) ---
            solution_df = current_question.get_solution_df()
            is_state_correct = solution_df.equals(edited_df)
            
            # --- 2. Formula Analysis (AI Evaluation) ---
            ai_evaluation = excel_agent.evaluate_formula(current_question, formula)
            
            # --- 3. Update Session State ---
            state["user_answers"].append({
                "question_id": current_question.id,
                "submitted_formula": formula,
                "final_dataframe": edited_df.to_dict('list'),
                "is_state_correct": is_state_correct
            })
            state["evaluations"].append(ai_evaluation.model_dump()) # Store as dict
            state["current_question_index"] += 1

            # Check if interview is over
            if state["current_question_index"] >= len(questions):
                state["interview_finished"] = True
                state["end_time"] = datetime.now().isoformat()
                save_interview_report(state) # Save to PostgreSQL
            
            # Save the updated state to Redis and rerun the app
            session_manager.save_session_state(state)
            # Clear local state for the next question
            del st.session_state['current_df']
            st.rerun()


def final_report_screen(state: dict):
    """Displays the final performance report."""
    st.success("🎉 You have completed the interview! 🎉")
    st.header("Your Performance Report")

    evaluations = state.get("evaluations", [])
    questions = state.get("questions", [])
    
    if not evaluations:
        st.warning("No evaluations were found.")
        return

    # --- Overall Score ---
    scores = [e['score'] for e in evaluations]
    avg_score = sum(scores) / len(scores) if scores else 0
    st.metric(label="Overall Score", value=f"{avg_score:.1f} / 5.0")
    st.progress(avg_score / 5.0)

    # --- Detailed Feedback per Question ---
    st.subheader("Detailed Feedback")
    for i, evaluation in enumerate(evaluations):
        with st.container(border=True):
            question = questions[i]
            st.markdown(f"**Task {i+1}:** {question.task_description}")
            st.markdown(f"**Your Score:** {'⭐' * evaluation['score']}{'★' * (5 - evaluation['score'])}")
            if evaluation['is_correct']:
                st.success(f"**Feedback:** {evaluation['feedback']}")
            else:
                st.error(f"**Feedback:** {evaluation['feedback']}")
    
    st.info("Thank you for your time. A copy of this report has been saved.")

# --- Helper Function Loader ---
# We still need to create this file.
from utils import helpers

# --- Entry Point ---
if __name__ == "__main__":
    main()