from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    app_name: str = "Spotify Auto Like Sorter"
    app_version: str = "1.0.0"
    debug: bool = False

    # Spotify
    spotify_client_id: str = Field(..., alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(..., alias="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = Field(default="http://localhost:8888/callback")

    # Database
    database_url: str = Field(default="sqlite:///./spotify_analyzer.db")
    database_echo: bool = Field(default=False)

    # Cache
    cache_dir: Path = Field(default=Path("./cache"))
    cache_ttl: int = Field(default=3600)
    cache_enabled: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_file: Path = Field(default=Path("./logs/app.log"))

    # Performance
    max_workers: int = Field(default=4)
    batch_size: int = Field(default=50)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **data):
        super().__init__(**data)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()