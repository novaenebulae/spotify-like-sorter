import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from src.api.deezer_client import DeezerClient
from src.api.itunes_client import iTunesClient
from src.audio.preview_downloader import PreviewDownloader
from src.database.repository import AnalysisRepository, TrackRepository
from src.logger import logger


class PreviewManager:
    """Gère la récupération et téléchargement de previews"""

    def __init__(self, session: Session):
        self.session = session
        self.analysis_repo = AnalysisRepository(session)
        self.downloader = PreviewDownloader()

    async def fetch_preview(
        self,
        track: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Récupérer preview: Deezer → iTunes → None

        Args:
            track: {
                'spotify_id': str,
                'title': str,
                'artist': str,
                'isrc': str
            }

        Returns:
            {
                'preview_url': str,
                'source': 'deezer' ou 'itunes',
                'fetched_at': datetime
            }
            ou None
        """
        track_id = track['spotify_id']
        title = track.get('title', 'Unknown')

        # 1. Essayer Deezer
        logger.debug(f"🔍 Cherching: {title} (via Deezer)")

        try:
            async with DeezerClient() as deezer:
                result = await deezer.search(
                    isrc=track.get('isrc'),
                    title=track.get('title'),
                    artist=track.get('artist'),
                    track_id=track_id
                )

                if result:
                    logger.debug(f"✅ Deezer trouvé: {track.get('isrc')} → {result['preview_url'][:60]}...")
                    return {
                        'preview_url': result['preview_url'],
                        'source': 'deezer',
                        'fetched_at': datetime.utcnow()
                    }
                else:
                    logger.debug(f"❌ Deezer not found: {track.get('isrc')}")

        except Exception as e:
            logger.error(f"❌ Deezer error ({track_id}): {type(e).__name__}: {e}")

        # 2. Fallback iTunes
        logger.debug(f"🔍 Fallback iTunes: {title}")

        try:
            async with iTunesClient() as itunes:
                result = await itunes.search_by_name(
                    title=track.get('title'),
                    artist=track.get('artist'),
                    track_id=track_id
                )

                if result:
                    logger.debug(f"✅ iTunes trouvé: {track.get('isrc')} → {result['preview_url'][:60]}...")
                    return {
                        'preview_url': result['preview_url'],
                        'source': 'itunes',
                        'fetched_at': datetime.utcnow()
                    }
                else:
                    logger.debug(f"❌ iTunes not found: {track.get('isrc')}")

        except Exception as e:
            logger.error(f"❌ iTunes error ({track_id}): {type(e).__name__}: {e}")

        # 3. Pas trouvé
        logger.debug(f"⚠️ No preview found: {track_id}")
        return None

    async def process_all_tracks(
        self,
        tracks: list,
        download: bool = True
    ) -> Dict[str, Any]:
        """
        Traiter tous les tracks: fetch + download

        Args:
            tracks: Liste des tracks
            download: Télécharger les fichiers?

        Returns:
            Stats globales
        """
        stats = {
            'total': len(tracks),
            'fetched': 0,
            'deezer': 0,
            'itunes': 0,
            'not_found': 0,
            'downloaded': 0,
            'download_failed': 0
        }

        download_queue = []

        with logging_redirect_tqdm():
            # Phase 1: Fetch URLs
            logger.info(f"📡 Phase 1: Fetching {len(tracks)} previews...")

            with tqdm(tracks, desc="Fetch previews", unit="track", smoothing=0.05) as pbar:
                for track in pbar:
                    if self.analysis_repo.get_track_preview_status_by_spotify_id(track['spotify_id']).preview_status in ['downloaded']:
                        pbar.set_postfix(
                            fetched=stats['fetched'],
                            deezer=stats['deezer'],
                            itunes=stats['itunes'],
                            not_found=stats['not_found'],
                        )
                        continue

                    try:
                        result = await self.fetch_preview(track)

                        if result:
                            # Mettre à jour BD
                            self.analysis_repo.update_analysis(
                                spotify_id=track['spotify_id'],
                                track_preview_url=result['preview_url'],
                                preview_source=result['source'],
                                preview_fetched_at=result['fetched_at'],
                                preview_status='fetched'
                            )

                            stats['fetched'] += 1
                            stats[result['source']] += 1

                            if download:
                                download_queue.append({
                                    'track_id': track['spotify_id'],
                                    'preview_url': result['preview_url']
                                })

                        else:
                            # Pas trouvé
                            self.analysis_repo.update_analysis(
                                spotify_id=track['spotify_id'],
                                preview_status='not_found',
                                preview_error='No preview found on Deezer or iTunes'
                            )

                            stats['not_found'] += 1

                        self.session.commit()

                    except Exception as e:
                        logger.error(f"Error processing {track['spotify_id']}: {e}")
                        self.session.rollback()

            logger.info(f"\n✅ Phase 1 complete: {stats['fetched']} found, {stats['not_found']} not found")

            # Phase 2: Download
            if download and download_queue:
                logger.info(f"💾 Phase 2: Downloading {len(download_queue)} previews...")

                download_stats = await self.downloader.download_batch(download_queue)

                # Mettre à jour statuts
                for track_id, local_path in download_stats['downloaded_files'].items():
                    self.analysis_repo.update_analysis(
                        spotify_id=track_id,
                        preview_local_path=local_path,
                        preview_status='downloaded'
                    )

                # Erreurs: Sauvegarder les erreurs
                for track_id, error in download_stats['errors'].items():
                    self.analysis_repo.update_analysis(
                        spotify_id=track_id,
                        preview_error=error,
                        preview_status='download_failed'
                    )

                self.session.commit()

                stats['downloaded'] = download_stats['success']
                stats['download_failed'] = download_stats['failed']

            return stats