# app/core/models.py

from pydantic import BaseModel, Field
import pandas as pd
from typing import Any, Dict, List

class Question(BaseModel):
    """
    Represents a single interview question/task.
    This model validates the structure of each entry in questions.json.
    """
    id: str = Field(..., description="Unique identifier for the question.")
    topic: str = Field(..., description="The category of the question, e.g., 'Formulas & Functions'.")
    difficulty: str = Field(..., description="Difficulty level, e.g., 'Easy', 'Intermediate', 'Hard'.")
    task_description: str = Field(..., description="The instruction given to the candidate.")
    
    # The starting data for the st.data_editor, represented as a dictionary
    # that can be loaded into a Pandas DataFrame.
    # e.g., {"col1": [1, 2], "col2": [3, 4]}
    starting_data: Dict[str, List[Any]]
    
    # The expected final state of the data for programmatic checking.
    # Same format as starting_data.
    solution_data: Dict[str, List[Any]]
    
    # The evaluation prompt for the LLM, focusing on the "how".
    evaluation_criteria: str = Field(..., description="Specific criteria for the LLM to evaluate the user's formula.")

    def get_starting_df(self) -> pd.DataFrame:
        """Helper to convert starting_data dict to a DataFrame."""
        return pd.DataFrame(self.starting_data)
    
    def get_solution_df(self) -> pd.DataFrame:
        """Helper to convert solution_data dict to a DataFrame."""
        return pd.DataFrame(self.solution_data)


class Evaluation(BaseModel):
    """
    Represents the structured evaluation output from the LLM.
    This model ensures the AI's response is in the format we expect.
    """
    score: int = Field(..., ge=1, le=5, description="The score from 1 (poor) to 5 (excellent).")
    is_correct: bool = Field(..., description="Whether the formula logic is fundamentally correct.")
    feedback: str = Field(..., description="Detailed justification for the score, including comments on correctness, efficiency, and best practices.")