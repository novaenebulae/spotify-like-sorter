"""
retry_config.py - COPIER DANS: src/config/retry_config.py
Gestion intelligente des timeouts et retry logic
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception
)
import asyncio

# ============ CONFIGURATION ============

TIMEOUT_CONFIG = {
    "deezer": 10,      # Deezer = endpoint direct = rapide
    "itunes": 15,      # iTunes = peut être lent
    "download": 30     # Téléchargement = peut prendre du temps
}

# ============ RETRY LOGIC ============

def create_retry_decorator(max_attempts=4):
    """
    Crée un décorateur de retry avec exponential backoff
    
    Comportement:
    - Tentative 1: Immediate (fail fast)
    - Tentative 2: Attendre 1 sec
    - Tentative 3: Attendre 2 sec
    - Tentative 4: Attendre 4 sec
    
    Max: 4 tentatives
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            asyncio.TimeoutError,
            ConnectionError,
            OSError
        )),
        reraise=True  # Re-lever l'exception après échec final
    )

# Décorateurs prêts à utiliser
RETRY_DEEZER = create_retry_decorator(max_attempts=4)
RETRY_ITUNES = create_retry_decorator(max_attempts=4)
RETRY_DOWNLOAD = create_retry_decorator(max_attempts=3)  # Downloads plus agressif

# ============ USAGE ============

"""
Utilisation:

@RETRY_DEEZER
async def search_by_isrc(self, isrc: str):
    # Cette fonction reessayera automatiquement
    # en cas de timeout ou ConnectionError
    ...

Logs générés automatiquement:
- Tentative 1: Fail → Retry in 1s
- Tentative 2: Fail → Retry in 2s
- Tentative 3: Fail → Retry in 4s
- Tentative 4: Fail → Exception
"""
