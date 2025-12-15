# Roadmap Détaillée et Best Practices - Spotify Auto Like Sorter

## 🗓️ Roadmap Semaine par Semaine

### **SEMAINE 1: Infrastructure Fondamentale**

#### Jour 1-2: Setup et Authentification Spotify
```python
# src/api/spotify_client.py - Structure de base
class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
        )
    
    async def get_liked_tracks(self, limit=50):
        """
        Récupère TOUS les titres likés avec pagination
        Limite API: 50 tracks max par requête
        5000 tracks = 100 requêtes
        """
        results = []
        offset = 0
        while True:
            batch = self.sp.current_user_saved_tracks(limit=50, offset=offset)
            if not batch['items']:
                break
            results.extend(batch['items'])
            offset += 50
        return results
```

**Checklist**:
- [ ] Enregistrer app Spotify Developer
- [ ] Implémenter `SpotifyClient`
- [ ] Test connexion & récupération 10 tracks
- [ ] Gestion erreurs et rate limits

#### Jour 3: Base de Données
```python
# src/database/models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Track(Base):
    __tablename__ = "tracks"
    spotify_id = Column(String, primary_key=True)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    duration_ms = Column(Integer)
    popularity = Column(Integer)
    isrc = Column(String)
    uri = Column(String)
    added_at = Column(DateTime)

class TrackAnalysis(Base):
    __tablename__ = "track_analyses"
    id = Column(Integer, primary_key=True)
    spotify_id = Column(String, ForeignKey("tracks.spotify_id"))
    deezer_preview_url = Column(String)
    analysis_status = Column(String)  # pending, processing, completed, failed
    genre_discogs_519 = Column(JSON)
    arousal_valence = Column(JSON)
    # ... autres colonnes
```

**Checklist**:
- [ ] Créer schéma SQLAlchemy
- [ ] Initialiser SQLite
- [ ] Tester créations/lectures
- [ ] Ajouter migrations Alembic

#### Jour 4-5: Cache et Système de Configuration
```python
# src/cache/cache_manager.py
class CacheManager:
    def __init__(self, cache_dir='./cache', ttl=3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl
        self.memory_cache = {}
    
    def get(self, key: str):
        # 1. Vérifier mémoire
        # 2. Vérifier disque
        # 3. Retourner None si expiré
        ...
    
    def set(self, key: str, value, ttl=None):
        self.memory_cache[key] = (value, time.time())
        # Aussi sauver sur disque
        ...
```

**Checklist**:
- [ ] Implémenter `CacheManager`
- [ ] Tester memory + disk cache
- [ ] Config variables d'environnement (.env)
- [ ] Setup logging

---

### **SEMAINE 2: Intégration Deezer et Essentia**

#### Jour 1-2: Deezer API
```python
# src/api/deezer_client.py
class DeezerClient:
    async def get_preview(self, track_data):
        """
        Cherche preview Deezer pour une track Spotify
        Stratégies:
        1. ISRC (plus fiable)
        2. Titre + Artiste
        3. Fallback: None
        """
        # Chercher par ISRC d'abord
        if track_data.get('isrc'):
            result = await self._search_by_isrc(track_data['isrc'])
            if result:
                return result
        
        # Fallback: chercher par titre + artiste
        result = await self._search_by_name(
            track_data['title'],
            track_data['artist']
        )
        return result
    
    async def _search_by_isrc(self, isrc):
        url = f"https://api.deezer.com/search?isrc={isrc}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if data['data']:
                    return data['data'][0]['preview']
        return None
```

**Checklist**:
- [ ] Tester recherche par ISRC
- [ ] Tester recherche par titre/artiste
- [ ] Implémenter async batch processing (5-10 concurrent)
- [ ] Logger les tracks non trouvées

#### Jour 3-4: Installation et Setup Essentia
```python
# src/audio/essentia_models.py
class EssentiaTensorFlowModels:
    MODELS = {
        'genre_discogs_519': {
            'path': 'models/genre-discogs519-musicnn-1.pb',
            'output_layer': 'predictions/prob'
        },
        'arousal_valence_deam': {
            'path': 'models/arousal_valence_deam-musicnn-1.pb',
            'output_layer': 'predictions/regression'
        },
        # ... autres modèles
    }
    
    def __init__(self, models_dir='./models'):
        self.models_dir = Path(models_dir)
        self.sessions = {}
        self._load_all_models()
    
    def _load_all_models(self):
        """Charge tous les modèles TensorFlow au startup"""
        for name, config in self.MODELS.items():
            model_path = self.models_dir / config['path']
            session = self._load_model(model_path)
            self.sessions[name] = session
    
    def _load_model(self, model_path):
        import tensorflow as tf
        # Charger GraphDef
        with tf.io.gfile.GFile(model_path, 'rb') as f:
            graph_def = tf.compat.v1.GraphDef()
            graph_def.ParseFromString(f.read())
        
        graph = tf.Graph()
        with graph.as_default():
            tf.import_graph_def(graph_def, name='')
        
        return tf.compat.v1.Session(graph=graph)
```

**Checklist**:
- [ ] Télécharger les 10 modèles principaux (~2GB)
- [ ] Implémenter loader TensorFlow
- [ ] Tester chargement et inférence
- [ ] Documenter requirements CUDA (si nécessaire)

#### Jour 5: Téléchargement des Previews
```python
# src/audio/preview_downloader.py
class PreviewDownloader:
    def __init__(self, output_dir='./previews'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def download(self, track_id, preview_url):
        """Télécharge un preview 30s"""
        if not preview_url:
            return None
        
        output_path = self.output_dir / f"{track_id}.mp3"
        if output_path.exists():
            return output_path
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(preview_url) as resp:
                    if resp.status == 200:
                        with open(output_path, 'wb') as f:
                            f.write(await resp.read())
                        return output_path
        except Exception as e:
            logger.error(f"Erreur téléchargement {track_id}: {e}")
        
        return None
    
    async def download_batch(self, tracks_with_previews, max_workers=5):
        """Télécharge en parallèle"""
        semaphore = asyncio.Semaphore(max_workers)
        
        async def bounded_download(track_id, preview_url):
            async with semaphore:
                return await self.download(track_id, preview_url)
        
        tasks = [
            bounded_download(t['id'], t['preview_url'])
            for t in tracks_with_previews
        ]
        return await asyncio.gather(*tasks)
```

**Checklist**:
- [ ] Implémenter async downloader
- [ ] Gestion erreurs et retries
- [ ] Gestion espace disque
- [ ] Nettoyage fichiers orphelins

---

### **SEMAINE 3: Analyse Audio**

#### Jour 1-3: Pipeline d'Analyse Audio
```python
# src/audio/analyzer.py
class AudioAnalyzer:
    def __init__(self, models_dir='./models'):
        self.essentia_models = EssentiaTensorFlowModels(models_dir)
        self.feature_extractor = FeatureExtractor()
    
    async def analyze_track(self, audio_path: str) -> dict:
        """
        Analyse complète d'une track
        Retourne tous les descripteurs
        Durée: 1-2 minutes par track
        """
        try:
            # 1. Charger audio
            audio = self._load_audio(audio_path)
            
            # 2. Extraire embeddings
            embeddings = {
                'maest': self._get_maest_embedding(audio),
                'effnet': self._get_effnet_embedding(audio)
            }
            
            # 3. Classifier avec tous les modèles
            classifications = await self._run_all_classifiers(embeddings)
            
            # 4. Features bas-niveau
            low_level = self.feature_extractor.extract(audio)
            
            # 5. Combiner tous les résultats
            return {
                'embeddings': embeddings,
                'classifications': classifications,
                'low_level_features': low_level,
                'timestamp': datetime.now()
            }
        
        except Exception as e:
            logger.error(f"Analyse échouée pour {audio_path}: {e}")
            raise
    
    def _load_audio(self, audio_path) -> np.ndarray:
        """Charger MP3 en numpy array"""
        import librosa
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        return audio
    
    async def _run_all_classifiers(self, embeddings):
        """Lance tous les classifiers en parallèle"""
        tasks = []
        
        # Genre
        tasks.append(self._classify_genre(embeddings['maest']))
        
        # Moods
        tasks.append(self._classify_arousal_valence(embeddings['maest']))
        tasks.append(self._classify_engagement(embeddings['maest']))
        tasks.append(self._classify_danceability(embeddings['maest']))
        
        # etc...
        
        results = await asyncio.gather(*tasks)
        return {
            'genre_discogs_519': results[0],
            'arousal_valence': results[1],
            'engagement': results[2],
            'danceability': results[3],
            # ... autres
        }
    
    def _classify_genre(self, embedding) -> dict:
        """Lance modèle genre-discogs-519"""
        session = self.essentia_models.sessions['genre_discogs_519']
        # Préparer input
        # Inférer
        # Retourner probabilities
        ...
```

**Checklist**:
- [ ] Implémenter `AudioAnalyzer`
- [ ] Tester sur 1 track, 10 tracks, 100 tracks
- [ ] Profiler performance (temps par track)
- [ ] Optimiser si trop lent

#### Jour 4-5: Pipeline en Batch avec Persistance
```python
# src/audio/analysis_pipeline.py
class AnalysisPipeline:
    def __init__(self, db_session, analyzer, preview_downloader):
        self.db = db_session
        self.analyzer = analyzer
        self.downloader = preview_downloader
    
    async def process_all_tracks(self, tracks, max_workers=4):
        """
        Traite tous les tracks en batch
        Sauvegarde après chaque analysse
        """
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_track(track):
            async with semaphore:
                return await self.process_single(track)
        
        # Récupérer seulement les non-analysés
        pending_tracks = self.db.query(Track).filter(
            ~Track.analyses.any()
        ).all()
        
        pbar = tqdm(total=len(pending_tracks))
        
        async for result in asyncio.as_completed(
            [process_track(t) for t in pending_tracks]
        ):
            try:
                analysis_result = await result
                self.db.add(analysis_result)
                self.db.commit()
                pbar.update(1)
            except Exception as e:
                logger.error(f"Erreur: {e}")
                pbar.update(1)
        
        pbar.close()
    
    async def process_single(self, track):
        """Traite une seule track"""
        # 1. Récupérer preview Deezer
        preview_url = await self._get_preview(track)
        
        # 2. Télécharger
        audio_path = await self.downloader.download(
            track.spotify_id,
            preview_url
        )
        
        if not audio_path:
            return TrackAnalysis(
                spotify_id=track.spotify_id,
                status='failed',
                error='No preview found'
            )
        
        # 3. Analyser
        analysis_data = await self.analyzer.analyze_track(audio_path)
        
        # 4. Sauvegarder
        return TrackAnalysis(
            spotify_id=track.spotify_id,
            deezer_preview_url=preview_url,
            status='completed',
            **analysis_data
        )
```

**Checklist**:
- [ ] Implémenter pipeline batch
- [ ] Test sur 50 tracks
- [ ] Gestion erreurs et retries
- [ ] Recovery en cas de crash
- [ ] Affichage progression (pour UI)

---

### **SEMAINE 4: Clustering et Agrégation**

#### Jour 1-2: Feature Engineering et Normalisation
```python
# src/playlist/feature_engineering.py
class FeatureEngineer:
    def __init__(self, db_session):
        self.db = db_session
        self.scaler = StandardScaler()
    
    def create_feature_matrix(self, tracks_analysis):
        """
        Crée matrice de features (n_tracks, n_features)
        Features:
        - Embeddings MAEST (512-dim) - normalisés
        - Genre probabilities (top 10 genres)
        - Mood scores (arousal, valence, engagement)
        - Audio properties (tempo, timbre, acoustic/electronic)
        - Binary flags (voice, danceability, aggressive, etc)
        """
        features = []
        
        for analysis in tracks_analysis:
            track_features = []
            
            # 1. Embeddings MAEST (512 dim)
            maest_emb = analysis['embeddings']['maest']
            track_features.extend(maest_emb)
            
            # 2. Genre top-5 probabilities
            genre_probs = analysis['classifications']['genre_discogs_519']
            top_5_probs = sorted(genre_probs.items(), key=lambda x: x[1])[:5]
            for prob in top_5_probs:
                track_features.append(prob[1])
            
            # 3. Moods
            av = analysis['classifications']['arousal_valence']
            track_features.extend([av['arousal'], av['valence']])
            
            engagement = analysis['classifications']['engagement']
            track_features.append(engagement['engagement_score'])
            
            # 4. Audio properties
            low_level = analysis['low_level_features']
            track_features.append(low_level['tempo'])
            track_features.append(1.0 if low_level['timbre'] == 'bright' else 0.0)
            track_features.append(1.0 if analysis['is_acoustic'] else 0.0)
            
            # 5. Binary features
            track_features.append(1.0 if analysis['has_voice'] else 0.0)
            track_features.append(1.0 if analysis['is_danceability'] else 0.0)
            
            features.append(track_features)
        
        # Normaliser
        matrix = np.array(features)
        matrix = self.scaler.fit_transform(matrix)
        return matrix
    
    def compute_similarity_matrix(self, feature_matrix, metric='cosine'):
        """Calcule matrice de similarité"""
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity(feature_matrix)
```

#### Jour 3: Clustering et Playlist Generation
```python
# src/playlist/aggregator.py
class PlaylistAggregator:
    def __init__(self, feature_engineer):
        self.fe = feature_engineer
    
    def create_playlists_kmeans(self, tracks_analysis, n_clusters=10):
        """
        Crée playlists avec K-Means
        n_clusters = nombre de playlists
        """
        # 1. Créer matrice de features
        feature_matrix = self.fe.create_feature_matrix(tracks_analysis)
        
        # 2. K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(feature_matrix)
        
        # 3. Grouper tracks par cluster
        playlists = {}
        for track_id, label in enumerate(labels):
            if label not in playlists:
                playlists[label] = []
            playlists[label].append(track_id)
        
        # 4. Générer noms
        playlist_dicts = []
        for cluster_id, track_indices in playlists.items():
            cluster_tracks = [tracks_analysis[i] for i in track_indices]
            
            name = self._suggest_playlist_name(cluster_tracks)
            description = self._generate_description(cluster_tracks)
            
            playlist_dicts.append({
                'name': name,
                'description': description,
                'track_ids': [tracks_analysis[i]['spotify_id'] 
                              for i in track_indices],
                'cluster_id': cluster_id,
                'track_count': len(track_indices)
            })
        
        return playlist_dicts
    
    def _suggest_playlist_name(self, cluster_tracks):
        """
        Génère un nom intelligent basé sur:
        - Genre dominant
        - Mood dominant
        - Autres caractéristiques
        """
        # Extraire stats du cluster
        genres = {}
        moods = []
        avg_energy = 0
        
        for track in cluster_tracks:
            # Genre dominant
            genre_probs = track['classifications']['genre_discogs_519']
            top_genre = max(genre_probs.items(), key=lambda x: x[1])[0]
            genres[top_genre] = genres.get(top_genre, 0) + 1
            
            # Mood
            av = track['classifications']['arousal_valence']
            moods.append((av['arousal'], av['valence']))
            
            # Energy
            avg_energy += av['arousal']
        
        avg_energy /= len(cluster_tracks)
        
        # Générer nom
        top_genre = max(genres.items(), key=lambda x: x[1])[0]
        avg_mood = np.mean(moods, axis=0)
        
        if avg_energy > 0.7:
            energy_word = "Energy"
        elif avg_energy > 0.4:
            energy_word = "Groovy"
        else:
            energy_word = "Chill"
        
        if avg_mood[1] > 0.6:
            mood_word = "Happy"
        elif avg_mood[1] < 0.4:
            mood_word = "Melancholic"
        else:
            mood_word = "Balanced"
        
        return f"{energy_word} {mood_word} {top_genre}"
    
    def _generate_description(self, cluster_tracks):
        """Génère une description détaillée"""
        # Analyser stats
        n_tracks = len(cluster_tracks)
        avg_tempo = np.mean([t['low_level_features']['tempo'] 
                             for t in cluster_tracks])
        voice_ratio = sum(1 for t in cluster_tracks 
                         if t['has_voice']) / n_tracks
        
        return (f"Auto-curated playlist with {n_tracks} tracks. "
                f"Average tempo: {avg_tempo:.0f} BPM. "
                f"{voice_ratio*100:.0f}% have vocals.")
```

**Checklist**:
- [ ] Implémenter feature engineering
- [ ] Tester clustering K-Means (5-15 clusters)
- [ ] Implémenter génération noms intelligents
- [ ] Tester sur dataset complet

#### Jour 4-5: Gestion Playlists Spotify
```python
# src/playlist/playlist_manager.py
class SpotifyPlaylistManager:
    def __init__(self, spotify_client):
        self.client = spotify_client
    
    async def create_playlist(self, name, description, track_ids):
        """Crée une playlist Spotify"""
        # 1. Créer
        playlist = self.client.sp.user_playlist_create(
            self.client.sp.current_user()['id'],
            name=name,
            description=description
        )
        playlist_id = playlist['id']
        
        # 2. Ajouter tracks (limité à 100 par requête)
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            self.client.sp.playlist_add_items(playlist_id, batch)
        
        return playlist_id
    
    async def sync_playlists(self, playlists_configs):
        """Crée toutes les playlists"""
        created = []
        for config in playlists_configs:
            playlist_id = await self.create_playlist(
                config['name'],
                config['description'],
                config['track_ids']
            )
            
            # Sauvegarder en BD
            playlist_obj = Playlist(
                spotify_playlist_id=playlist_id,
                name=config['name'],
                track_count=len(config['track_ids']),
                synced_to_spotify=True
            )
            self.db.add(playlist_obj)
            self.db.commit()
            
            created.append(playlist_id)
        
        return created
```

**Checklist**:
- [ ] Test création 1-2 playlists
- [ ] Gestion erreurs (playlist existe déjà, etc)
- [ ] Batch add tracks
- [ ] Persistance en BD

---

### **SEMAINE 5: Interface GUI PyQt6**

#### Jour 1-2: Structure PyQt6 de base
```python
# src/gui/main_window.py
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Auto Like Sorter")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout avec sidebar + contenu
        main_layout = QHBoxLayout()
        
        # Sidebar navigation
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar, 1)
        
        # Stacked widget pour les screens
        self.stacked_widget = QStackedWidget()
        self.login_screen = LoginScreen()
        self.fetch_screen = FetchTracksScreen()
        self.analysis_screen = AnalysisScreen()
        self.playlist_screen = PlaylistScreen()
        
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.fetch_screen)
        self.stacked_widget.addWidget(self.analysis_screen)
        self.stacked_widget.addWidget(self.playlist_screen)
        
        main_layout.addWidget(self.stacked_widget, 4)
        self.central_widget.setLayout(main_layout)
    
    def _create_sidebar(self):
        """Crée le menu latéral"""
        sidebar = QWidget()
        layout = QVBoxLayout()
        
        buttons = [
            ("🔑 Login", self.show_login),
            ("📥 Fetch Liked", self.show_fetch),
            ("🎵 Analyze", self.show_analysis),
            ("🎧 Create Playlists", self.show_playlist)
        ]
        
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        layout.addStretch()
        sidebar.setLayout(layout)
        return sidebar
    
    def show_login(self):
        self.stacked_widget.setCurrentWidget(self.login_screen)
    
    def show_fetch(self):
        self.stacked_widget.setCurrentWidget(self.fetch_screen)
    
    def show_analysis(self):
        self.stacked_widget.setCurrentWidget(self.analysis_screen)
    
    def show_playlist(self):
        self.stacked_widget.setCurrentWidget(self.playlist_screen)
```

#### Jour 3: Screens Principaux
```python
# src/gui/screens/fetch_tracks.py
class FetchTracksScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Fetch Your Liked Tracks")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("This will download all your liked tracks from Spotify")
        layout.addWidget(desc)
        
        # Stats
        self.stats_label = QLabel("Ready to fetch")
        layout.addWidget(self.stats_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Fetch button
        self.fetch_btn = QPushButton("Start Fetching")
        self.fetch_btn.clicked.connect(self.start_fetch)
        layout.addWidget(self.fetch_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Worker
        self.fetch_worker = FetchWorker()
        self.fetch_worker.progress.connect(self.update_progress)
        self.fetch_worker.finished.connect(self.on_fetch_complete)
    
    def start_fetch(self):
        self.fetch_btn.setEnabled(False)
        self.fetch_worker.start()
    
    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress.setValue(percent)
        self.stats_label.setText(f"Fetched {current}/{total} tracks")
    
    def on_fetch_complete(self, tracks):
        QMessageBox.information(
            self, "Success",
            f"Successfully fetched {len(tracks)} tracks!"
        )
        self.fetch_btn.setEnabled(True)
```

#### Jour 4: Analysis Screen avec Real-time Progress
```python
# src/gui/screens/analysis.py
class AnalysisScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Analyze Your Tracks")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Stats
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        self.completed_label = QLabel("Completed: 0")
        self.remaining_label = QLabel("Remaining: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(self.remaining_label)
        layout.addLayout(stats_layout)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        layout.addWidget(QLabel("Overall Progress"))
        layout.addWidget(self.overall_progress)
        
        # Step progress
        self.step_progress = QProgressBar()
        self.step_label = QLabel("Step: Initializing...")
        layout.addWidget(self.step_label)
        layout.addWidget(self.step_progress)
        
        # Current track info
        self.current_track = QLabel("")
        layout.addWidget(self.current_track)
        
        # Options
        opts_layout = QHBoxLayout()
        self.only_pending = QCheckBox("Only pending tracks")
        self.only_pending.setChecked(True)
        opts_layout.addWidget(self.only_pending)
        layout.addLayout(opts_layout)
        
        # Start button
        self.start_btn = QPushButton("Start Analysis")
        self.start_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.start_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Worker
        self.worker = AnalysisWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.on_complete)
    
    def start_analysis(self):
        self.start_btn.setEnabled(False)
        self.worker.start()
    
    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.overall_progress.setValue(percent)
        self.completed_label.setText(f"Completed: {current}")
        self.remaining_label.setText(f"Remaining: {total - current}")
    
    def update_status(self, message):
        # Afficher track en cours, étape courante, etc
        self.step_label.setText(message)
```

#### Jour 5: Playlist Creation et Stats
```python
# src/gui/screens/playlist_creation.py
class PlaylistScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Create Playlists")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Energy Based",
            "Mood Based",
            "Genre Based",
            "Activity Based",
            "Custom"
        ])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)
        
        # Number of playlists
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Number of playlists:"))
        self.n_playlists_spin = QSpinBox()
        self.n_playlists_spin.setValue(10)
        self.n_playlists_spin.setRange(2, 50)
        n_layout.addWidget(self.n_playlists_spin)
        layout.addLayout(n_layout)
        
        # Preview
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(
            ["Playlist Name", "Tracks", "Description"]
        )
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview_table)
        
        # Create button
        self.create_btn = QPushButton("Create Playlists")
        self.create_btn.clicked.connect(self.create_playlists)
        layout.addWidget(self.create_btn)
        
        self.setLayout(layout)
    
    def on_preset_changed(self, preset_name):
        # Charger paramètres du preset
        # Mettre à jour n_playlists_spin
        # Afficher aperçu
        pass
    
    def create_playlists(self):
        # Lancer worker
        # Afficher progress
        # Créer sur Spotify
        pass
```

**Checklist**:
- [ ] Implémenter tous les screens
- [ ] Test navigation entre screens
- [ ] Implémenter workers (threads)
- [ ] Gestion des signaux/slots
- [ ] Styling CSS/QSS

---

### **SEMAINE 6: Finalisation et Testing**

#### Jour 1-2: Intégration Complète
- [ ] Tester flow complet (Login → Fetch → Analysis → Create)
- [ ] Gestion des erreurs dans GUI
- [ ] Logging en fichier
- [ ] Caching et recovery

#### Jour 3: Performance & Optimisation
- [ ] Profiler temps d'exécution
- [ ] Optimiser bottlenecks
- [ ] Gestion mémoire
- [ ] Parallelization

#### Jour 4: Documentation & Tests
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] Documentation README/INSTALL
- [ ] Example workflows

#### Jour 5: Déploiement
- [ ] Setup packaging (setup.py)
- [ ] Docker file (optionnel)
- [ ] Installation guide
- [ ] Beta testing avec utilisateurs

---

## 🛠️ Best Practices Techniques

### 1. **Gestion des Erreurs**
```python
class APIError(Exception):
    """Erreur API générique"""
    pass

class RateLimitError(APIError):
    """Rate limit Spotify"""
    pass

class PreviewNotFoundError(APIError):
    """Preview Deezer non trouvé"""
    pass

# Utilisation avec retry
async def with_retry(func, max_retries=3, backoff=2):
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = backoff ** attempt
                logger.warning(f"Rate limited. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
```

### 2. **Logging**
```python
# src/logger.py
import logging
from loguru import logger

def setup_logger(log_file='./logs/app.log'):
    logger.add(
        log_file,
        rotation="500 MB",
        retention="10 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}"
    )
    return logger

# Usage
logger.info(f"Fetched {len(tracks)} tracks")
logger.warning(f"Preview not found for {track_id}")
logger.error(f"Analysis failed: {error}")
```

### 3. **Configuration Hiérarchique**
```python
# src/config.py
from pydantic import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Spotify
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    
    # Paths
    CACHE_DIR: Path = Path("./cache")
    MODELS_DIR: Path = Path("./models")
    
    # Performance
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 32
    
    class Config:
        env_file = '.env'

settings = Settings()
```

### 4. **Async/Await Best Practices**
```python
# ✅ BON
async def fetch_all_previews(tracks):
    tasks = [get_preview(t) for t in tracks]
    return await asyncio.gather(*tasks)

# ❌ MAUVAIS
async def fetch_all_previews_bad(tracks):
    for track in tracks:
        preview = await get_preview(track)  # Sequential!
```

### 5. **Testing**
```python
# tests/test_analyzer.py
import pytest
from src.audio.analyzer import AudioAnalyzer

@pytest.fixture
def analyzer():
    return AudioAnalyzer('./tests/fixtures/models')

@pytest.mark.asyncio
async def test_analyze_track(analyzer):
    result = await analyzer.analyze_track('./tests/fixtures/sample.mp3')
    assert 'embeddings' in result
    assert 'classifications' in result
    assert len(result['embeddings']['maest']) == 512

def test_feature_matrix_shape():
    # Test feature engineering
    pass
```

---

## 📊 Estimation Temps Total

```
Phase 1 (Infra):        5-8 jours
Phase 2 (Audio):        5-7 jours
Phase 3 (Clustering):   4-6 jours
Phase 4 (GUI):          5-8 jours
Phase 5 (Deploy):       3-4 jours
─────────────────────────────────
TOTAL:                  22-33 jours
                        (~1 mois à temps plein)
```

Avec équipe de 2-3 devs = 2-3 semaines

---

