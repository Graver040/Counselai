import os

class Settings:
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./dev.db')

settings = Settings()
