# app/core/agent.py

from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict, Any
import logging

from app.core.config import settings
from app.core.models import Question, Evaluation

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelAgent:
    """
    The AI agent responsible for evaluating candidate responses.
    """
    def __init__(self):
        # Initialize the ChatOllama model connector
        try:
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_HOST,
                temperature=0.0,  # We want deterministic, consistent evaluations
                keep_alive=-1 # Keep the model loaded in memory
            )
            logger.info(f"ChatOllama initialized successfully with model '{settings.OLLAMA_MODEL}'.")
        except Exception as e:
            logger.error(f"Failed to initialize ChatOllama: {e}")
            self.llm = None
        
        # Define the Pydantic model for the output parser
        self.parser = JsonOutputParser(pydantic_object=Evaluation)

        # Define the prompt template for the evaluation
        self.prompt = ChatPromptTemplate.from_template(
            """
            System: You are an expert Excel formula evaluator for a technical interview.
            Your task is to assess a candidate's submitted formula for a specific task.
            Evaluate the formula strictly based on the provided criteria.
            Provide your evaluation in a valid JSON format.

            **Task Context:**
            - Task Description: {task_description}
            - Evaluation Criteria: {evaluation_criteria}

            **Candidate's Submission:**
            - Formula: "{candidate_formula}"

            **Your Evaluation:**
            - Please provide your detailed assessment below.
            {format_instructions}
            """
        )
        
        # Chain the components together
        if self.llm:
            self.chain = self.prompt | self.llm | self.parser
        else:
            self.chain = None

    def evaluate_formula(self, question: Question, candidate_formula: str) -> Evaluation | None:
        """
        Evaluates the candidate's formula for a given question.

        Args:
            question: The Question object containing the task and criteria.
            candidate_formula: The formula string submitted by the candidate.

        Returns:
            An Evaluation object with the score and feedback, or None if an error occurs.
        """
        if not self.chain:
            logger.error("Evaluation chain is not initialized. Cannot evaluate.")
            return None

        try:
            logger.info(f"Invoking evaluation chain for question '{question.id}'...")
            
            # Prepare the input for the chain
            chain_input = {
                "task_description": question.task_description,
                "evaluation_criteria": question.evaluation_criteria,
                "candidate_formula": candidate_formula,
                "format_instructions": self.parser.get_format_instructions(),
            }
            
            # Invoke the chain and get the structured output
            evaluation_result = self.chain.invoke(chain_input)
            
            # Pydantic will have already validated the structure, but we can log it
            logger.info(f"Evaluation successful. Score: {evaluation_result['score']}.")
            
            # The parser returns a dict, so we instantiate our model from it
            return Evaluation(**evaluation_result)

        except Exception as e:
            logger.error(f"An error occurred during formula evaluation: {e}", exc_info=True)
            # In case of a parsing or LLM error, return a default error evaluation
            return Evaluation(
                score=1,
                is_correct=False,
                feedback="An error occurred while evaluating the response. Please ensure the formula is valid or try again."
            )

# Create a single, importable instance of the agent
excel_agent = ExcelAgent()