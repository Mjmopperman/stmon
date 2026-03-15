# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "92.4.143.135"
    DB_PORT: int = 5432
    
    # Hasura settings (not used by FastAPI, but needed for .env validation)
    HASURA_ADMIN_SECRET: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env
