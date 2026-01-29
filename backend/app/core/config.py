from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DATABASE_URL: str = "sqlite:///./app.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    LLM_PROVIDER: str = "mock"

    class Config:
        env_file = ".env"

settings = Settings()
