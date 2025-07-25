import os
from typing import List
import dotenv
from typing import Optional

dotenv.load_dotenv()

class Settings:
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL",
                                            "postgresql://postgres:Mahen2%40_Money@localhost:5432/chatdb" )
    
    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:5500",  # Live Server
        "http://localhost:5173",  # Vite default
    ]
    
    # App Settings
    APP_NAME: str = os.getenv("APP_NAME", "Chat Application")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Admin Credentials (change in production!)
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

settings = Settings()