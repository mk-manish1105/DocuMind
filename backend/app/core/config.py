from dotenv import load_dotenv
import os

# Load environment variables from .env file into the process environment.
# This allows configuration without hardcoding secrets in code.
load_dotenv()


class Settings:
    """
    Centralized application configuration.

    This class reads configuration values from environment variables
    and exposes them as typed attributes. It is instantiated once and
    reused across the application.
    """

    # ------------------------
    # Database configuration
    # ------------------------
    # SQLAlchemy-compatible database connection URL
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # ------------------------
    # Authentication / JWT configuration
    # ------------------------
    # Secret key used to sign and verify JWT tokens.
    # A default value is provided for local development only.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "unsafe-secret")

    # Algorithm used for JWT encoding/decoding
    JWT_ALGORITHM: str = "HS256"

    # Access token expiration time (in minutes).
    # Defaults to 30 days if not explicitly set.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200")
    )

    # ------------------------
    # Model API configuration
    # ------------------------
    # API key for accessing the external language model service
    LLAMA_API_KEY: str = os.getenv("LLAMA_API_KEY")

    # Base URL for the model chat/completions endpoint
    LLAMA_API_URL: str = os.getenv(
        "LLAMA_API_URL",
        "https://api.groq.com/openai/v1/chat/completions"
    )

    # Default model identifier used for generating responses
    LLAMA_MODEL: str = os.getenv(
        "LLAMA_MODEL",
        "llama-3.1-8b-instant"
    )


# Singleton settings instance imported across the app
settings = Settings()
