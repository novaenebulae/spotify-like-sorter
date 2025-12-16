from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from src.database.models import Track, TrackAnalysis
from src.logger import logger


class TrackRepository:
    """CRUD pour les tracks"""

    def __init__(self, session: Session):
        self.session = session

    def create_track(self, track_data: Dict[str, Any]) -> Track:
        """Crée une track"""
        existing = self.session.query(Track).filter(
            Track.spotify_id == track_data['spotify_id']
        ).first()

        if existing:
            return existing

        track = Track(**track_data)
        self.session.add(track)
        self.session.flush()
        return track

    def create_many_tracks(self, tracks_data: List[Dict[str, Any]]) -> int:
        """Crée plusieurs tracks"""
        count = 0
        for track_data in tracks_data:
            existing = self.session.query(Track).filter(
                Track.spotify_id == track_data['spotify_id']
            ).first()

            if not existing:
                track = Track(**track_data)
                self.session.add(track)
                count += 1

        self.session.flush()
        logger.info(f"✅ {count} tracks créées")
        return count

    def get_track(self, spotify_id: str) -> Optional[Track]:
        """Récupère une track"""
        return self.session.query(Track).filter(
            Track.spotify_id == spotify_id
        ).first()

    def get_all_tracks(self) -> List[Track]:
        """Récupère toutes les tracks"""
        return self.session.query(Track).all()

    def get_unanalyzed_tracks(self, limit: Optional[int] = None) -> List[Track]:
        """Récupère les tracks non analysées"""
        query = self.session.query(Track).filter(~Track.analysis.any())
        if limit:
            query = query.limit(limit)
        return query.all()

    def count_all(self) -> int:
        """Compte le nombre total"""
        return self.session.query(Track).count()

    def count_analyzed(self) -> int:
        """Compte les analysées"""
        return self.session.query(Track).filter(Track.analysis.any()).count()


class AnalysisRepository:
    """CRUD pour les analyses"""

    def __init__(self, session: Session):
        self.session = session

    def create_analysis(self, spotify_id: str, status: str = "pending") -> TrackAnalysis:
        """Crée une analyse"""
        analysis = TrackAnalysis(
            spotify_id=spotify_id,
            analysis_status=status
        )
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def update_status(self, spotify_id: str, status: str, error_message: Optional[str] = None):
        """Met à jour le statut"""
        analysis = self.session.query(TrackAnalysis).filter(
            TrackAnalysis.spotify_id == spotify_id
        ).first()

        if analysis:
            analysis.analysis_status = status
            if error_message:
                analysis.error_message = error_message
            analysis.analysis_date = datetime.utcnow()
            self.session.flush()

    def get_by_status(self, status: str) -> list[TrackAnalysis]:
        """Récupère par statut"""
        return self.session.query(TrackAnalysis).filter(
            TrackAnalysis.analysis_status == status
        ).all()

    def get_stats(self) -> Dict[str, int]:
        """Retourne les stats"""
        statuses = ["pending", "processing", "completed", "failed"]
        stats = {}

        for status in statuses:
            count = self.session.query(TrackAnalysis).filter(
                TrackAnalysis.analysis_status == status
            ).count()
            stats[status] = count

        return stats

    def update_analysis(
            self,
            spotify_id: str,
            track_preview_url: Optional[str] = None,
            preview_local_path: Optional[str] = None,
            preview_source: Optional[str] = None,
            preview_fetched_at: Optional[datetime] = None,
            preview_status: Optional[str] = None,
            preview_error: Optional[str] = None,
            **kwargs
    ) -> TrackAnalysis:
        """
        Mettre à jour une analyse avec infos preview
        """
        analysis = self.session.query(TrackAnalysis).filter(
            TrackAnalysis.spotify_id == spotify_id
        ).first()

        if not analysis:
            raise ValueError(f"TrackAnalysis not found: {spotify_id}")

        if track_preview_url is not None:
            analysis.track_preview_url = track_preview_url
        if preview_local_path is not None:
            analysis.preview_local_path = preview_local_path
        if preview_source is not None:
            analysis.preview_source = preview_source
        if preview_fetched_at is not None:
            analysis.preview_fetched_at = preview_fetched_at
        if preview_status is not None:
            analysis.preview_status = preview_status
        if preview_error is not None:
            analysis.preview_error = preview_error

        analysis.updated_at = datetime.utcnow()

        return analysis

    def get_tracks_without_preview(self) -> List[TrackAnalysis]:
        """Récupérer tous les tracks sans preview"""
        return self.session.query(TrackAnalysis).filter(
            TrackAnalysis.preview_status == "pending"
        ).all()

    def get_preview_stats(self) -> Dict[str, int]:
        """Statistiques sur les previews"""
        return {
            'total': self.session.query(TrackAnalysis).count(),
            'fetched': self.session.query(TrackAnalysis).filter(
                TrackAnalysis.preview_status.in_(['fetched', 'downloaded'])
            ).count(),
            'deezer': self.session.query(TrackAnalysis).filter(
                TrackAnalysis.preview_source == 'deezer'
            ).count(),
            'itunes': self.session.query(TrackAnalysis).filter(
                TrackAnalysis.preview_source == 'itunes'
            ).count(),
            'not_found': self.session.query(TrackAnalysis).filter(
                TrackAnalysis.preview_status == 'not_found'
            ).count(),
            'downloaded': self.session.query(TrackAnalysis).filter(
                TrackAnalysis.preview_status == 'downloaded'
            ).count(),
        }