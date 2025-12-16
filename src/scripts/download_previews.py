import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration du chemin projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))


from src.logger import logger
from src.database.database import db_manager
from src.database.repository import TrackRepository, AnalysisRepository
from src.audio.preview_manager import PreviewManager


async def main():
    """Exécution principale Phase 2"""

    logger.info("=" * 60)
    logger.info("🎵 SPOTIFY AUTO LIKE SORTER - PHASE 2")
    logger.info("Fetching Previews (Deezer + iTunes)")
    logger.info("=" * 60)

    try:
        # 1. Vérifier BD
        logger.info("\n1️⃣ Vérification base de données...")
        db_manager.create_tables()
        db_manager.health_check()

        with db_manager.session_scope() as session:
            track_repo = TrackRepository(session)
            analysis_repo = AnalysisRepository(session)

            # Stats initiales
            total_tracks = track_repo.count_all()
            preview_stats = analysis_repo.get_preview_stats()

            logger.info(f"✅ BD OK: {total_tracks} tracks")
            logger.info(f"   Previews actuels: {preview_stats['fetched']}/{total_tracks}")

            # 2. Récupérer tous les tracks
            logger.info("\n2️⃣ Récupération des tracks...")
            all_tracks = track_repo.get_all_tracks()[:10]

            tracks_data = [
                {
                    'spotify_id': track.spotify_id,
                    'title': track.title,
                    'artist': track.artist,
                    'isrc': track.isrc
                }
                for track in all_tracks
            ]

            logger.info(f"✅ {len(tracks_data)} tracks prêts")

            # 3. Fetch + Download
            logger.info("\n3️⃣ Début: Fetch + Download...")
            manager = PreviewManager(session)

            start_time = datetime.now()
            stats = await manager.process_all_tracks(tracks_data, download=True)
            duration = (datetime.now() - start_time).total_seconds()

            # 4. Stats finales
            logger.info("\n4️⃣ Statistiques finales:")
            logger.info(f"   Total: {stats['total']}")
            logger.info(f"   Trouvés: {stats['fetched']} ({stats['fetched'] / stats['total'] * 100:.1f}%)")
            logger.info(f"   - Deezer: {stats['deezer']}")
            logger.info(f"   - iTunes: {stats['itunes']}")
            logger.info(f"   Non trouvés: {stats['not_found']}")
            logger.info(f"   Téléchargés: {stats['downloaded']}")
            logger.info(f"   Erreurs téléchargement: {stats['download_failed']}")
            logger.info(f"   Durée: {duration / 60:.1f} minutes")

            # 5. Vérification fichiers
            logger.info("\n5️⃣ Vérification fichiers...")
            verify_stats = manager.downloader.verify_all()

            # CORRECTION: Vérifier la clé 'status' avant d'accéder aux autres
            if verify_stats['status'] == 'ERROR':
                logger.warning("   Aucun fichier trouvé!")
            else:
                logger.info(f"   Fichiers: {verify_stats['total_files']}")
                logger.info(f"   Taille totale: {verify_stats['total_size_mb']:.1f} MB")
                logger.info(f"   Taille moyenne: {verify_stats['avg_size_kb']:.1f} KB")

            logger.info("\n✅ Phase 2 terminée avec succès!")
            return 0

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
