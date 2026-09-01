from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ALLSPORTS_API_KEY: str = ""
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/arbitrage"
    DEFAULT_TOTAL_STAKE: float = 1000.0
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
