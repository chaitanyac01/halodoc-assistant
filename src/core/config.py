from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # Google AI Configuration
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    model_name: str = Field(default="gemini-1.5-pro", env="MODEL_NAME")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    max_tokens: int = Field(default=2048, env="MAX_TOKENS")
    
    # Vector Database
    chroma_persist_directory: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    
    # Agent Configuration
    max_agent_iterations: int = Field(default=5, env="MAX_AGENT_ITERATIONS")
    agent_timeout_seconds: int = Field(default=30, env="AGENT_TIMEOUT_SECONDS")
    
    # Mock Services
    payment_service_url: str = Field(default="http://mock-payment-service", env="PAYMENT_SERVICE_URL")
    order_service_url: str = Field(default="http://mock-order-service", env="ORDER_SERVICE_URL")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="./logs/halodoc_assistant.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    return Settings()

# Create necessary directories
def setup_directories():
    settings = get_settings()
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(settings.log_file)).mkdir(parents=True, exist_ok=True)