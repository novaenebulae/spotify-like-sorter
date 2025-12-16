import sys
from pathlib import Path
from loguru import logger as _logger
from src.config.config import settings


def setup_logger():
    """Configure le logging centralisé"""

    # Enlever le handler par défaut
    _logger.remove()

    # Format personnalisé
    log_format = (
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Console
    _logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True
    )

    # Fichier
    _logger.add(
        settings.log_file,
        format=log_format,
        level=settings.log_level,
        rotation="500 MB",
        retention="10 days",
        compression="zip"
    )

    return _logger


logger = setup_logger()