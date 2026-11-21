from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model_name: str = "qwen3:8b"

    log_level: str = "INFO"
    log_level_libs: str = "WARNING"  # httpx/httpcore/urllib3/chromadb/sentence_transformers


settings = Settings()
