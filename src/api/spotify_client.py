import asyncio

from typing import List, Dict, Optional, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.config.config import settings
from src.logger import logger
from src.api.exceptions import AuthenticationError, DataNotFoundError

from datetime import datetime, timezone


class SpotifyClient:
    """Client Spotify avec gestion OAuth"""

    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None):

        self.client_id = client_id or settings.spotify_client_id
        self.client_secret = client_secret or settings.spotify_client_secret
        self.redirect_uri = redirect_uri or settings.spotify_redirect_uri

        self.sp = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialise le client Spotipy"""
        try:
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=[
                    "user-library-read",
                    "playlist-modify-public",
                    "playlist-modify-private"
                ]
            )

            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("✅ Client Spotify initialisé")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            raise AuthenticationError(f"Impossible d'initialiser Spotify: {e}")

    def test_connection(self) -> bool:
        """Teste la connexion"""
        try:
            user = self.sp.current_user()
            logger.info(f"✅ Connecté: {user['display_name']}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            raise AuthenticationError(f"Authentification échouée: {e}")

    def get_current_user(self) -> Dict[str, Any]:
        """Récupère l'utilisateur actuel"""
        return self.sp.current_user()

    async def get_all_liked_tracks(self, progress_callback=None) -> List[Dict]:
        """Récupère TOUS les titres likés"""
        all_tracks = []
        offset = 0
        limit = settings.batch_size

        try:
            # Première requête pour connaître le total
            first_batch = self.sp.current_user_saved_tracks(limit=limit, offset=0)
            total_tracks = first_batch['total']

            logger.info(f"📊 Total: {total_tracks} tracks")

            # Pagination
            while offset < total_tracks:
                try:
                    batch = self.sp.current_user_saved_tracks(
                        limit=limit,
                        offset=offset
                    )

                    items = batch.get('items', [])
                    all_tracks.extend(items)

                    offset += limit

                    if progress_callback:
                        progress_callback(len(all_tracks), total_tracks)

                    logger.debug(f"Récupéré {len(all_tracks)}/{total_tracks}")

                    # Rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Erreur fetch: {e}")
                    raise

            logger.info(f"✅ Récupération: {len(all_tracks)} tracks")
            return all_tracks

        except Exception as e:
            logger.error(f"Erreur: {e}")
            raise

    def parse_track_data(self, track_item: Dict) -> Dict[str, Any]:
        """Parse un track item"""
        try:
            track = track_item.get('track', {})
            artists = [a['name'] for a in track.get('artists', [])]

            added_at_raw = track_item.get('added_at')
            added_at_dt = None
            if added_at_raw:
                # Spotify renvoie souvent une string ISO, ex: "2024-01-02T03:04:05Z"
                # datetime.fromisoformat accepte "+00:00" mais pas "Z"
                if isinstance(added_at_raw, str):
                    added_at_dt = datetime.fromisoformat(added_at_raw.replace("Z", "+00:00"))
                elif isinstance(added_at_raw, datetime):
                    added_at_dt = added_at_raw

                # Optionnel: normaliser en UTC naive (souvent plus simple côté SQLite)
                if isinstance(added_at_dt, datetime) and added_at_dt.tzinfo is not None:
                    added_at_dt = added_at_dt.astimezone(timezone.utc).replace(tzinfo=None)

            return {
                'spotify_id': track.get('id'),
                'title': track.get('name'),
                'artist': artists[0] if artists else 'Unknown',
                'artists_list': artists,
                'album': track.get('album', {}).get('name'),
                'duration_ms': track.get('duration_ms'),
                'popularity': track.get('popularity'),
                'isrc': track.get('external_ids', {}).get('isrc'),
                'uri': track.get('uri'),
                'added_at': added_at_dt,
                'preview_url': track.get('preview_url'),
                'explicit': track.get('explicit')
            }

        except Exception as e:
            logger.error(f"Erreur parsing: {e}")
            raise
