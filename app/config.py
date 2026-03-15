from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "92.4.143.135"  # Your DB VM IP
    DB_PORT: int = 5432

    class Config:
        env_file = ".env"

settings = Settings()
