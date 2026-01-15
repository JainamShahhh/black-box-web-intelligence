"""
Configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # LLM Provider
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="Which LLM provider to use"
    )
    
    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model name")
    
    # Anthropic
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", 
        description="Anthropic model name"
    )
    
    # Database
    database_path: str = Field(
        default="./data/blackbox.db",
        description="SQLite database path"
    )
    
    # ChromaDB
    chroma_persist_dir: str = Field(
        default="./data/chroma",
        description="ChromaDB persistence directory"
    )
    
    # Server
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    # Browser
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_timeout: int = Field(default=30000, description="Browser timeout in ms")
    
    # Safety & Rate Limiting
    max_requests_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute to target"
    )
    max_exploration_depth: int = Field(
        default=50,
        description="Maximum depth of exploration"
    )
    max_loop_iterations: int = Field(
        default=1000,
        description="Maximum scientific loop iterations"
    )
    confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for hypothesis export"
    )
    
    # Guardrails
    authorized_domains: str = Field(
        default="",
        description="Comma-separated list of authorized domains"
    )
    enable_probing: bool = Field(
        default=True,
        description="Enable hypothesis probing/verification"
    )
    enable_fuzzing: bool = Field(
        default=False,
        description="Enable security fuzzing (disabled by default)"
    )


# Global settings instance
settings = Settings()
