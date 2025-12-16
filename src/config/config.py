from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Racine du projet (…/spotify-like-sorter)
    project_root: Path = Path(__file__).resolve().parent.parent.parent

    # Application
    app_name: str = "Spotify Auto Like Sorter"
    app_version: str = "1.0.0"
    debug: bool = False

    # Spotify
    spotify_client_id: str = Field(..., alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(..., alias="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = Field(default="http://localhost:8888/callback")

    # Preview Fetching
    deezer_enabled: bool = Field(default=True, alias="DEEZER_ENABLED")
    itunes_enabled: bool = Field(default=True, alias="ITUNES_ENABLED")
    max_concurrent_downloads: int = Field(default=10, alias="MAX_CONCURRENT_DOWNLOADS")
    download_timeout: int = Field(default=15, alias="DOWNLOAD_TIMEOUT")
    previews_dir: Path = Field(default=None, alias="PREVIEWS_DIR")

    # Database
    database_url: str = Field(default=None, alias="DATABASE_URL")
    database_echo: bool = Field(default=False)

    # Cache
    cache_dir: Path = Field(default=None, alias="CACHE_DIR")
    cache_ttl: int = Field(default=3600)
    cache_enabled: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_file: Path = Field(default=None, alias="LOG_FILE")

    # Performance
    max_workers: int = Field(default=4)
    batch_size: int = Field(default=50)

    model_config = SettingsConfigDict(
        env_file=project_root / ".env",  # .env à la racine
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def __init__(self, **data):
        super().__init__(**data)

        def _anchor_path(p: Path) -> Path:
            """Si p est relatif, le rattache à la racine du projet."""
            if p is None:
                return None
            return p if p.is_absolute() else (self.project_root / p)

        # --- Defaults ancrés à la racine (si pas fournis via .env) ---
        if self.database_url is None:
            db_path = self.project_root / "spotify_analyzer.db"
            self.database_url = f"sqlite:///{db_path.as_posix()}"
        else:
            # Si l'env fournit un sqlite relatif (ex: sqlite:///spotify_analyzer.db),
            # on le rend absolu vers project_root.
            if self.database_url.startswith("sqlite:///"):
                raw = self.database_url.removeprefix("sqlite:///")
                if raw and not Path(raw).is_absolute():
                    db_path = self.project_root / raw
                    self.database_url = f"sqlite:///{db_path.as_posix()}"

        if self.cache_dir is None:
            self.cache_dir = self.project_root / "cache"
        else:
            self.cache_dir = _anchor_path(self.cache_dir)

        if self.log_file is None:
            self.log_file = self.project_root / "logs" / "app.log"
        else:
            self.log_file = _anchor_path(self.log_file)

        if self.previews_dir is None:
            self.previews_dir = self.project_root / "previews"
        else:
            self.previews_dir = _anchor_path(self.previews_dir)

        # --- Création des dossiers au bon endroit ---
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()