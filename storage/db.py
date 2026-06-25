"""
Módulo de almacenamiento SQLite (modo offline)
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import sqlite3
import json
import os
import re
import hashlib
from datetime import datetime
from config import BASE_DIR, OFFLINE_MODE, DB_PATH
from storage.migrations import MigrationManager


def _init_db():
    """Inicializa la base de datos y aplica migraciones pendientes."""
    # Ejecutar migraciones primero
    MigrationManager(DB_PATH).apply_migrations()
    conn = sqlite3.connect(DB_PATH)
    return conn


def _firma_pdf(nombre_archivo, n_columnas, banco_detectado=""):
    """
    Genera una firma única por nombre normalizado + nro. columnas + banco detectado.
    CORREGIDO: Incluye banco_detectado para evitar colisiones.
    """
    base = re.sub(r'[0-9_\-]', '', os.path.splitext(nombre_archivo or '')[0].lower()).strip()
    raw = f"{base}_{n_columnas}_{banco_detectado}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _auto_guardar_archivo(uploaded_file, subfolder="datos_entrada"):
    if not OFFLINE_MODE or uploaded_file is None:
        return None, False
    dest_dir = os.path.join(BASE_DIR, subfolder, datetime.now().strftime("%Y-%m"))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, uploaded_file.name)
    if not os.path.exists(dest):
        with open(dest, "wb") as f:
            f.write(uploaded_file.getvalue())
        return dest, True
    return dest, False


def _auto_guardar_excel(excel_bytes, nombre):
    if not OFFLINE_MODE:
        return None
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    destdir = os.path.join(BASE_DIR, "reportes_excel", ts)
    os.makedirs(destdir, exist_ok=True)
    dest = os.path.join(destdir, nombre)
    with open(dest, "wb") as f:
        f.write(excel_bytes)
    return dest


def _guardar_historial_sqlite(d):
    try:
        conn = _init_db()
        conn.execute("""INSERT INTO historial
            (fecha_hora,archivo_banco,archivo_auxiliar,periodo,
             n_banco,n_aux,n_exactas,n_aprox,n_solo_banco,n_solo_aux,
             tasa,saldo_banco,saldo_aux,diferencia_neta,excel_path)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d["fecha_hora"],d["archivo_banco"],d["archivo_auxiliar"],d["periodo"],
             d["n_banco"],d["n_aux"],d["n_exactas"],d["n_aprox"],
             d["n_solo_banco"],d["n_solo_aux"],d["tasa"],
             d["saldo_banco"],d["saldo_aux"],d["diferencia_neta"],d.get("excel_path","")))
        conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.error(f"[_guardar_historial_sqlite] {e}", exc_info=True)


def leer_historial_sqlite(limite=8):
    try:
        if not os.path.exists(DB_PATH):
            return []
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """SELECT fecha_hora,archivo_banco,archivo_auxiliar,periodo,
                      tasa,n_exactas,n_banco,diferencia_neta
               FROM historial ORDER BY id DESC LIMIT ?""", (limite,)).fetchall()
        conn.close()
        return rows
    except Exception as e:
        import logging
        logging.error(f"[leer_historial_sqlite] {e}", exc_info=True)
        return []


# ── Fase C: Catálogo de formatos PDF aprendidos ───────────────────────────────

def registrar_formato_pdf(nombre_archivo, tipo_doc, columnas, fmt_fecha,
                          prefijos_doc, banco_detectado=""):
    """Guarda o actualiza el patrón de un PDF procesado exitosamente."""
    if not OFFLINE_MODE:
        return
    try:
        firma = _firma_pdf(nombre_archivo, len(columnas) if columnas else 0, banco_detectado)
        ahora = datetime.now().isoformat(timespec='seconds')
        conn = _init_db()
        existe = conn.execute(
            "SELECT id, usos FROM pdf_formatos WHERE firma=?", (firma,)).fetchone()
        if existe:
            conn.execute(
                "UPDATE pdf_formatos SET usos=?, ultima_vez=? WHERE firma=?",
                (existe[1] + 1, ahora, firma))
        else:
            conn.execute("""INSERT INTO pdf_formatos
                (firma, tipo_doc, columnas, fmt_fecha, prefijos_doc,
                 banco_detectado, usos, ultima_vez)
                VALUES (?,?,?,?,?,?,1,?)""",
                (firma, tipo_doc,
                 json.dumps(columnas or [], ensure_ascii=False),
                 fmt_fecha or '',
                 json.dumps(prefijos_doc or [], ensure_ascii=False),
                 banco_detectado or '', ahora))
        conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.error(f"[registrar_formato_pdf] {e}", exc_info=True)


def buscar_formato_pdf(nombre_archivo, n_columnas, banco_detectado=""):
    """Devuelve dict con info del formato guardado, o None si no existe."""
    if not OFFLINE_MODE:
        return None
    try:
        firma = _firma_pdf(nombre_archivo, n_columnas, banco_detectado)
        conn = _init_db()
        row = conn.execute(
            """SELECT tipo_doc, columnas, fmt_fecha, prefijos_doc,
                      banco_detectado, usos, ultima_vez
               FROM pdf_formatos WHERE firma=?""", (firma,)).fetchone()
        conn.close()
        if not row:
            return None
        return {
            'tipo_doc'        : row[0],
            'columnas'        : json.loads(row[1] or '[]'),
            'fmt_fecha'       : row[2],
            'prefijos_doc'    : json.loads(row[3] or '[]'),
            'banco_detectado' : row[4],
            'usos'            : row[5],
            'ultima_vez'      : row[6],
        }
    except Exception as e:
        import logging
        logging.error(f"[buscar_formato_pdf] {e}", exc_info=True)
        return None


def listar_formatos_aprendidos():
    """Devuelve todos los formatos guardados en el catálogo."""
    try:
        if not os.path.exists(DB_PATH):
            return []
        conn = _init_db()
        rows = conn.execute(
            """SELECT firma, tipo_doc, banco_detectado, usos, ultima_vez
               FROM pdf_formatos ORDER BY usos DESC""").fetchall()
        conn.close()
        return rows
    except Exception as e:
        import logging
        logging.error(f"[listar_formatos_aprendidos] {e}", exc_info=True)
        return []