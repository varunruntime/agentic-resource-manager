from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Agentic AI Resource Manager"
    database_url: str = "sqlite:///./agentic.db"
    secret_key: str = "change-me-in-production"
    simulation_mode: bool = True
    llm_api_key: str | None = None
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
