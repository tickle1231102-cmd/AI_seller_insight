from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 값을 os.environ 에도 올려 os.getenv 로 읽는 모듈(ai/client.py 등)에서도 보이게 한다.
load_dotenv()


class Settings(BaseSettings):
    """환경변수 로드. 다른 모듈은 os.environ 대신 settings 를 사용한다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 15
    llm_mode: str = "mock"  # real | mock
    allowed_origins: str = "http://localhost:3000"
    max_files: int = 10
    max_file_size_mb: int = 5

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
