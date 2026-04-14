from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Health Analyzer"
    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    database_url: str = "sqlite:///./health_analyzer.db"

    # File uploads — local path (used when use_azure_storage=False)
    upload_dir: str = "uploads/lab_tests"

    # Azure Blob Storage (for production file uploads)
    use_azure_storage: bool = False
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "health-uploads"

    # Anthropic
    anthropic_api_key: str = ""

    # Whoop
    whoop_client_id: str = ""
    whoop_client_secret: str = ""
    whoop_redirect_uri: str = "http://localhost:8000/api/integrations/whoop/callback"
    whoop_auth_url: str = "https://api.prod.whoop.com/oauth/oauth2/auth"
    whoop_token_url: str = "https://api.prod.whoop.com/oauth/oauth2/token"
    whoop_api_base: str = "https://api.prod.whoop.com/developer/v1"

    # Withings
    withings_client_id: str = ""
    withings_client_secret: str = ""
    withings_redirect_uri: str = "http://localhost:8000/api/integrations/withings/callback"
    withings_auth_url: str = "https://account.withings.com/oauth2_user/authorize2"
    withings_token_url: str = "https://wbsapi.withings.net/v2/oauth2"
    withings_api_base: str = "https://wbsapi.withings.net"

    # Fitbod
    fitbod_client_id: str = ""
    fitbod_client_secret: str = ""
    fitbod_redirect_uri: str = "http://localhost:8000/api/integrations/fitbod/callback"

    # Yazio
    yazio_client_id: str = ""
    yazio_client_secret: str = ""
    yazio_redirect_uri: str = "http://localhost:8000/api/integrations/yazio/callback"
    yazio_api_base: str = "https://api.yazio.com/v1"

    # Renpho
    renpho_api_base: str = "https://renphohealth.com/api"

    # Braun
    braun_api_key: str = ""

    # Larq
    larq_client_id: str = ""
    larq_client_secret: str = ""
    larq_redirect_uri: str = "http://localhost:8000/api/integrations/larq/callback"
    larq_api_base: str = "https://api.mylarq.com/v1"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
