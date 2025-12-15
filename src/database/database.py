from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from pathlib import Path

from src.config import settings
from src.logger import logger
from src.database.models import Base


class DatabaseManager:
    """Gestion de la base de données"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _initialize(self):
        """Initialise SQLAlchemy"""
        try:
            db_url = self.database_url
            if db_url.startswith("sqlite://"):
                db_path = db_url.replace("sqlite:///", "")
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            self.engine = create_engine(
                db_url,
                echo=settings.database_echo,
                connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"✅ BD initialisée: {db_url}")

        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            raise

    def create_tables(self):
        """Crée toutes les tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Tables créées")
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            raise

    def get_session(self) -> Session:
        """Retourne une session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Context manager pour les sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur transaction: {e}")
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Vérifie la connexion"""
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            logger.info("✅ Health check OK")
            return True
        except Exception as e:
            logger.error(f"❌ Health check échoué: {e}")
            return False


db_manager = DatabaseManager()