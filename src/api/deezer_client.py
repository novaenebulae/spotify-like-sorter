"""
deezer_client.py - VERSION CORRIGÉE AVEC BON ENDPOINT
Remplacer: src/api/deezer_client.py
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any

from src.config.retry_config import TIMEOUT_CONFIG, RETRY_DEEZER
from src.logger import logger
from src.cache.cache_manager import cache_manager

class DeezerClient:
    """Client pour Deezer API - Recherche previews"""
    
    SEARCH_URL = "https://api.deezer.com/search"
    TRACK_URL = "https://api.deezer.com/2.0/track"
    TIMEOUT = TIMEOUT_CONFIG["deezer"]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @RETRY_DEEZER
    async def search_by_isrc(self, isrc: str, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Chercher par ISRC - Endpoint DIRECT
        
        Utilise: https://api.deezer.com/2.0/track/isrc:XXXXX
        """
        if not isrc or len(isrc) < 5:
            return None
        
        cache_key = f"deezer_isrc_{isrc}"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.debug(f"Cache hit (ISRC): {isrc}")
            return cached
        
        try:
            # ✅ ENDPOINT DIRECT - Plus fiable que /search
            url = f"{self.TRACK_URL}/isrc:{isrc}"
            
            if not self.session:
                return None
            
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Vérifier preview
                    if data.get("preview"):
                        logger.debug(f"✅ Deezer (ISRC direct): {track_id} → {data['preview'][:50]}...")
                        result = {
                            "preview_url": data["preview"],
                            "source": "deezer"
                        }
                        cache_manager.set(cache_key, result)
                        return result
                    else:
                        logger.debug(f"❌ Deezer ISRC found but no preview: {isrc}")
                        return None
                
                elif resp.status == 404:
                    logger.debug(f"❌ Deezer ISRC not found: {isrc}")
                    return None
                else:
                    logger.debug(f"Deezer ISRC HTTP {resp.status}")
                    return None
        
        except asyncio.TimeoutError:
            logger.debug(f"Deezer ISRC timeout: {isrc}")
            return None
        except Exception as e:
            logger.debug(f"Deezer ISRC error: {e}")
            return None
    
    async def search_by_name(
        self,
        title: str,
        artist: str,
        track_id: str
    ) -> Optional[Dict[str, Any]]:
        """Chercher par titre+artiste (fallback)"""
        if not title or not artist:
            return None
        
        cache_key = f"deezer_name_{title}_{artist}".replace(" ", "_")[:100]
        cached = cache_manager.get(cache_key)
        if cached:
            logger.debug(f"Cache hit (Name): {title}")
            return cached
        
        try:
            # Requête Deezer par titre+artiste
            query = f"track:{title} artist:{artist}"
            params = {"q": query}
            result = await self._search_request(params)
            
            if result:
                logger.debug(f"✅ Deezer (Name): {track_id} → {result['preview_url'][:50]}...")
                cache_manager.set(cache_key, result)
                return result
        
        except Exception as e:
            logger.debug(f"Deezer Name error: {e}")
        
        return None
    
    async def _search_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Requête à Deezer /search endpoint"""
        if not self.session:
            return None
        
        try:
            async with self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"Deezer search HTTP {resp.status}")
                    return None
                
                data = await resp.json()
                
                # Parser réponse
                if data.get("data") and len(data["data"]) > 0:
                    track = data["data"][0]
                    
                    # Vérifier preview
                    if track.get("preview"):
                        return {
                            "preview_url": track["preview"],
                            "source": "deezer"
                        }
                
                return None
        
        except asyncio.TimeoutError:
            logger.debug("Deezer search timeout")
            return None
        except Exception as e:
            logger.debug(f"Deezer search error: {e}")
            return None
    
    async def search(
        self,
        isrc: Optional[str] = None,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Recherche intelligente: ISRC (direct) → Nom → None
        
        ✅ Priorité: ISRC direct endpoint (plus fiable)
        """
        # 1. Essayer ISRC avec endpoint direct (TRÈS fiable)
        if isrc:
            result = await self.search_by_isrc(isrc, track_id or "unknown")
            if result:
                return result
        
        # 2. Essayer titre+artiste (fallback)
        if title and artist:
            result = await self.search_by_name(title, artist, track_id or "unknown")
            if result:
                return result
        
        return None
