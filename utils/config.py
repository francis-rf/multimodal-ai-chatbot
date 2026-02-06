"""
Configuration Management using Pydantic Settings
Loads environment variables from .env file
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Main Settings class that loads all configuration from .env file"""

    # API Keys
    groq_api_key: str
    gemini_api_key: str
    fireworks_api_key: str
    tavily_api_key: str

    # Model Configuration
    openai_model: str = "openai/gpt-oss-120b"
    groq_model: str = "groq/compound"
    gemini_model: str = "gemini-2.5-flash-lite"
    qwen_model: str = "qwen/qwen3-32b"
    llama_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    fireworks_model: str = "stable-diffusion-xl-1024-v1-0"
    text_to_speech: str = "canopylabs/orpheus-v1-english"

    # API Base URLs
    groq_base_url: str = "https://api.groq.com/openai/v1"
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Application Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_env: str = "development"
    debug: bool = True

    # CORS Settings
    cors_origins: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"

    # File Upload Settings
    upload_dir: str = "./uploads"
    max_file_size: int = 10485760  # 10MB in bytes
    allowed_image_formats: str = "jpg,jpeg,png,gif,webp"
    allowed_audio_formats: str = "mp3,wav,ogg,m4a"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    # Logging Settings
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string to list"""
        return [origin.strip() for origin in self.cors_origins.split(',')]

    def get_allowed_images(self) -> List[str]:
        """Parse allowed image formats to list"""
        return [fmt.strip().lower() for fmt in self.allowed_image_formats.split(',')]

    def get_allowed_audio(self) -> List[str]:
        """Parse allowed audio formats to list"""
        return [fmt.strip().lower() for fmt in self.allowed_audio_formats.split(',')]


# Create singleton instance
settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
