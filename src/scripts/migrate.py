"""Migration: Ajouter colonnes de stockage preview"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database import db_manager
from src.database.models import TrackAnalysis
from sqlalchemy import text


def migrate():
    """Ajouter les colonnes si elles n'existent pas"""

    with db_manager.session_scope() as session:
        columns_to_add = {
            'track_preview_url': 'VARCHAR(500)',
            'preview_local_path': 'VARCHAR(500)',
            'preview_source': 'VARCHAR(20)',
            'preview_fetched_at': 'DATETIME',
            'preview_status': 'VARCHAR(20)',
            'preview_error': 'TEXT'
        }

        for col_name, col_type in columns_to_add.items():
            try:
                # Vérifier si colonne existe
                query = f"PRAGMA table_info(track_analyses)"
                result = session.execute(text(query))
                existing = [row for row in result]

                if col_name not in existing:
                    # Ajouter colonne
                    alter_sql = f"ALTER TABLE track_analyses ADD COLUMN {col_name} {col_type}"
                    session.execute(text(alter_sql))
                    print(f"✅ Ajoutée: {col_name}")
                else:
                    print(f"✓ Existe: {col_name}")

            except Exception as e:
                print(f"❌ Erreur {col_name}: {e}")

        session.commit()
        print("✅ Migration complète!")


if __name__ == "__main__":
    migrate()
