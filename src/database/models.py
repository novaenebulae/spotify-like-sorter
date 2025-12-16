from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Boolean, JSON, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Track(Base):
    __tablename__ = "tracks"

    spotify_id = Column(String(50), primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    artist = Column(String(300), nullable=False)
    artists_list = Column(JSON)
    album = Column(String(300))
    duration_ms = Column(Integer)
    popularity = Column(Integer)
    isrc = Column(String(50), index=True)
    uri = Column(String(300))
    preview_url = Column(String(500))
    explicit = Column(Boolean, default=False)

    added_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analysis = relationship("TrackAnalysis", uselist=False, back_populates="track")
    track_metadata = relationship("TrackMetadata", uselist=False, back_populates="track")


class TrackAnalysis(Base):
    __tablename__ = "track_analyses"

    id = Column(Integer, primary_key=True)
    spotify_id = Column(String(50), ForeignKey("tracks.spotify_id"), unique=True)

    track_preview_url = Column(String(500), nullable=True)
    preview_local_path = Column(String(500), nullable=True)
    preview_source = Column(String(20), nullable=True)
    preview_fetched_at = Column(DateTime, nullable=True)

    analysis_status = Column(String(20), default="pending", index=True)
    preview_status = Column(String(20), default="pending")

    preview_error = Column(Text, nullable=True)
    error_message = Column(Text)

    analysis_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    track = relationship("Track", back_populates="analysis")

    def __repr__(self):
        return f"<TrackAnalysis(id={self.id}, status={self.analysis_status}, preview={self.preview_status})>"

class TrackMetadata(Base):
    __tablename__ = "metadatas"

    id = Column(Integer, primary_key=True)
    spotify_id = Column(String(50), ForeignKey("tracks.spotify_id"), unique=True)

    genre_discogs_519 = Column(JSON)
    genre_confidence = Column(Float)
    arousal_valence = Column(JSON)
    engagement = Column(Float)
    danceability = Column(Boolean)

    tempo_bpm = Column(Integer)
    timbre = Column(String(20))
    is_acoustic = Column(Boolean)
    is_electronic = Column(Boolean)
    has_voice = Column(Boolean)
    voice_gender = Column(String(20))

    is_aggressive = Column(Boolean)
    is_happy = Column(Boolean)
    is_party = Column(Boolean)
    is_relaxed = Column(Boolean)
    is_sad = Column(Boolean)

    mood_mirex = Column(String(50))
    mood_jamendo = Column(JSON)
    instruments = Column(JSON)
    is_tonal = Column(Boolean)

    maest_embedding = Column(JSON)
    effnet_embedding = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    track = relationship("Track", back_populates="track_metadata")


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True)
    spotify_playlist_id = Column(String(50), unique=True)
    name = Column(String(300), nullable=False)
    description = Column(Text)

    criteria = Column(JSON)
    track_count = Column(Integer, default=0)
    synced_to_spotify = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)