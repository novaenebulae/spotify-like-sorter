#!/usr/bin/env python
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database import db_manager
from src.logger import logger


def main():
    logger.info("🚀 Initialisation BD...")

    try:
        db_manager.create_tables()
        if db_manager.health_check():
            logger.info("✅ BD prête!")
            return 0
        else:
            logger.error("❌ Health check échoué")
            return 1

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())