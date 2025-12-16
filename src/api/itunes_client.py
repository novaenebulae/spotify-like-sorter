"""
itunes_client.py - VERSION CORRIGÉE (Content-Type text/javascript fix)
Remplacer: src/api/itunes_client.py
"""

import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any

from src.config.retry_config import TIMEOUT_CONFIG, RETRY_ITUNES
from src.logger import logger
from src.cache.cache_manager import cache_manager

class iTunesClient:
    """Client pour iTunes Search API (fallback seulement)"""
    
    BASE_URL = "https://itunes.apple.com/search"
    TIMEOUT = TIMEOUT_CONFIG["itunes"]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @RETRY_ITUNES
    async def search_by_name(
        self,
        title: str,
        artist: str,
        track_id: str
    ) -> Optional[Dict[str, Any]]:
        """Chercher sur iTunes (fallback)"""
        if not title or not artist:
            return None
        
        cache_key = f"itunes_{title}_{artist}".replace(" ", "_")[:100]
        cached = cache_manager.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit (iTunes): {title}")
            return cached
        
        try:
            if not self.session:
                return None
            
            query = f"{title} {artist}"
            params = {
                "term": query,
                "entity": "song",
                "country": "fr",
                "limit": 5
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"iTunes HTTP {resp.status}")
                    return None
                
                # Utiliser text() au lieu de json()
                try:
                    content = await resp.text()
                    data = json.loads(content)  # Parser manuellement
                except json.JSONDecodeError as e:
                    logger.debug(f"iTunes JSON parse error: {e}")
                    return None
                except Exception as e:
                    logger.debug(f"iTunes error: {e}")
                    return None
                
                # Chercher preview
                for result in data.get("results", []):
                    if result.get("previewUrl"):
                        logger.debug(f"✅ iTunes: {track_id} → {result['previewUrl'][:50]}...")
                        result_dict = {
                            "preview_url": result["previewUrl"],
                            "source": "itunes"
                        }
                        cache_manager.set(cache_key, result_dict)
                        return result_dict
                
                return None
        
        except asyncio.TimeoutError:
            logger.debug(f"iTunes timeout: {title}")
            return None
        except Exception as e:
            logger.debug(f"iTunes error ({title}): {e}")
            return None
