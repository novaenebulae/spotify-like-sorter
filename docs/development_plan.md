# Plan de Développement - Spotify Auto Like Sorter
## Application de Tri Automatique des Titres Likés Spotify

---

## 📋 Vue d'ensemble du projet

**Objectif**: Créer une application Python complète permettant de récupérer, analyser et organiser automatiquement les ~5000 titres likés Spotify en playlists intelligentes basées sur l'analyse audio.

**Architecture générale**:
```
Spotify API → Récupération des titres
    ↓
Deezer API → Récupération des previews 30s
    ↓
Essentia ML → Analyse audio (13+ modèles)
    ↓
Base de données/Cache → Stockage des analyses
    ↓
Agrégation → Clustering et création de playlists
    ↓
GUI → Gestion et export vers Spotify
```

---

## 🎯 Phase 1: Récupération et Stockage des Titres Likés

### 1.1 Configuration Spotify API
**Durée estimée**: 2-3 jours  
**Dépendances**: `spotipy`, `requests-oauthlib`

#### Tâches:
- [ ] Enregistrement de l'application sur Spotify Developer Dashboard
- [ ] Implémentation de l'authentification OAuth 2.0
- [ ] Création de la classe `SpotifyClient`:
  - Gestion du token d'accès et refresh
  - Pagination pour récupérer les 5000+ titres likés
  - Gestion des rate limits (API Spotify: 429 errors)
- [ ] Tests de connexion et récupération des données

#### Structure des données récupérées:
```python
{
    'track_id': str,           # Identifiant unique Spotify
    'title': str,
    'artist': str,
    'artists_list': list,
    'album': str,
    'duration_ms': int,
    'added_at': datetime,
    'popularity': int,          # 0-100
    'isrc': str,                # Code pour chercher sur Deezer
    'uri': str                  # Pour créer playlists
}
```

### 1.2 Implémentation de la Base de Données/Cache
**Durée estimée**: 2-3 jours  
**Dépendances**: `sqlalchemy`, `sqlite3`, `pickle` (caching local)

#### Options recommandées:
1. **SQLite** (développement): Simple, fichier local
2. **PostgreSQL** (production): Plus robuste
3. **Cache Redis** (optionnel): Pour accès rapide aux données analysées

#### Schéma de base de données:
```sql
-- Table principale des titres
CREATE TABLE tracks (
    id TEXT PRIMARY KEY,
    spotify_id TEXT UNIQUE,
    title TEXT,
    artist TEXT,
    album TEXT,
    duration_ms INTEGER,
    added_at TIMESTAMP,
    popularity INTEGER,
    isrc TEXT,
    uri TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour stocker les analyses
CREATE TABLE track_analyses (
    id INTEGER PRIMARY KEY,
    spotify_id TEXT FOREIGN KEY,
    analysis_date TIMESTAMP,
    deezer_preview_url TEXT,
    analysis_status ENUM('pending', 'analyzing', 'completed', 'failed'),
    error_message TEXT,
    created_at TIMESTAMP
);

-- Table pour les métadonnées Essentia
CREATE TABLE track_metadata (
    id INTEGER PRIMARY KEY,
    spotify_id TEXT FOREIGN KEY,
    -- Genre (Discogs 519)
    genre_discogs519 JSON,
    genre_confidence FLOAT,
    -- Moods
    arousal_valence_deam JSON,
    engagement_level FLOAT,
    approachability FLOAT,
    danceability BOOLEAN,
    -- Audio properties
    tempo_bpm INTEGER,
    timbre TEXT,  -- 'bright' ou 'dark'
    is_acoustic BOOLEAN,
    is_electronic BOOLEAN,
    has_voice BOOLEAN,
    voice_gender TEXT,  -- 'male', 'female', 'mixed'
    -- Moods spécifiques
    is_aggressive BOOLEAN,
    is_happy BOOLEAN,
    is_party BOOLEAN,
    is_relaxed BOOLEAN,
    is_sad BOOLEAN,
    mirex_mood TEXT,
    jamendo_mood JSON,
    -- Instrumentation
    instruments JSON,
    instrument_role TEXT,  -- 'bass', 'melody', etc
    -- Tonalité
    is_tonal BOOLEAN,
    -- Embeddings
    discogs_effnet_embedding BLOB,
    maest_embedding BLOB,
    created_at TIMESTAMP
);

-- Table des playlists créées
CREATE TABLE playlists (
    id INTEGER PRIMARY KEY,
    spotify_playlist_id TEXT UNIQUE,
    name TEXT,
    description TEXT,
    criteria JSON,  -- Paramètres utilisés pour la création
    track_count INTEGER,
    created_at TIMESTAMP,
    synced_to_spotify BOOLEAN DEFAULT FALSE
);

-- Table de jointure tracks <-> playlists
CREATE TABLE playlist_tracks (
    playlist_id INTEGER,
    track_id TEXT,
    added_at TIMESTAMP,
    PRIMARY KEY (playlist_id, track_id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id),
    FOREIGN KEY (track_id) REFERENCES tracks(spotify_id)
);
```

### 1.3 Système de Caching
**Durée estimée**: 1-2 jours

#### Implémentation:
- [ ] Cache en mémoire (Python dict + TTL)
- [ ] Cache disque (pickle pour data volumineuses)
- [ ] Invalidation automatique
- [ ] Logging des hits/misses

```python
class CacheManager:
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = cache_dir
        self.memory_cache = {}
        self.ttl = 3600  # 1 heure
    
    def get(self, key): ...
    def set(self, key, value): ...
    def invalidate(self, key): ...
    def clear_expired(self): ...
```

---

## 🎵 Phase 2: Récupération des Previews et Analyse Audio

### 2.1 Intégration Deezer API
**Durée estimée**: 2-3 jours  
**Dépendances**: `requests`

**⚠️ Limitation importante**: L'API Deezer public retourne UNIQUEMENT les previews 30s (pas de flux complets sans authentification premium).

#### Tâches:
- [ ] Enregistrement Deezer Developer
- [ ] Implémentation de `DeezerClient`:
  - Recherche par ISRC (International Standard Recording Code)
  - Recherche par titre + artiste (fallback)
  - Gestion des erreurs (track non trouvée)
  - Stockage des URLs de preview
- [ ] Gestion des préviews manquantes (fallback: synthèse audio?)

```python
class DeezerClient:
    async def get_preview(self, track_data):
        """
        Cherche le preview Deezer d'une track Spotify
        Stratégies:
        1. Recherche par ISRC (+ fiable)
        2. Recherche par titre + artiste
        3. Retourne None si non trouvée
        """
        ...
    
    async def fetch_previews_batch(self, tracks, max_workers=5):
        """Récupération parallèle pour 5000 tracks"""
        ...
```

### 2.2 Téléchargement et Gestion des Previews
**Durée estimée**: 1-2 jours

- [ ] Téléchargement des 30s en MP3
- [ ] Stockage optimisé (répertoire local ou cloud)
- [ ] Gestion de l'espace disque (5000 × 1-2MB = 5-10GB)
- [ ] Nettoyage automatique des anciens fichiers

### 2.3 Intégration Essentia
**Durée estimée**: 3-5 jours  
**Dépendances**: `essentia-tensorflow`, `tensorflow>=2.10`, `numpy`, `librosa`

#### Installation:
```bash
pip install essentia-tensorflow tensorflow==2.13.0
```

#### Modèles à télécharger:
```python
MODELS_TO_USE = {
    # Genre
    'genre_discogs_400': 'genre-discogs400-musicnn-1',
    'genre_discogs_519': 'genre-discogs519-musicnn-1',
    
    # Moods & Context
    'approachability': 'approachability_2c-musicnn-1',
    'engagement': 'engagement_2c-musicnn-1',
    'arousal_valence_deam': 'arousal_valence_deam-musicnn-1',
    'danceability': 'danceability-musicnn-1',
    
    # Mood specific
    'mood_aggressive': 'mood_aggressive-musicnn-1',
    'mood_happy': 'mood_happy-musicnn-1',
    'mood_party': 'mood_party-musicnn-1',
    'mood_relaxed': 'mood_relaxed-musicnn-1',
    'mood_sad': 'mood_sad-musicnn-1',
    'moods_mirex': 'moods_mirex-musicnn-1',
    
    # Audio properties
    'voice_instrumental': 'voice_instrumental-musicnn-1',
    'voice_gender': 'voice_gender-musicnn-1',
    'acoustic_electronic_nsynth': 'nsynth_acoustic_electronic-musicnn-1',
    'timbre': 'timbre-musicnn-1',
    
    # Tempo
    'tempocnn': 'deepsquare_k16-v2-1',
    
    # Embeddings
    'discogs_effnet': 'discogs-effnet-bs64-1',
    'maest_30s': 'discogs-maest-30s-pw-1'
}
```

#### Architecture du module d'analyse:
```python
class AudioAnalyzer:
    def __init__(self, models_dir='./models'):
        self.models = {}
        self.load_models()
    
    def load_models(self):
        """Charge tous les modèles Essentia au démarrage"""
        ...
    
    async def analyze_track(self, audio_path: str) -> dict:
        """
        Analyse audio complète d'une track
        Retourne tous les descripteurs high-level
        """
        # 1. Charger audio
        # 2. Extraire embeddings (MAEST, EffNet)
        # 3. Classifier avec tous les modèles
        # 4. Extraire caractéristiques bas-niveau
        # 5. Retourner dictionnaire complet
        ...
    
    def extract_embeddings(self, audio):
        """Extrait MAEST et EffNet embeddings"""
        ...
    
    def run_classifiers(self, embeddings) -> dict:
        """Lance tous les classifiers en parallèle"""
        ...
    
    def extract_low_level_features(self, audio) -> dict:
        """
        Caractéristiques bas-niveau:
        - Tempo (via TempoCNN ou extraction)
        - Loudness
        - Zero crossing rate
        - Spectral centroid
        - etc.
        """
        ...
```

#### Pipeline d'analyse complet:
```python
class AnalysisPipeline:
    async def process_track(self, track_data, preview_path):
        """
        Pipeline complet pour une track:
        1. Vérifier cache
        2. Charger audio
        3. Analyser
        4. Stocker en BD
        5. Retourner métadonnées
        """
        ...
    
    async def batch_process(self, tracks, max_workers=4):
        """
        Traitement par batch (4 analyses parallèles max)
        Chaque worker traite 1 track = 1-2 min
        ~5000 tracks = 1000-2000 min = 16-33 heures
        """
        ...
    
    def add_progress_callback(self, callback):
        """Pour l'UI: feedback de progression"""
        ...
```

---

## 🧠 Phase 3: Agrégation et Création de Playlists

### 3.1 Système de Clustering et Similarité
**Durée estimée**: 3-4 jours  
**Dépendances**: `scikit-learn`, `scipy`, `numpy`

#### Stratégies de clustering:
1. **Clustering simple** (K-Means):
   - Basé sur embeddings MAEST/EffNet
   - K variable (5-20 clusters)
   - Rapide et déterministe

2. **Clustering hiérarchique**:
   - Pour playlists imbriquées
   - Dendrogramme pour explorer

3. **Graph-based clustering**:
   - Construction d'un graph de similarité
   - Community detection (Louvain)

```python
class PlaylistAggregator:
    def __init__(self, metadata_db):
        self.metadata = metadata_db
        self.scaler = StandardScaler()
    
    def create_feature_matrix(self, tracks_metadata):
        """
        Crée une matrice de features:
        - Embeddings (MAEST: 512-dim)
        - Genre probabilities
        - Mood scores (arousal, valence, engagement)
        - Audio properties (tempo, timbre, etc)
        
        Output: (n_tracks, n_features)
        """
        ...
    
    def compute_similarity(self, feature_matrix, metric='cosine'):
        """Calcule matrice de similarité"""
        ...
    
    def cluster_kmeans(self, feature_matrix, n_clusters=10):
        """K-Means clustering"""
        ...
    
    def cluster_hierarchical(self, feature_matrix, n_clusters=10):
        """Clustering hiérarchique"""
        ...
    
    def suggest_playlist_name(self, cluster_tracks):
        """
        Génère des noms de playlist intelligents:
        - Basé sur genres dominants
        - Basé sur moods dominants
        - Basé sur caractéristiques audio
        
        Ex: "Chill Electronic Vibes", "Party Hit Energy", etc.
        """
        ...
```

### 3.2 Paramètres de Création Personnalisables
**Durée estimée**: 1-2 jours

#### Presets prédéfinis:
```python
PRESETS = {
    'energy_based': {
        'description': 'Trier par niveau d\'énergie',
        'criteria': ['arousal', 'tempo_bpm'],
        'n_playlists': 5,
        'names': ['Sleepy Time', 'Chill', 'Moderate', 'Energetic', 'Party']
    },
    'mood_based': {
        'description': 'Trier par humeur',
        'criteria': ['valence', 'arousal'],
        'n_playlists': 4,
        'names': ['Sad & Introspective', 'Happy & Uplifting', 'Angry & Intense', 'Calm & Peaceful']
    },
    'genre_clustering': {
        'description': 'Trier par genre + similarité',
        'criteria': ['genre_discogs_519', 'embeddings_maest'],
        'n_playlists': 'auto',  # Basé sur nombre de genres
    },
    'activity_based': {
        'description': 'Trier par activité',
        'criteria': ['engagement', 'danceability'],
        'n_playlists': 4,
        'names': ['Background Listening', 'Casual Listening', 'Active Listening', 'Dance Floor']
    }
}
```

#### Interface de personnalisation:
```python
class PlaylistConfig:
    def __init__(self):
        self.preset = None  # Ou paramètres custom
        self.criteria = []  # Colonnes à utiliser
        self.n_playlists = 10
        self.playlist_names = []
        self.min_tracks_per_playlist = 5
        self.max_tracks_per_playlist = 500
    
    @staticmethod
    def from_preset(preset_name):
        """Crée config à partir d'un preset"""
        ...
    
    def validate(self):
        """Valide les paramètres"""
        ...
```

### 3.3 Module de Création de Playlists Spotify
**Durée estimée**: 2 jours

```python
class SpotifyPlaylistManager:
    def __init__(self, spotify_client):
        self.client = spotify_client
    
    async def create_playlist(self, name, description, track_ids):
        """Crée une playlist Spotify"""
        ...
    
    async def add_tracks_to_playlist(self, playlist_id, track_ids):
        """
        Ajoute les tracks
        Attention: limite API de 100 tracks par requête
        """
        ...
    
    async def sync_playlists(self, playlist_configs):
        """
        Crée/met à jour toutes les playlists
        Stocke les IDs Spotify en base de données
        """
        ...
    
    async def remove_track_from_liked(self, track_id):
        """
        Optionnel: supprime la track des Liked
        après qu'elle soit traitée et déplacée
        """
        ...
```

---

## 🎨 Phase 4: Interface Utilisateur (GUI)

### 4.1 Framework GUI
**Durée estimée**: 4-6 jours  
**Dépendances**: `PyQt6`, `PyQt6-Charts`, `pyqtgraph`

Options:
- **PyQt6**: Moderne, riche en widgets, cross-platform
- **tkinter**: Plus léger, inclus dans Python
- **PySimpleGUI**: Très facile mais moins flexible

**Recommandation**: PyQt6 pour meilleur UX/UI

### 4.2 Écrans Principaux

#### 1. **Écran de Connexion Spotify**
- [ ] OAuth login
- [ ] Affichage des permissions requises
- [ ] Gestion des tokens

#### 2. **Écran de Récupération des Titres**
- [ ] Bouton "Récupérer mes titres likés"
- [ ] Barre de progression
- [ ] Affichage du nombre de titres
- [ ] Log des erreurs

#### 3. **Écran d'Analyse Audio**
- [ ] Bouton "Analyser les previews"
- [ ] Barre de progression par étapes:
  - Récupération Deezer
  - Téléchargement audio
  - Analyse Essentia
- [ ] Filtres (ex: "Analyser seulement les non-analysés")
- [ ] Statistiques (% complété, temps estimé restant)

#### 4. **Écran de Création de Playlists**
- [ ] Dropdown des presets
- [ ] Paramètres personnalisables:
  - Nombre de playlists
  - Critères de tri
  - Noms des playlists
- [ ] Preview du résultat
- [ ] Bouton "Créer les playlists"

#### 5. **Écran de Gestion des Playlists**
- [ ] Tableau des playlists créées
- [ ] Nombre de tracks par playlist
- [ ] Actions:
  - Aperçu des tracks
  - Suppression
  - Modification des noms
  - Synchronisation Spotify
- [ ] Gestion des likes (supprimer après placement?)

#### 6. **Écran de Statistiques & Dashboard**
- [ ] Graphiques:
  - Distribution des genres
  - Distribution des moods (arousal/valence)
  - Distribution du tempo
  - Acoustique vs. Électronique
- [ ] Statistiques globales
- [ ] Export en CSV/JSON

### 4.3 Architecture PyQt6
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_workers()
    
    def init_ui(self):
        """Initialise l'interface"""
        self.central_widget = QWidget()
        self.layout = QStackedLayout()
        
        # Écrans
        self.login_screen = LoginScreen()
        self.fetch_screen = FetchTracksScreen()
        self.analysis_screen = AnalysisScreen()
        self.playlist_screen = PlaylistScreen()
        self.management_screen = PlaylistManagementScreen()
        self.stats_screen = StatsScreen()
        
        # Navigation
        self.sidebar = NavigationSidebar()
        self.sidebar.connect_signals()
        
    def setup_workers(self):
        """Threads workers pour opérations longues"""
        self.fetch_worker = FetchWorker()
        self.analysis_worker = AnalysisWorker()
        self.playlist_worker = PlaylistCreationWorker()
```

### 4.4 Workers (Threading)
```python
class FetchWorker(QObject):
    """Récupère les titres likés sans bloquer l'UI"""
    progress = pyqtSignal(int)  # %
    finished = pyqtSignal(list)  # Tracks list
    error = pyqtSignal(str)
    
    def run(self):
        try:
            tracks = self.spotify_client.get_liked_tracks()
            self.finished.emit(tracks)
        except Exception as e:
            self.error.emit(str(e))

class AnalysisWorker(QObject):
    """Lance l'analyse audio"""
    progress = pyqtSignal(int, int)  # current, total
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    
    def run(self):
        ...

class PlaylistCreationWorker(QObject):
    """Crée les playlists sur Spotify"""
    progress = pyqtSignal(int, int)
    playlist_created = pyqtSignal(str, str)  # nom, id
    finished = pyqtSignal()
    ...
```

---

## 📦 Phase 5: Configuration et Déploiement

### 5.1 Gestion des Dépendances
**Durée estimée**: 1 jour

```txt
# requirements.txt
# API & Web
spotipy==2.23.0
requests==2.31.0
requests-oauthlib==1.3.0
aiohttp==3.9.0

# Audio Analysis
essentia-tensorflow==2.1.0
tensorflow==2.13.0
numpy==1.24.3
scipy==1.11.0
librosa==0.10.0
soundfile==0.12.1

# ML & Data
scikit-learn==1.3.0
pandas==2.0.3
numpy==1.24.3

# Database
sqlalchemy==2.0.20
alembic==1.11.3

# GUI
PyQt6==6.5.2
PyQt6-Charts==6.5.2
pyqtgraph==0.13.3

# Utilities
python-dotenv==1.0.0
pyyaml==6.0
tqdm==4.66.1
loguru==0.7.0
pydantic==2.0.3

# Development
pytest==7.4.0
pytest-asyncio==0.21.1
black==23.7.0
isort==5.12.0
mypy==1.4.1
```

### 5.2 Configuration et Variables d'Environnement
**Durée estimée**: 1 jour

```bash
# .env
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

DEEZER_APP_ID=...
DEEZER_APP_SECRET=...

# Database
DATABASE_URL=sqlite:///./spotify_analyzer.db

# Chemins
CACHE_DIR=./cache
MODELS_DIR=./models
PREVIEW_DIR=./previews
LOG_DIR=./logs

# Configuration
LOG_LEVEL=INFO
MAX_WORKERS=4
BATCH_SIZE=32
```

### 5.3 Structure du Projet
```
spotify-auto-like-sorter/
├── src/
│   ├── __init__.py
│   ├── main.py                      # Point d'entrée
│   ├── config.py                    # Configuration
│   ├── logger.py                    # Logging
│   │
│   ├── api/
│   │   ├── spotify_client.py        # Client Spotify
│   │   ├── deezer_client.py         # Client Deezer
│   │   └── oauth_handler.py         # Gestion OAuth
│   │
│   ├── audio/
│   │   ├── analyzer.py              # Moteur d'analyse
│   │   ├── essentia_models.py       # Modèles Essentia
│   │   ├── feature_extractor.py     # Extraction features
│   │   └── audio_processor.py       # Traitement audio
│   │
│   ├── database/
│   │   ├── models.py                # Schéma SQLAlchemy
│   │   ├── repository.py            # CRUD operations
│   │   └── migrations/              # Alembic migrations
│   │
│   ├── playlist/
│   │   ├── aggregator.py            # Clustering & agrégation
│   │   ├── playlist_manager.py      # Gestion playlists Spotify
│   │   └── presets.py               # Presets prédéfinis
│   │
│   ├── cache/
│   │   ├── cache_manager.py         # Gestion cache
│   │   └── decorators.py            # @cache decorators
│   │
│   ├── gui/
│   │   ├── main_window.py           # Fenêtre principale
│   │   ├── screens/
│   │   │   ├── login.py
│   │   │   ├── fetch_tracks.py
│   │   │   ├── analysis.py
│   │   │   ├── playlist_creation.py
│   │   │   ├── management.py
│   │   │   └── stats.py
│   │   ├── widgets/
│   │   │   ├── progress_bar.py
│   │   │   ├── table_models.py
│   │   │   └── charts.py
│   │   └── workers/
│   │       ├── fetch_worker.py
│   │       ├── analysis_worker.py
│   │       └── playlist_worker.py
│   │
│   └── utils/
│       ├── decorators.py
│       ├── helpers.py
│       └── validators.py
│
├── tests/
│   ├── test_spotify_client.py
│   ├── test_analyzer.py
│   ├── test_aggregator.py
│   └── test_database.py
│
├── resources/
│   ├── icons/
│   ├── styles/
│   └── data/
│
├── requirements.txt
├── .env.example
├── README.md
├── INSTALL.md
└── setup.py
```

### 5.4 Installation et Lancement

#### Installation:
```bash
# Clone le repo
git clone https://github.com/user/spotify-auto-like-sorter.git
cd spotify-auto-like-sorter

# Créer venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt

# Télécharger les modèles Essentia (~2GB)
python scripts/download_models.py

# Initialiser la base de données
python scripts/init_db.py

# Configurer .env
cp .env.example .env
# Éditer .env avec vos credentials Spotify/Deezer

# Lancer l'appli
python src/main.py
```

---

## ⏱️ Timeline Estimée

| Phase | Durée | Description |
|-------|-------|-------------|
| **1. Récupération & Stockage** | 5-8 jours | Spotify API + BD + Cache |
| **2. Analyse Audio** | 5-7 jours | Deezer API + Essentia |
| **3. Agrégation & Playlists** | 4-6 jours | Clustering + Création |
| **4. GUI** | 5-8 jours | PyQt6 + Workers |
| **5. Configuration & Tests** | 3-4 jours | Setup + Testing |
| **Total** | **22-33 jours** | ~1 mois (développement à temps plein) |

---

## 🎯 Priorités et Dépendances

### Phase 1 → 2 → 3 → 4

- ✅ Phase 1 indépendante
- ✅ Phase 2 dépend de Phase 1 (avoir les titres)
- ✅ Phase 3 dépend de Phase 2 (avoir les analyses)
- ✅ Phase 4 peut être parallèle à Phases 2-3 (prototype d'écrans)

### Points Critiques:
1. **Essentia TensorFlow**: Installation complexe, peut nécessiter CUDA
2. **Deezer API**: Pas tous les titres ont des previews
3. **Analyse audio**: ~1-2 min par track, 5000 tracks = 83-166 heures
   - Optimisation: Paralléliser (4 workers = 20-41 heures)
4. **Modèles Essentia**: ~2GB de disque requis

---

## 🔧 Considérations Techniques

### Optimisations Recommandées:

1. **Parallélisation**:
   - Récupération Deezer: asyncio + 5-10 concurrent connections
   - Analyse audio: multiprocessing + 4-8 workers
   - Téléchargement previews: asyncio downloader

2. **Caching**:
   - Embeddings Essentia (512-dim): ~5MB × 5000 = 25GB (compresser?)
   - Métadonnées complètes: SQLite suffisant

3. **Gestion Mémoire**:
   - Charger audio 30s à la fois
   - Libérer modèles TensorFlow entre analyses
   - Utiliser generators pour large datasets

### Dépannage Essentia:
```bash
# Sur macOS (Apple Silicon):
pip install --upgrade --force-reinstall essentia-tensorflow
# Peut nécessiter Rosetta2 ou conda-forge

# Sur Linux (GPU CUDA):
pip install tensorflow[and-cuda]==2.13.0

# Tester:
python -c "import essentia.standard as estd; print(estd.__version__)"
```

---

## 📊 Exemple de Résultat Final

**5000 titres likés** → **10-15 playlists intelligentes**:

```
🎵 Playlists créées:
├── 🌙 Sleepy Ambient (324 tracks) - Arousal basse, Valence basse
├── 😌 Relaxing & Chill (412 tracks) - Engagement bas, Tempo ~90-100 BPM
├── 🎸 Indie Rock Vibes (287 tracks) - Genre Rock/Alternative, Acoustic
├── 💃 Dance Party Energy (156 tracks) - Danceability haute, Tempo ~120+ BPM
├── 🎹 Acoustic Singer-Songwriter (198 tracks) - Voice présent, Acoustic
├── ⚡ Electronic Synthwave (301 tracks) - Electronic, Timbre bright
├── 😊 Happy Uplifting Tracks (276 tracks) - Valence haute
├── 😢 Sad & Introspective (189 tracks) - Mood Sad, Valence basse
├── 🔥 Aggressive & Intense (142 tracks) - Mood Aggressive, Arousal haute
├── 🌍 World & Folk Fusion (245 tracks) - Genres World/Folk
├── 🎼 Jazz Smooth Grooves (178 tracks) - Genre Jazz, Timbre dark
├── 🎭 Cinematic & Orchestral (134 tracks) - Orchestral, Epic mood
├── 🎙️ Hip-Hop & Rap Hits (287 tracks) - Genre Hip-Hop, Voice présent
├── 🎸 Classic Rock Legends (201 tracks) - Genre Rock/Classic, Acoustic
└── 🎼 Pop Hits Collection (350 tracks) - Genre Pop, Valence haute
```

Chaque playlist est :
- ✅ **Cohérente musicalement** (similarité audio)
- ✅ **Curatée intelligemment** (basée sur 13+ features)
- ✅ **Facilement modifiable** (paramètres personnalisables)
- ✅ **Synchronisée avec Spotify** (accès direct depuis app)
- ✅ **Traçable** (métadonnées complètes stockées)

---

## 🚀 Phase Future (Post-MVP):

1. **Web Dashboard**: Flask/FastAPI pour accès web
2. **Mobile App**: React Native ou Flutter
3. **Recommendations**: Suggestions de nouvelles tracks basées sur playlists
4. **Real-time Sync**: Mise à jour automatique des likes
5. **Collaboration**: Partage de playlists avec amis
6. **ML Training**: Modèles personnalisés basés sur historique utilisateur
7. **Cloud Deployment**: Docker + AWS/GCP/Azure

