# 🎨 Phase 1 - Architecture Visuelle et Schémas

## 🏗️ Architecture Système Phase 1

```
┌─────────────────────────────────────────────────────────────┐
│                     SPOTIFY AUTO LIKE SORTER               │
│                         Phase 1                             │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                          UTILISATEUR                                  │
│                                                                      │
│  Clic: python src/main.py                                           │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION (Pydantic)                         │
│                                                                      │
│  .env → Settings → Variables globales sécurisées                    │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│                      LOGGING (Loguru)                                │
│                                                                      │
│  ├─→ Console (couleurs)                                             │
│  └─→ ./logs/app.log (rotaté automatiquement)                        │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│               SPOTIFY CLIENT (OAuth 2.0)                             │
│                                                                      │
│  SpotifyOAuth → Login → Token Management                            │
│                                                                      │
│  async get_all_liked_tracks():                                      │
│  ├─ Requête 1: offset=0,   limit=50     (50 tracks)                │
│  ├─ Requête 2: offset=50,  limit=50     (50 tracks)                │
│  ├─ ...                                                              │
│  └─ Requête 100: offset=4950, limit=50  (50 tracks)                │
│                                                                      │
│  Result: List[Dict] ~5000 tracks                                    │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│                   PARSING & NORMALISATION                            │
│                                                                      │
│  Raw Spotify API Response:                                          │
│  {\"added_at\": \"...\", \"track\": {\"id\": \"...\", ...}}                │
│                  ↓                                                   │
│  Parsed Track:                                                      │
│  {\"spotify_id\": \"...\", \"title\": \"...\", \"artist\": \"...\"}         │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│                  REPOSITORY (CRUD Operations)                        │
│                                                                      │
│  TrackRepository:                                                   │
│  ├─ create_track()                                                  │
│  ├─ create_many_tracks()  ← 5000 inserts bulk                       │
│  ├─ get_track()                                                     │
│  └─ get_unanalyzed_tracks()                                         │
│                                                                      │
│  AnalysisRepository:                                                │
│  ├─ create_analysis()                                               │
│  ├─ update_status()                                                 │
│  └─ get_stats()                                                     │
└──────────────────────────────────────────────────────────────────────┘
                              ↓

┌──────────────────────────────────────────────────────────────────────┐
│              DATABASE (SQLite avec SQLAlchemy ORM)                   │
│                                                                      │
│  sqlite_analyzer.db (50-100 MB)                                     │
│  ├─ tracks (5000+ rows)                                             │
│  │  ├─ spotify_id (PK): \"3n3Ppam7vgaVa1iaRUc9Lp\"                   │
│  │  ├─ title: \"Bohemian Rhapsody\"                                  │
│  │  ├─ artist: \"Queen\"                                             │
│  │  ├─ album: \"A Night at the Opera\"                              │
│  │  ├─ duration_ms: 354600                                          │
│  │  ├─ popularity: 81                                               │
│  │  ├─ isrc: \"GBUM71505395\"                                        │
│  │  ├─ uri: \"spotify:track:...\"                                    │
│  │  ├─ added_at: \"2023-06-15 14:22:30\"                            │
│  │  └─ created_at: \"2024-01-10 12:34:56\"                          │
│  │                                                                   │
│  ├─ track_analyses (5000+ rows)                                     │
│  │  ├─ id (PK): 1                                                   │
│  │  ├─ spotify_id (FK): \"3n3Ppam7vgaVa1iaRUc9Lp\"                  │
│  │  ├─ analysis_status: \"pending\" ← Pour Phase 2                  │
│  │  ├─ error_message: NULL                                          │
│  │  ├─ deezer_preview_url: NULL ← Rempli Phase 2                   │
│  │  └─ created_at: \"2024-01-10 12:34:56\"                          │
│  │                                                                   │
│  └─ track_metadata (5000+ rows - vide pour Phase 1)                │
│     ├─ genre_discogs_519: NULL ← Phase 3                           │
│     ├─ arousal_valence: NULL ← Phase 3                             │
│     ├─ tempo_bpm: NULL ← Phase 3                                   │
│     ├─ maest_embedding: NULL ← Phase 3                             │
│     └─ ... autres champs pour Phase 3                              │
└──────────────────────────────────────────────────────────────────────┘

PARALLÈLE:

┌──────────────────────────────────────────────────────────────────────┐
│               CACHE MANAGER (Dual-layer)                             │
│                                                                      │
│  Mémoire (RAM):                                                     │
│  ├─ Très rapide (<1ms)                                              │
│  ├─ Volatile (disparaît au redémarrage)                             │
│  └─ TTL: 3600 sec                                                   │
│                                                                      │
│  Disque (./cache/):                                                 │
│  ├─ Persistant                                                      │
│  ├─ Fallback mémoire                                                │
│  ├─ TTL: 3600 sec                                                   │
│  └─ Fichiers .pickle binaires                                       │
│                                                                      │
│  Flux: get(key) → Mémoire? → Disque? → Manque                     │
│        set(key) → Mémoire + Disque                                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Schéma Base de Données (ERD)

```
┌──────────────────────────────────────────────────────────────────┐
│                          TRACKS                                  │
├──────────────────────────────────────────────────────────────────┤
│ PK spotify_id           │ VARCHAR(50)                             │
│    title                │ VARCHAR(300)  [NOT NULL]                │
│    artist               │ VARCHAR(300)  [NOT NULL]                │
│    artists_list         │ JSON                                    │
│    album                │ VARCHAR(300)                            │
│    duration_ms          │ INTEGER                                 │
│    popularity           │ INTEGER (0-100)                         │
│    isrc                 │ VARCHAR(50)   [INDEX]                   │
│    uri                  │ VARCHAR(300)                            │
│    preview_url          │ VARCHAR(500)                            │
│    explicit             │ BOOLEAN       [DEFAULT: false]          │
│    added_at             │ DATETIME                                │
│    created_at           │ DATETIME      [DEFAULT: NOW, INDEX]    │
│    updated_at           │ DATETIME      [DEFAULT: NOW]            │
└──────────────────────────────────────────────────────────────────┘
               ↓ 1:1                          ↓ 1:1
    ┌─────────────────────┐        ┌─────────────────────────┐
    │  TRACK_ANALYSES     │        │   TRACK_METADATA        │
    ├─────────────────────┤        ├─────────────────────────┤
    │ PK id: INTEGER      │        │ PK id: INTEGER          │
    │ FK spotify_id       │        │ FK spotify_id           │
    │    status: STRING   │        │    genre_discogs_519    │
    │    error_msg: TEXT  │        │    arousal_valence      │
    │    analysis_date    │        │    tempo_bpm            │
    │    created_at       │        │    maest_embedding      │
    │    updated_at       │        │    (... 20+ champs)      │
    └─────────────────────┘        └─────────────────────────┘
                                       (Phase 2-3 seulement)
```

---

## 🔄 Flux de Données Phase 1

```
Utilisateur
    │
    └──→ python src/main.py
         │
         ├─→ 1. Vérifier BD
         │   └─→ Créer tables si nécessaire
         │
         ├─→ 2. Spotify Auth
         │   └─→ OAuth login
         │
         ├─→ 3. Récupérer Tracks
         │   ├─→ get_all_liked_tracks()
         │   │   ├─→ Boucle 100 requêtes (pagination 50)
         │   │   │   ├─→ Request API #1 (offset=0)
         │   │   │   ├─→ Request API #2 (offset=50)
         │   │   │   └─→ ... Request API #100 (offset=4950)
         │   │   └─→ Result: 5000 tracks
         │   │
         │   └─→ parse_track_data()
         │       └─→ Normaliser: brut → structured dict
         │
         ├─→ 4. Sauvegarder en BD
         │   ├─→ TrackRepository.create_many_tracks()
         │   │   └─→ INSERT 5000 rows (1 transaction)
         │   │
         │   └─→ AnalysisRepository.create_analysis()
         │       └─→ INSERT 5000 rows (analysis_status=\"pending\")
         │
         ├─→ 5. Afficher Stats
         │   ├─→ SELECT COUNT(*) FROM tracks       → 5000
         │   ├─→ SELECT COUNT(*) WHERE status=\"pending\"  → 5000
         │   └─→ Log: \"✅ Phase 1 réussie!\"
         │
         └─→ Cache & Logs
             ├─→ Cache ./cache/ rempli (optionnel)
             └─→ Logs ./logs/app.log générés

Base de Données
    │
    └─→ sqlite_analyzer.db
        ├─→ Tracks: 5000+ rows
        ├─→ Analyses: 5000+ rows
        └─→ Metadata: 5000+ empty rows
```

---

## ⏱️ Timeline Phase 1

```
Jour 1: Setup (2-3h)
├─ Git/Python venv
├─ pip install
├─ Credentials Spotify
└─ .env configuration

Jour 2: Infrastructure (4-5h)
├─ src/config.py (50 lignes)
├─ src/logger.py (40 lignes)
└─ Tests imports

Jour 3: Spotify (6-8h)
├─ src/api/exceptions.py (20 lignes)
├─ src/api/spotify_client.py (350 lignes) ⭐
└─ Test: python scripts/test_connection.py ✅

Jour 4: Base de Données (6-8h)
├─ src/database/models.py (200 lignes)
├─ src/database/database.py (100 lignes)
├─ src/database/repository.py (150 lignes)
└─ Test: python scripts/init_db.py ✅

Jour 5: Système Complet (4-6h)
├─ src/cache/cache_manager.py (150 lignes)
├─ scripts/init_db.py (20 lignes)
├─ scripts/test_connection.py (40 lignes)
├─ src/main.py (80 lignes)
└─ Test: python src/main.py ✅

Jour 6: Tests & Polish (2-3h)
├─ Tests d'exécution complets
├─ Vérification données BD
├─ Documentation complète
└─ Commits Git

TOTAL: 24-33 heures (3-4 jours à temps plein)
```

---

## 💾 Taille Fichiers Attendue

```
Phase 1 Deliverables:
│
├─ Code Source (~1500 lignes)
│  ├─ src/config.py                    ~50 lignes
│  ├─ src/logger.py                    ~40 lignes
│  ├─ src/api/exceptions.py            ~20 lignes
│  ├─ src/api/spotify_client.py        ~350 lignes ⭐
│  ├─ src/database/models.py           ~200 lignes
│  ├─ src/database/database.py         ~100 lignes
│  ├─ src/database/repository.py       ~150 lignes
│  ├─ src/cache/cache_manager.py       ~150 lignes
│  ├─ scripts/init_db.py               ~20 lignes
│  ├─ scripts/test_connection.py       ~40 lignes
│  └─ src/main.py                      ~80 lignes
│
├─ Documentation (~8000 lignes)
│  ├─ phase1_complete.md               ~2000 lignes
│  ├─ IMPLEMENTATION_GUIDE.md          ~1500 lignes
│  ├─ IMPLEMENTATION_COMPLETE.md       ~2500 lignes
│  ├─ RESUME_EXECUTIF.md               ~1000 lignes
│  ├─ README.md                        ~500 lignes
│  └─ This file (ARCHITECTURE.md)      ~500 lignes
│
├─ Configuration
│  ├─ requirements.txt                 ~30 lignes
│  ├─ .env.example                     ~20 lignes
│  └─ .gitignore                       ~40 lignes
│
└─ Données (Runtime)
   ├─ .env                             ~20 lignes (sécurisé)
   ├─ spotify_analyzer.db              ~50-100 MB
   ├─ cache/                           ~0-10 MB (optionnel)
   └─ logs/app.log                     ~1-5 MB (rotaté)
```

---

## 🎯 Critères de Succès Phase 1

### ✅ Technique
- [ ] Tous les imports fonctionnent
- [ ] Base de données créée et accessible
- [ ] 5000+ tracks stockés avec tous les champs
- [ ] Cache fonctionnel (mémoire + disque)
- [ ] Logs générés et rotatés
- [ ] Configuration sécurisée (.env)
- [ ] Gestion d'erreurs robuste
- [ ] Code commenté et documenté

### ✅ Fonctionnel
- [ ] Connexion Spotify réussie
- [ ] Récupération paginated complète (~100 requêtes)
- [ ] Parsing normalisé des données
- [ ] Sauvegarde en BD sans doublons
- [ ] Requêtes BD optimisées
- [ ] Performance: <10 minutes pour 5000 tracks
- [ ] Pas de fuites mémoire
- [ ] Redémarrage sans état

### ✅ Code Quality
- [ ] Respect PEP 8
- [ ] Type hints (Optional, List, Dict)
- [ ] Exceptions custom et handling
- [ ] Logging à 5 niveaux (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] Context managers (with statements)
- [ ] Async/await où approprié
- [ ] Repository pattern (séparation concerns)
- [ ] Configuration externalisée

### ✅ Documentation
- [ ] README complet
- [ ] Code commenté
- [ ] Architecture diagrammes
- [ ] Setup instructions
- [ ] Troubleshooting guide
- [ ] API documentation
- [ ] Database schema
- [ ] Timeline complète

---

## 🚀 ReadyChecks Avant Phase 2

```
Phase 1 ✅ Complete?
├─ BD contient 5000+ tracks
├─ Toutes les analyses status=\"pending\"
├─ Cache système fonctionnel
├─ Logs générés correctement
├─ Configuration sécurisée
├─ Code production-ready
├─ Documentation complète
└─ Commits Git clean

→ YES? Prêt pour Phase 2 (Deezer + Previews)
```

---

## 📌 Notes Importantes

### Sécurité
- ⚠️ JAMAIS commit .env avec credentials réels
- ⚠️ JAMAIS share Client Secret
- ✅ Utiliser .env.example comme template
- ✅ Utiliser variables d'environnement en production

### Performance
- ✅ Pagination 50 tracks optimal (limites API)
- ✅ Bulk insert (create_many_tracks)
- ✅ Cache dual-layer pour hit rate 90%+
- ✅ Async opérations pour non-blocking I/O

### Scalabilité
- ✅ Repository pattern permet changement ORM
- ✅ Configuration centralisée permet switching DB
- ✅ Logging structuré permet analytics
- ✅ Cache pluggable (Redis, Memcached)

---

**Phase 1 = Fondation solide pour Phases 2-5** 🎵🚀
