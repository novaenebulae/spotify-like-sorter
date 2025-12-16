#!/usr/bin/env python
"""
Vérifier l'état des previews après Phase 2
"""
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import settings
from src.database.database import db_manager
from src.database.repository import AnalysisRepository
from src.logger import logger


def main():
    """Vérification des previews"""

    logger.info("=" * 60)
    logger.info("🔍 Vérification Phase 2 - Previews")
    logger.info("=" * 60)

    try:
        db_manager.create_tables()

        with db_manager.session_scope() as session:
            analysis_repo = AnalysisRepository(session)

            # Stats
            stats = analysis_repo.get_preview_stats()

            logger.info("\n📊 Statistiques Previews:")
            logger.info(f"   Total tracks: {stats['total']}")
            logger.info(
                f"   Trouvés: {stats['fetched']}/{stats['total']} ({stats['fetched'] / stats['total'] * 100:.1f}%)")
            logger.info(f"   - Deezer: {stats['deezer']}")
            logger.info(f"   - iTunes: {stats['itunes']}")
            logger.info(f"   - Non trouvés: {stats['not_found']}")
            logger.info(f"   - Téléchargés: {stats['downloaded']}")

            # Vérifier fichiers
            previews_dir = settings.previews_dir
            if previews_dir.exists():
                mp3_files = list(previews_dir.glob("*.mp3"))
                total_size = sum(f.stat().st_size for f in mp3_files)

                logger.info(f"\n💾 Fichiers:")
                logger.info(f"   Fichiers MP3: {len(mp3_files)}")
                logger.info(f"   Taille totale: {total_size / (1024 ** 3):.2f} GB")

            logger.info("\n✅ Vérification complète!")
            return 0

    except Exception as e:
        logger.error(f"Erreur: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())