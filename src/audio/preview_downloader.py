"""
Téléchargement asynchrone des previews audio
"""

import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from src.config.retry_config import RETRY_DOWNLOAD, TIMEOUT_CONFIG
from src.logger import logger



class PreviewDownloader:
    """Télécharge et stocke les previews MP3"""

    def __init__(self, output_dir: Path = None, max_concurrent: int = 10):
        """
        Initialiser le downloader

        Args:
            output_dir: Dossier de destination (défaut: ./previews/)
            max_concurrent: Nombre de téléchargements simultanés
        """
        self.TIMEOUT = TIMEOUT_CONFIG['download']

        self.output_dir = output_dir or Path("previews")
        self.max_concurrent = max_concurrent
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"PreviewDownloader initialisé: {self.output_dir}")

    def get_preview_path(self, track_id: str) -> Path:
        """Chemin de destination pour un preview"""
        return self.output_dir / f"{track_id}.mp3"

    @RETRY_DOWNLOAD
    async def download(
            self,
            track_id: str,
            preview_url: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Télécharger un preview

        Args:
            track_id: ID Spotify
            preview_url: URL du preview

        Returns:
            (success: bool, error_message: Optional[str])
        """
        output_path = self.get_preview_path(track_id)

        # Vérifier si déjà téléchargé
        if output_path.exists() and output_path.stat().st_size > 10000:
            logger.debug(f"Preview déjà présent: {track_id}")
            return True, None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        preview_url,
                        timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
                ) as resp:

                    if resp.status != 200:
                        error = f"HTTP {resp.status}"
                        logger.warning(f"Download error ({track_id}): {error}")
                        return False, error

                    # Télécharger contenu
                    content = await resp.read()

                    # Vérifier taille (preview = ~200-400 KB)
                    if len(content) < 10000:  # < 10 KB = suspect
                        error = f"Fichier trop petit ({len(content)} bytes)"
                        logger.warning(f"Download warning ({track_id}): {error}")
                        return False, error

                    if len(content) > 10 * 1024 * 1024:  # > 10 MB = suspect
                        error = f"Fichier trop gros ({len(content)} bytes)"
                        logger.warning(f"Download warning ({track_id}): {error}")
                        return False, error

                    # Écrire fichier
                    with open(output_path, 'wb') as f:
                        f.write(content)

                    logger.info(f"✅ Downloaded: {track_id} ({len(content) / 1024:.1f} KB)")
                    return True, None

        except asyncio.TimeoutError:
            error = "Timeout"
            logger.warning(f"Download timeout ({track_id})")
            return False, error
        except Exception as e:
            error = str(e)
            logger.error(f"Download error ({track_id}): {error}")
            return False, error

    async def download_batch(
            self,
            tracks: List[Dict]
    ) -> Dict[str, any]:
        """
        Télécharger plusieurs previews en parallèle

        Args:
            tracks: Liste de {'track_id': '', 'preview_url': ''}

        Returns:
            {
                'total': int,
                'success': int,
                'failed': int,
                'errors': {track_id: error_msg},
                'downloaded_files': {track_id: local_path}  # ← NOUVEAU!
            }
        """

        logger.info(f"🚀 Starting batch download: {len(tracks)} tracks")

        # Créer semaphore pour limiter concurrence
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_limit(track: Dict):
            async with semaphore:
                return await self.download(
                    track['track_id'],
                    track['preview_url']
                )

        # Télécharger tous
        results = await asyncio.gather(
            *[download_with_limit(track) for track in tracks],
            return_exceptions=True
        )

        # Parser résultats
        stats = {
            'total': len(tracks),
            'success': 0,
            'failed': 0,
            'errors': {},
            'downloaded_files': {}  # ← NOUVEAU: Stocker les chemins!
        }

        for i, (track, result) in enumerate(zip(tracks, results)):
            track_id = track['track_id']

            if isinstance(result, Exception):
                stats['failed'] += 1
                stats['errors'][track_id] = str(result)
            else:
                success, error = result

                if success:
                    stats['success'] += 1
                    local_path = self.get_preview_path(track_id)
                    stats['downloaded_files'][track_id] = str(local_path)
                else:
                    stats['failed'] += 1
                    if error:
                        stats['errors'][track_id] = error

            # Progress
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i + 1}/{len(tracks)}")

        logger.info(f"✅ Batch complete: {stats['success']} success, {stats['failed']} failed")

        return stats

    def verify_all(self) -> Dict[str, any]:
        """
        Vérifier tous les fichiers téléchargés

        Returns:
            {
                'total_files': int,
                'total_size_mb': float,
                'avg_size_kb': float,
                'min_size_kb': float,
                'max_size_kb': float,
                'status': 'OK' ou 'WARNING'
            }
        """
        files = list(self.output_dir.glob("*.mp3"))

        if not files:
            logger.warning("Aucun fichier trouvé!")
            return {'status': 'ERROR', 'total_files': 0}

        sizes = [f.stat().st_size for f in files]
        total_size = sum(sizes)

        stats = {
            'total_files': len(files),
            'total_size_mb': total_size / (1024 * 1024),
            'avg_size_kb': sum(sizes) / len(sizes) / 1024,
            'min_size_kb': min(sizes) / 1024,
            'max_size_kb': max(sizes) / 1024,
            'status': 'OK'
        }

        # Warnings
        if stats['avg_size_kb'] < 100:
            logger.warning(f"⚠️ Taille moyenne faible: {stats['avg_size_kb']:.1f} KB")
            stats['status'] = 'WARNING'

        logger.info(f"Verification: {stats['total_files']} files, {stats['total_size_mb']:.1f} MB total")
        return stats