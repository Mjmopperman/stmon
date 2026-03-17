# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    # Hasura settings
    HASURA_ADMIN_SECRET: str
    HASURA_URL: str = "http://hasura:8080/v1/graphql"  # Internal Docker network URL

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env

settings = Settings()