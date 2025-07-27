# app/core/config.py

import os
from pydantic_settings import BaseSettings
from pydantic import Field

# A small hack to help Pydantic find the .env file
# when running inside a Docker container where the working directory is /app.
# If you run locally, you might need to adjust the path or ensure you
# `cd` into the root directory first.
# An alternative is to use a library like `python-dotenv`.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # --- App Settings ---
    APP_TITLE: str = Field("AI Excel Interviewer", description="The title of the application.")

    # --- Redis Configuration ---
    REDIS_HOST: str = Field(..., description="Redis server host.")
    REDIS_PORT: int = Field(6379, description="Redis server port.")
    REDIS_PASSWORD: str | None = Field(None, description="Redis server password, if any.")

    # --- PostgreSQL Configuration ---
    POSTGRES_HOST: str = Field(..., description="PostgreSQL server host.")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL server port.")
    POSTGRES_USER: str = Field(..., description="PostgreSQL username.")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password.")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name.")

    @property
    def postgres_dsn(self) -> str:
        """Generates the PostgreSQL Data Source Name (DSN)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- Ollama AI Configuration ---
    OLLAMA_HOST: str = Field(..., description="URL for the Ollama server.")
    OLLAMA_MODEL: str = Field("llama3:8b", description="The LLM model to use for the agent.")

    class Config:
        # This tells Pydantic to look for a .env file.
        # However, due to Docker's working directory, we load it manually above.
        env_file = ".env"
        env_file_encoding = 'utf-8'


# Create a single, importable instance of the settings
settings = Settings()