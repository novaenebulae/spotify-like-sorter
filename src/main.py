#!/usr/bin/env python
import asyncio

from config import settings
from logger import logger
from database.database import db_manager
from api.spotify_client import SpotifyClient
from database.repository import TrackRepository, AnalysisRepository


async def main():
    logger.info(f"🚀 {settings.app_name} v{settings.app_version}")

    try:
        # 1. BD
        logger.info("1️⃣ Vérification BD...")
        db_manager.create_tables()
        db_manager.health_check()

        # 2. Spotify
        logger.info("2️⃣ Connexion Spotify...")
        spotify = SpotifyClient()
        spotify.test_connection()

        # 3. Récupérer tracks
        logger.info("3️⃣ Récupération titres likés...")

        def progress_callback(current, total):
            percent = (current / total) * 100
            logger.info(f"   {current}/{total} ({percent:.1f}%)")

        tracks = await spotify.get_all_liked_tracks(progress_callback)

        # 4. Sauvegarder
        logger.info("4️⃣ Sauvegarde...")

        parsed_tracks = [spotify.parse_track_data(item) for item in tracks]

        with db_manager.session_scope() as session:
            track_repo = TrackRepository(session)
            analysis_repo = AnalysisRepository(session)

            track_repo.create_many_tracks(parsed_tracks)

            for track_data in parsed_tracks:
                analysis_repo.create_analysis(track_data['spotify_id'])

            session.commit()

        # 5. Stats
        with db_manager.session_scope() as session:
            track_repo = TrackRepository(session)
            analysis_repo = AnalysisRepository(session)

            total = track_repo.count_all()
            stats = analysis_repo.get_stats()

            logger.info(f"\\n📊 Statistiques:")
            logger.info(f"   Total: {total}")
            logger.info(f"   Pending: {stats['pending']}")
            logger.info(f"   Completed: {stats['completed']}")

        logger.info("\\n✅ Phase 1 réussie!")
        return 0

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))