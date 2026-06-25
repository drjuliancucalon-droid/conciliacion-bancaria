"""
Gestión de migraciones de esquema de base de datos
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import sqlite3
from datetime import datetime
from config import DB_PATH


class MigrationManager:
    """
    Gestiona el versionado del esquema de la base de datos.
    Cada migración tiene un número de versión y una función de aplicación.
    """
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema_version_table()
    
    def _ensure_schema_version_table(self):
        """Crea la tabla schema_version si no existe."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def get_current_version(self):
        """Obtiene la versión actual del esquema."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        conn.close()
        return row[0] if row and row[0] is not None else 0
    
    def apply_migrations(self):
        """Aplica todas las migraciones pendientes en orden."""
        current_version = self.get_current_version()
        migrations = self._get_migrations()
        
        for version, description, migration_func in migrations:
            if version > current_version:
                print(f"Aplicando migración v{version}: {description}")
                conn = sqlite3.connect(self.db_path)
                try:
                    migration_func(conn)
                    conn.execute(
                        "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                        (version, datetime.now().isoformat(timespec='seconds'), description)
                    )
                    conn.commit()
                    print(f"  ✓ Migración v{version} aplicada correctamente")
                except Exception as e:
                    conn.rollback()
                    print(f"  ✗ Error en migración v{version}: {e}")
                    raise
                finally:
                    conn.close()
    
    def _get_migrations(self):
        """Define todas las migraciones disponibles."""
        return [
            (1, "Esquema inicial: historial, pdf_formatos, nc_catalogo, nc_aprendizaje, nc_historial_match", self._migration_v1),
        ]
    
    def _migration_v1(self, conn):
        """Migración v1: Crea las 4 tablas originales."""
        # Tabla historial
        conn.execute("""CREATE TABLE IF NOT EXISTS historial (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora       TEXT,
            archivo_banco    TEXT,
            archivo_auxiliar TEXT,
            periodo          TEXT,
            n_banco          INTEGER,
            n_aux            INTEGER,
            n_exactas        INTEGER,
            n_aprox          INTEGER,
            n_solo_banco     INTEGER,
            n_solo_aux       INTEGER,
            tasa             REAL,
            saldo_banco      REAL,
            saldo_aux        REAL,
            diferencia_neta  REAL,
            excel_path       TEXT
        )""")
        
        # Tabla pdf_formatos (Fase C)
        conn.execute("""CREATE TABLE IF NOT EXISTS pdf_formatos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            firma           TEXT UNIQUE,
            tipo_doc        TEXT,
            columnas        TEXT,
            fmt_fecha       TEXT,
            prefijos_doc    TEXT,
            banco_detectado TEXT,
            usos            INTEGER DEFAULT 1,
            ultima_vez      TEXT
        )""")
        
        # Tabla nc_catalogo (Fase D)
        conn.execute("""CREATE TABLE IF NOT EXISTS nc_catalogo (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid            TEXT UNIQUE,
            banco_tokens    TEXT,
            aux_tokens      TEXT,
            confirmaciones  INTEGER DEFAULT 1,
            nivel           TEXT DEFAULT 'PENDIENTE',
            aprobado_por    TEXT DEFAULT 'AUTO',
            fecha_primera   TEXT,
            fecha_ultima    TEXT,
            sync_status     TEXT DEFAULT 'PENDIENTE_SYNC'
        )""")
        
        # Tabla nc_aprendizaje
        conn.execute("""CREATE TABLE IF NOT EXISTS nc_aprendizaje (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid            TEXT UNIQUE,
            banco_desc_raw  TEXT,
            aux_concepto_raw TEXT,
            banco_tokens    TEXT,
            aux_tokens      TEXT,
            veces_visto     INTEGER DEFAULT 1,
            fecha_primera   TEXT,
            fecha_ultima    TEXT
        )""")
        
        # Tabla nc_historial_match
        conn.execute("""CREATE TABLE IF NOT EXISTS nc_historial_match (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha           TEXT,
            banco_desc      TEXT,
            aux_doc         TEXT,
            aux_concepto    TEXT,
            metodo          TEXT,
            valor_banco     REAL,
            valor_aux       REAL
        )""")


def run_migrations():
    """Punto de entrada para ejecutar migraciones."""
    manager = MigrationManager()
    manager.apply_migrations()