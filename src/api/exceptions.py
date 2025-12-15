class SpotifyAPIError(Exception):
    """Erreur API Spotify générique"""
    pass

class AuthenticationError(SpotifyAPIError):
    """Erreur d'authentification"""
    pass

class RateLimitError(SpotifyAPIError):
    """Rate limit dépassé"""
    pass

class TokenRefreshError(SpotifyAPIError):
    """Erreur lors du refresh du token"""
    pass

class DataNotFoundError(SpotifyAPIError):
    """Données non trouvées"""
    pass