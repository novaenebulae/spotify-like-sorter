#!/usr/bin/env python
import os
import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.spotify_client import SpotifyClient
from src.logger import logger


async def main():
    logger.info("🔗 Test Spotify...")

    try:
        client = SpotifyClient()

        if client.test_connection():
            user = client.get_current_user()
            logger.info(f"👤 {user['display_name']}")
            logger.info(f"📊 Followers: {user['followers']['total']}")

            logger.info("\\n📥 Récupération 10 premiers tracks...")
            tracks = await client.get_all_liked_tracks()

            if tracks:
                logger.info(f"✅ {len(tracks)} tracks")
                for i, item in enumerate(tracks[:3], 1):
                    parsed = client.parse_track_data(item)
                    logger.info(f"  {i}. {parsed['title']} - {parsed['artist']}")

            return 0

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))