from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Notification Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database Settings
    DB_NAME: str = "hrms_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_CHARSET: str = "utf8"

    # CORS Settings
    CORS_ORIGINS: str = "https://localhost,http://localhost:3000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ==========================================
    # Kafka Settings
    # ==========================================
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP_ID: str = "notification-service-consumer"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = False
    KAFKA_MAX_POLL_INTERVAL_MS: int = 300000
    KAFKA_SESSION_TIMEOUT_MS: int = 45000
    KAFKA_HEARTBEAT_INTERVAL_MS: int = 15000

    # ==========================================
    # Redis Settings
    # ==========================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Cache TTL Settings (in seconds)
    CACHE_TTL_PREFERENCES: int = 3600  # 1 hour
    CACHE_TTL_TEMPLATES: int = 3600  # 1 hour
    CACHE_TTL_METRICS: int = 300  # 5 minutes
    CACHE_TTL_DEDUP: int = 86400  # 24 hours

    # ==========================================
    # Email Provider Settings
    # ==========================================
    # Options: "ses", "smtp", "hybrid"
    # - "ses": Use only Amazon SES
    # - "smtp": Use only Gmail SMTP
    # - "hybrid": Use SES as primary with SMTP as fallback
    EMAIL_PROVIDER: str = "hybrid"

    # Amazon SES Settings (Primary for Kubernetes deployment)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    SES_SENDER_EMAIL: str = ""  # Must be verified in SES
    SES_CONFIGURATION_SET: str = ""  # Optional: for tracking/metrics
    SES_ENABLED: bool = True

    # Gmail SMTP Settings (Secondary/Fallback)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_APP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_ENABLED: bool = True

    EMAIL_SERVICE_NAME: str = "HRMS"

    # Notification Settings
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 300

    # Rate Limiting Settings
    RATE_LIMIT_MAX_REQUESTS: int = 100  # Max emails per window
    RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour window

    # Fallback Settings
    ENABLE_FALLBACK: bool = True  # Enable fallback to secondary provider
    FALLBACK_RETRY_COUNT: int = 2  # Number of retries before falling back

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return [self.CORS_ORIGINS]

    @property
    def use_ses_primary(self) -> bool:
        """Check if SES should be used as primary provider."""
        return self.EMAIL_PROVIDER in ("ses", "hybrid") and self.SES_ENABLED

    @property
    def use_smtp_primary(self) -> bool:
        """Check if SMTP should be used as primary provider."""
        return self.EMAIL_PROVIDER == "smtp" and self.SMTP_ENABLED

    @property
    def has_fallback(self) -> bool:
        """Check if fallback is available and enabled."""
        if not self.ENABLE_FALLBACK:
            return False
        if self.EMAIL_PROVIDER == "hybrid":
            return self.SMTP_ENABLED
        return False

    @property
    def ses_configured(self) -> bool:
        """Check if SES is properly configured."""
        return bool(
            self.AWS_ACCESS_KEY_ID
            and self.AWS_SECRET_ACCESS_KEY
            and self.SES_SENDER_EMAIL
        )

    @property
    def smtp_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.SMTP_USER and self.SMTP_APP_PASSWORD)

    @property
    def kafka_configured(self) -> bool:
        """Check if Kafka is properly configured."""
        return bool(self.KAFKA_BOOTSTRAP_SERVERS)

    @property
    def redis_configured(self) -> bool:
        """Check if Redis is properly configured."""
        return bool(self.REDIS_HOST and self.REDIS_PORT)

    # Asgardeo OAuth2 Settings
    ASGARDEO_ORG: str = ""  # REQUIRED: Must be set in .env file
    ASGARDEO_CLIENT_ID: str = ""  # REQUIRED: Must be set in .env file
    JWT_AUDIENCE: str | None = None  # Optional: Set in .env if needed
    JWT_ISSUER: str | None = None  # Optional: Set in .env if needed

    @property
    def jwks_url(self) -> str:
        """Generate JWKS URL from Asgardeo organization."""
        return f"https://api.asgardeo.io/t/{self.ASGARDEO_ORG}/oauth2/jwks"

    @property
    def token_url(self) -> str:
        """Generate token endpoint URL from Asgardeo organization."""
        return f"https://api.asgardeo.io/t/{self.ASGARDEO_ORG}/oauth2/token"

    @property
    def issuer(self) -> str:
        """Get JWT issuer, fallback to token URL if not explicitly set."""
        if self.JWT_ISSUER:
            return self.JWT_ISSUER
        return self.token_url

    @property
    def database_url(self) -> str:
        """Generate MySQL database URL."""
        return f"mysql+mysqldb://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"

    @property
    def database_url_without_db(self) -> str:
        """Generate MySQL URL without database name (for initial connection)."""
        return f"mysql+mysqldb://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}?charset={self.DB_CHARSET}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
