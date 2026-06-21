import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    APP_NAME: str = "ShortLink API"
    APP_VERSION: str = "1.0.0"
    
    SHORT_CODE_LENGTH: int = 6
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    REDIRECT_STATUS_CODE: int = 302
    
    DATABASE_PATH: Path = BASE_DIR / "data" / "shortlinks.db"
    
    GEOIP_DB_PATH: Path = BASE_DIR / "data" / "GeoLite2-City.mmdb"
    GEOIP_DOWNLOAD_URL: str = "https://git.io/GeoLite2-City.mmdb"
    
    RATE_LIMIT_CREATE: str = "10/minute"
    RATE_LIMIT_REDIRECT: str = "100/minute"
    
    BLACKLIST_DOMAINS: list = [
        "malware.com",
        "phishing.com",
        "scam.example.com",
    ]
    
    SNOWFLAKE_DATACENTER_ID: int = 1
    SNOWFLAKE_WORKER_ID: int = 1
    
    MAX_BATCH_SIZE: int = 100
    
    PASSWORD_COOKIE_NAME: str = "shortlink_auth"
    PASSWORD_COOKIE_TTL: int = 86400
    COOKIE_SECRET_KEY: str = os.getenv("COOKIE_SECRET_KEY", secrets.token_hex(32))
    
    DEFAULT_ADMIN_API_KEY: str = os.getenv("DEFAULT_ADMIN_API_KEY", "admin-default-key-2024")

settings = Settings()
