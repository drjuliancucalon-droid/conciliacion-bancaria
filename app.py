"""
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria Interactiva Premium
Soporte multiformato (PDF, CSV, Excel, TXT) + OCR para PDF escaneados
Arquitectura modular refactorizada — v2.0 Sprint 1: Rediseño visual profesional
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import io
import os
import tempfile
import logging
import pdfplumber
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS DE MÓDULOS REFACTORIZADOS
# ══════════════════════════════════════════════════════════════════════════════

from config import (
    BASE_DIR, OFFLINE_MODE, DB_PATH,
    TOL_EXACTA, TOL_APROX,
    _STOP_NC, REGLAS_COL,
    UMBRAL_DIF_NETA,
)

from storage import (
    guardar_historial,
    leer_historial,
    registrar_aprendizaje_nc,
    registrar_formato_pdf,
    buscar_formato_pdf,
    listar_formatos_aprendidos,
    _auto_guardar_archivo,
    _auto_guardar_excel,
    _init_db,
)

from engine import (
    comparar_documentos,
    determinar_columna,
    buscar_en_catalogo_nc,
    _aprender_match_nc,
    listar_catalogo_nc,
    asignar_puc_a_dataframe,
    resumen_por_puc,
    generar_reporte_comisiones,
)

from parsers import (
    parsear_banco_pdf,
    parsear_auxiliar_pdf,
    despachar_ruta,
    cargar_y_parsear_uploaded_file,
    REGISTRO_FORMATOS,
    muestra_texto,
)

from utils import (
    cop,
    pct_bar,
    semaforo_conciliacion,
    diagnosticar_pdf,
    extraer_periodo_banco,
)

from exports import (
    generar_excel_conciliacion,
    generar_pdf_conciliacion,
)

from utils.pdf_diagnostico import OCR_AVAILABLE

# Configuración de página
st.set_page_config(
    page_title="Conciliación Bancaria | CREDIEXPRESS",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS PREMIUM — TEMA CORPORATIVO CREDIEXPRESS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* ═══ IMPORTS ═══ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ═══ VARIABLES DE TEMA ═══ */
    :root {
        --primary: #1F4E79;
        --primary-light: #2E75B6;
        --primary-dark: #0D2B45;
        --accent: #D4AF37;
        --accent-light: #F0D060;
        --success: #28A745;
        --warning: #FFC107;
        --danger: #DC3545;
        --info: #17A2B8;
        --bg: #F5F7FA;
        --card-bg: #FFFFFF;
        --text: #1A1A2E;
        --text-secondary: #6C757D;
        --border: #E4E9F0;
        --shadow: 0 2px 12px rgba(0,0,0,0.08);
        --shadow-lg: 0 8px 32px rgba(0,0,0,0.12);
        --radius: 12px;
        --radius-sm: 8px;
        --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ═══ TEMA OSCURO ═══ */
    [data-theme="dark"] {
        --bg: #0F1923;
        --card-bg: #1A2A3A;
        --text: #E4E9F0;
        --text-secondary: #8899AA;
        --border: #2A3A4A;
        --shadow: 0 2px 12px rgba(0,0,0,0.3);
        --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
    }

    /* ═══ GLOBAL ═══ */
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    
    .stApp {
        background: var(--bg) !important;
        color: var(--text) !important;
    }

    /* ═══ SIDEBAR ═══ */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--primary-dark) 0%, var(--primary) 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.08) !important;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--accent-light) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
        margin-top: 1.5rem !important;
    }
    section[data-testid="stSidebar"] label {
        color: #CCD5E0 !important;
        font-size: 0.8rem !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-light) 100%) !important;
        color: var(--primary-dark) !important;
        font-weight: 700 !important;
        border: none !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 4px 16px rgba(212,175,55,0.35) !important;
        transition: var(--transition) !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(212,175,55,0.5) !important;
    }

    /* ═══ HEADER ═══ */
    .app-header {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 50%, var(--primary-light) 100%);
        padding: 1.5rem 2rem;
        border-radius: var(--radius);
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    .app-header::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
    }
    .app-header h1 {
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.5px !important;
    }
    .app-header p {
        font-size: 0.85rem !important;
        opacity: 0.85 !important;
        margin: 0.25rem 0 0 0 !important;
    }

    /* ═══ DASHBOARD CARDS ═══ */
    .dash-card {
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1.5rem;
        box-shadow: var(--shadow);
        border: 1px solid var(--border);
        transition: var(--transition);
        height: 100%;
    }
    .dash-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-2px);
    }
    .dash-card .card-icon {
        font-size: 2rem;
        margin-bottom: 0.75rem;
    }
    .dash-card .card-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .dash-card .card-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--primary);
        margin: 0.25rem 0;
    }
    .dash-card .card-sub {
        font-size: 0.78rem;
        color: var(--text-secondary);
    }

    /* ═══ METRIC BADGE ═══ */
    .metric-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .metric-badge.success { background: #D4EDDA; color: #155724; }
    .metric-badge.warning { background: #FFF3CD; color: #856404; }
    .metric-badge.danger { background: #F8D7DA; color: #721C24; }
    .metric-badge.info { background: #D1ECF1; color: #0C5460; }

    /* ═══ TABS ═══ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: transparent !important;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0 20px;
        background: transparent !important;
        border-radius: 8px 8px 0 0 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        color: var(--text-secondary) !important;
        border: none !important;
        transition: var(--transition);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(31,78,121,0.05) !important;
        color: var(--primary) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 -2px 8px rgba(31,78,121,0.3);
    }

    /* ═══ METRIC CARDS (Streamlit) ═══ */
    div[data-testid="stMetric"] {
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1rem !important;
        box-shadow: var(--shadow);
        border: 1px solid var(--border);
        transition: var(--transition);
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-lg);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        color: var(--text-secondary) !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        color: var(--primary) !important;
    }

    /* ═══ DATAFRAMES ═══ */
    .stDataFrame {
        border-radius: var(--radius) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow) !important;
        border: 1px solid var(--border) !important;
    }
    .stDataFrame thead th {
        background: var(--primary) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        padding: 10px 12px !important;
    }
    .stDataFrame tbody tr:hover {
        background: rgba(31,78,121,0.04) !important;
    }

    /* ═══ LANDING ═══ */
    .landing-container {
        text-align: center;
        padding: 3rem 1rem;
    }
    .landing-icon {
        font-size: 5rem;
        margin-bottom: 1rem;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .landing-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--primary);
        margin-bottom: 0.5rem;
    }
    .landing-sub {
        font-size: 1rem;
        color: var(--text-secondary);
        max-width: 500px;
        margin: 0 auto 2rem auto;
    }
    .landing-steps {
        display: flex;
        gap: 1.5rem;
        justify-content: center;
        flex-wrap: wrap;
        max-width: 700px;
        margin: 0 auto;
    }
    .landing-step {
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1.25rem;
        width: 200px;
        box-shadow: var(--shadow);
        border: 1px solid var(--border);
        text-align: center;
        transition: var(--transition);
    }
    .landing-step:hover {
        box-shadow: var(--shadow-lg);
    }
    .landing-step .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: var(--primary);
        color: white;
        font-weight: 700;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .landing-step .step-title {
        font-weight: 600;
        font-size: 0.85rem;
        color: var(--text);
    }
    .landing-step .step-desc {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }

    /* ═══ DIVIDERS ═══ */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1.5rem 0;
    }

    /* ═══ FOOTER ═══ */
    .app-footer {
        text-align: center;
        padding: 1rem;
        color: var(--text-secondary);
        font-size: 0.75rem;
        border-top: 1px solid var(--border);
        margin-top: 2rem;
    }

    /* ═══ PROGRESS BAR ═══ */
    .progress-bar {
        height: 8px;
        background: var(--border);
        border-radius: 4px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary), var(--accent));
        border-radius: 4px;
        transition: width 0.6s ease;
    }

    /* ═══ TOAST ═══ */
    .toast {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        padding: 1rem 1.5rem;
        border-radius: var(--radius);
        background: var(--card-bg);
        box-shadow: var(--shadow-lg);
        border-left: 4px solid var(--primary);
        font-weight: 500;
        animation: slideIn 0.3s ease;
    }
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN BÁSICA
# ══════════════════════════════════════════════════════════════════════════════

import hmac

def check_password():
    def password_entered():
        if hmac.compare_digest(
            st.session_state.get("password", ""),
            st.secrets.get("APP_PASSWORD", "crediexpress2025")
        ):
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    
    if st.session_state.get("password_correct", False):
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; padding:3rem 0 1rem 0;">
            <div style="font-size:4rem;">🏦</div>
            <h1 style="color:#1F4E79; font-weight:800; margin:0.5rem 0;">Conciliación Bancaria</h1>
            <p style="color:#6C757D; font-size:1rem;">CREDIEXPRESS POPAYÁN SAS</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "Contraseña de acceso", type="password",
            on_change=password_entered, key="password",
            placeholder="Ingrese su contraseña"
        )
        if "password_correct" in st.session_state:
            st.error("⚠️ Contraseña incorrecta")
    return False

if not check_password():
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# ══════════════════════════════════════════════════════════════════════════════

if 'df_banco' not in st.session_state:
    st.session_state.df_banco = pd.DataFrame()
if 'df_aux' not in st.session_state:
    st.session_state.df_aux = pd.DataFrame()
if 'matches_df' not in st.session_state:
    st.session_state.matches_df = pd.DataFrame()
if 'solo_banco_df' not in st.session_state:
    st.session_state.solo_banco_df = pd.DataFrame()
if 'solo_aux_df' not in st.session_state:
    st.session_state.solo_aux_df = pd.DataFrame()
if 'stats' not in st.session_state:
    st.session_state.stats = {}
if 'banco_meta' not in st.session_state:
    st.session_state.banco_meta = {}
if 'aux_meta' not in st.session_state:
    st.session_state.aux_meta = {}
if 'banco_fmt' not in st.session_state:
    st.session_state.banco_fmt = ''
if 'aux_fmt' not in st.session_state:
    st.session_state.aux_fmt = ''
if 'periodo' not in st.session_state:
    st.session_state.periodo = ''
if 'archivo_banco' not in st.session_state:
    st.session_state.archivo_banco = ''
if 'archivo_auxiliar' not in st.session_state:
    st.session_state.archivo_auxiliar = ''
if 'banco_ruta' not in st.session_state:
    st.session_state.banco_ruta = None
if 'aux_ruta' not in st.session_state:
    st.session_state.aux_ruta = None

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — PANEL DE CONTROL PROFESIONAL
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:0.5rem 0 1rem 0;">
        <div style="font-size:2.5rem;">🏦</div>
        <div style="font-weight:800; font-size:1.1rem; line-height:1.2;">
            Conciliación<br>Bancaria
        </div>
        <div style="font-size:0.7rem; opacity:0.7; margin-top:0.25rem;">
            CREDIEXPRESS POPAYÁN SAS
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Paso 1
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:0.5rem;">
        <span style="background:var(--accent); color:var(--primary-dark); 
                     width:22px; height:22px; border-radius:50%; display:inline-flex;
                     align-items:center; justify-content:center; font-weight:700;
                     font-size:0.75rem;">1</span>
        <span style="font-weight:600; font-size:0.82rem;">CARGAR ARCHIVOS</span>
    </div>
    """, unsafe_allow_html=True)
    
    banco_file = st.file_uploader(
        "📄 Extracto Bancario (PDF)",
        type=['pdf'],
        key="banco_uploader",
        help="PDF del extracto bancario mensual"
    )
    
    aux_file = st.file_uploader(
        "📋 Auxiliar Contable (PDF, CSV, Excel, TXT)",
        type=['pdf', 'csv', 'xlsx', 'xls', 'txt'],
        key="aux_uploader",
        help="Auxiliar contable en múltiples formatos"
    )
    
    st.markdown("---")
    
    # Paso 2
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:0.5rem;">
        <span style="background:var(--primary-light); color:white; 
                     width:22px; height:22px; border-radius:50%; display:inline-flex;
                     align-items:center; justify-content:center; font-weight:700;
                     font-size:0.75rem;">2</span>
        <span style="font-weight:600; font-size:0.82rem;">CONFIGURAR</span>
    </div>
    """, unsafe_allow_html=True)
    
    usar_ocr = st.checkbox(
        "🔍 OCR para PDF escaneados",
        value=False,
        disabled=not OCR_AVAILABLE,
        help="Activar si sus PDFs son imágenes escaneadas"
    )
    if not OCR_AVAILABLE:
        st.caption("⚠️ OCR no instalado")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tol_exacta = st.number_input(
            "Tol. Exacta", min_value=0.0, max_value=1000.0,
            value=TOL_EXACTA, step=1.0, help="COP"
        )
    with col_t2:
        tol_aprox = st.number_input(
            "Tol. Aprox %", min_value=0.1, max_value=10.0,
            value=TOL_APROX*100, step=0.1
        ) / 100
    
    umbral_diff = st.number_input(
        "Umbral Alerta (COP)",
        min_value=1.0, max_value=1000000.0,
        value=float(UMBRAL_DIF_NETA), step=100.0
    )
    
    st.markdown("---")
    
    # Paso 3
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:0.5rem;">
        <span style="background:var(--success); color:white; 
                     width:22px; height:22px; border-radius:50%; display:inline-flex;
                     align-items:center; justify-content:center; font-weight:700;
                     font-size:0.75rem;">3</span>
        <span style="font-weight:600; font-size:0.82rem;">PROCESAR</span>
    </div>
    """, unsafe_allow_html=True)
    
    procesar = st.button(
        "⚡ EJECUTAR CONCILIACIÓN",
        type="primary",
        use_container_width=True,
        disabled=not (banco_file and aux_file)
    )
    
    st.markdown("---")
    
    # Info entorno
    st.caption(
        f"{'🖥️ Local SQLite' if OFFLINE_MODE else '☁️ Cloud Sheets'}"
        f"{' • ✅ OCR' if OCR_AVAILABLE else ''}"
    )

# ══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

if procesar and banco_file and aux_file:
    with st.spinner("🔄 Procesando archivos y ejecutando conciliación..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_banco:
                tmp_banco.write(banco_file.getvalue())
                banco_path = tmp_banco.name
            
            aux_suffix = os.path.splitext(aux_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=aux_suffix) as tmp_aux:
                tmp_aux.write(aux_file.getvalue())
                aux_path = tmp_aux.name
            
            st.session_state.df_banco, st.session_state.banco_meta = parsear_banco_pdf(
                banco_path, usar_ocr=usar_ocr
            )
            st.session_state.banco_fmt = 'Banco PDF'
            st.session_state.archivo_banco = banco_file.name
            
            st.session_state.df_aux, st.session_state.aux_meta = parsear_auxiliar_pdf(
                aux_path, usar_ocr=usar_ocr
            )
            st.session_state.aux_fmt = 'Auxiliar PDF'
            st.session_state.archivo_auxiliar = aux_file.name
            
            with pdfplumber.open(banco_path) as pdf:
                texto_primera = pdf.pages[0].extract_text() or ''
            st.session_state.periodo = extraer_periodo_banco(texto_primera)
            
            matches, solo_banco, solo_aux, stats = comparar_documentos(
                st.session_state.df_banco,
                st.session_state.df_aux,
                tol_exacta=tol_exacta,
                tol_aprox=tol_aprox
            )
            
            st.session_state.matches_df = matches
            st.session_state.solo_banco_df = solo_banco
            st.session_state.solo_aux_df = solo_aux
            st.session_state.stats = stats
            
            st.session_state.banco_ruta = banco_path
            st.session_state.aux_ruta = aux_path
            
            historial_data = {
                'fecha_hora': datetime.now().isoformat(timespec='seconds'),
                'archivo_banco': st.session_state.archivo_banco,
                'archivo_auxiliar': st.session_state.archivo_auxiliar,
                'periodo': st.session_state.periodo,
                'n_banco': stats['n_banco'],
                'n_aux': stats['n_aux'],
                'n_exactas': stats['n_exactas'],
                'n_aprox': stats['n_aprox'],
                'n_solo_banco': stats['n_solo_banco'],
                'n_solo_aux': stats['n_solo_aux'],
                'tasa': stats['tasa'],
                'saldo_banco': stats['saldo_banco'],
                'saldo_aux': stats['saldo_aux'],
                'diferencia_neta': stats['diferencia_neta'],
            }
            guardar_historial(historial_data)
            
            if st.session_state.banco_meta:
                registrar_formato_pdf(
                    st.session_state.archivo_banco, 'BANCO',
                    list(st.session_state.df_banco.columns), '', [], ''
                )
            if st.session_state.aux_meta:
                registrar_formato_pdf(
                    st.session_state.archivo_auxiliar, 'AUXILIAR',
                    list(st.session_state.df_aux.columns), '', [], ''
                )
            
            st.balloons()
            st.success("✅ Conciliación completada exitosamente")
            
        except Exception as e:
            st.error(f"❌ Error procesando: {e}")
            logging.error(f"Error en procesamiento: {e}", exc_info=True)
        finally:
            for path in [st.session_state.get('banco_ruta'), st.session_state.get('aux_ruta')]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass

# ══════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.df_banco.empty and st.session_state.df_aux.empty:
    # ── LANDING PAGE / DASHBOARD ──────────────────────────────────────────
    st.markdown("""
    <div class="landing-container">
        <div class="landing-icon">🏦</div>
        <div class="landing-title">Conciliación Bancaria Inteligente</div>
        <div class="landing-sub">
            Automatice la conciliación entre sus extractos bancarios y auxiliares contables
            con matching inteligente, aprendizaje automático NC y exportación profesional.
        </div>
        <div class="landing-steps">
            <div class="landing-step">
                <div class="step-num">1</div>
                <div class="step-title">Cargar archivos</div>
                <div class="step-desc">Extracto bancario PDF + Auxiliar contable en cualquier formato</div>
            </div>
            <div class="landing-step">
                <div class="step-num">2</div>
                <div class="step-title">Configurar</div>
                <div class="step-desc">Ajuste tolerancias, active OCR si necesita</div>
            </div>
            <div class="landing-step">
                <div class="step-num">3</div>
                <div class="step-title">Procesar</div>
                <div class="step-desc">Conciliación automática en segundos</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="dash-card">
            <div class="card-icon">🔗</div>
            <div class="card-title">Matching Inteligente</div>
            <div class="card-sub">Exacto, aproximado, NC, agrupado y rechazos</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="dash-card">
            <div class="card-icon">🧠</div>
            <div class="card-title">Aprendizaje NC</div>
            <div class="card-sub">Catálogo automático de notas contables recurrentes</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="dash-card">
            <div class="card-icon">📊</div>
            <div class="card-title">Reportes Excel</div>
            <div class="card-sub">Exportación profesional con formatos por tipo de match</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="dash-card">
            <div class="card-icon">🔍</div>
            <div class="card-title">OCR Integrado</div>
            <div class="card-sub">Lectura de PDF escaneados con Tesseract</div>
        </div>
        """, unsafe_allow_html=True)
else:
    # ── HEADER ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="app-header">
        <h1>📊 Resultados de Conciliación</h1>
        <p>Período: {st.session_state.periodo} &nbsp;|&nbsp; 
           Banco: {st.session_state.archivo_banco} &nbsp;|&nbsp; 
           Auxiliar: {st.session_state.archivo_auxiliar}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ── KPIs SUPERIORES ──────────────────────────────────────────────────────
    stats = st.session_state.stats
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📥 Mov. Banco", stats.get('n_banco', 0))
    with col2:
        st.metric("📋 Asientos Aux", stats.get('n_aux', 0))
    with col3:
        st.metric("🎯 Exactas", stats.get('n_exactas', 0))
    with col4:
        st.metric("≈ Aprox", stats.get('n_aprox', 0))
    with col5:
        tasa = stats.get('tasa', 0)
        st.metric("📈 Tasa", f"{tasa:.1f}%")
    with col6:
        diff = stats.get('diferencia_neta', 0)
        st.metric("💰 Dif. Neta", cop(diff))
    
    # Barra de progreso de conciliación
    tasa_val = min(stats.get('tasa', 0), 100)
    color_bar = (
        '#28A745' if tasa_val >= 90 else
        '#FFC107' if tasa_val >= 70 else
        '#DC3545'
    )
    st.markdown(f"""
    <div style="margin: 0.5rem 0 1rem 0;">
        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-secondary);">
            <span>Progreso de conciliación</span>
            <span>{tasa_val:.1f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-bar-fill" style="width:{tasa_val}%; background:{color_bar};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Diagnóstico", "🏦 Banco", "📋 Auxiliar", "🔗 Comparación",
        "⚠️ Diferencias", "📄 Conciliación Formal", "📈 Visualizaciones", "📤 Exportar"
    ])
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 1: DIAGNÓSTICO
    # ══════════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("📊 Diagnóstico de Archivos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏦 Extracto Bancario")
            if st.session_state.banco_ruta:
                diag = diagnosticar_pdf(st.session_state.banco_ruta, 'BANCO')
                st.markdown(f"""
                <div class="dash-card">
                    <div class="card-title">Calidad del documento</div>
                    <div style="font-size:1.4rem; font-weight:700; margin:0.3rem 0;">{diag['calidad']}</div>
                    <div class="card-sub">
                        Págs: {diag['paginas_con_texto']}/{diag['paginas_total']} legibles
                        ({diag['pct_paginas_legibles']:.1f}%)
                        &nbsp;|&nbsp; Datos: {diag['pct_estimado_datos']:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if diag['advertencias']:
                    for adv in diag['advertencias']:
                        st.warning(adv)
                if diag['ocr_usado']:
                    st.info("🔍 Se utilizó OCR en algunas páginas")
        
        with col2:
            st.markdown("#### 📋 Auxiliar Contable")
            if st.session_state.aux_ruta:
                diag = diagnosticar_pdf(st.session_state.aux_ruta, 'AUXILIAR')
                st.markdown(f"""
                <div class="dash-card">
                    <div class="card-title">Calidad del documento</div>
                    <div style="font-size:1.4rem; font-weight:700; margin:0.3rem 0;">{diag['calidad']}</div>
                    <div class="card-sub">
                        Págs: {diag['paginas_con_texto']}/{diag['paginas_total']} legibles
                        ({diag['pct_paginas_legibles']:.1f}%)
                        &nbsp;|&nbsp; Docs encontrados: {diag['lineas_doc_encontradas']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if diag['advertencias']:
                    for adv in diag['advertencias']:
                        st.warning(adv)
                if diag['ocr_usado']:
                    st.info("🔍 Se utilizó OCR en algunas páginas")
        
        st.markdown("---")
        st.markdown("#### 📝 Muestra de Texto Extraído")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.banco_ruta:
                st.text_area("Banco", muestra_texto(st.session_state.banco_ruta), height=200,
                            key="diag_banco_text")
        with col2:
            if st.session_state.aux_ruta:
                st.text_area("Auxiliar", muestra_texto(st.session_state.aux_ruta), height=200,
                            key="diag_aux_text")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 2: BANCO
    # ══════════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("🏦 Movimientos Bancarios")
        df = st.session_state.df_banco
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_filtro = st.selectbox("Tipo", ['Todos', 'ABONO', 'CARGO'], key="banco_tipo")
            with col2:
                fecha_min = df['FECHA'].min()
                fecha_max = df['FECHA'].max()
                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    rango = st.date_input("Rango fechas", [fecha_min, fecha_max], key="banco_fecha")
            with col3:
                busqueda = st.text_input("🔍 Buscar descripción", key="banco_buscar")
            
            df_filtrado = df.copy()
            if tipo_filtro != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['TIPO'] == tipo_filtro]
            if busqueda:
                df_filtrado = df_filtrado[df_filtrado['DESCRIPCION'].str.contains(busqueda, case=False, na=False)]
            
            st.dataframe(
                df_filtrado[['FECHA_RAW', 'DESCRIPCION', 'VALOR', 'SALDO', 'TIPO', 'PAGINA']],
                use_container_width=True,
                height=400
            )
            
            # Resumen
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Movimientos", len(df))
            with c2:
                st.metric("Abonos", len(df[df['TIPO']=='ABONO']))
            with c3:
                st.metric("Cargos", len(df[df['TIPO']=='CARGO']))
            
            # ── ALERTAS DE COMISIONES ──
            st.markdown("---")
            st.markdown("#### 💰 Análisis de Comisiones Bancarias")
            comisiones_html = generar_reporte_comisiones(df)
            st.markdown(comisiones_html, unsafe_allow_html=True)
            
            # ── CLASIFICACIÓN PUC ──
            st.markdown("---")
            st.markdown("#### 📑 Clasificación por Plan de Cuentas (PUC)")
            df_puc = asignar_puc_a_dataframe(df)
            puc_resumen = resumen_por_puc(df)
            if not puc_resumen.empty:
                st.dataframe(puc_resumen, use_container_width=True, height=250)
            else:
                st.caption("Clasificación PUC no disponible")
            
            # Gráfico
            if len(df) > 0:
                fig, ax = plt.subplots(figsize=(10, 4))
                df_plot = df.dropna(subset=['FECHA', 'VALOR']).copy()
                if not df_plot.empty:
                    df_plot = df_plot.sort_values('FECHA')
                    colors = ['#28A745' if v >= 0 else '#DC3545' for v in df_plot['VALOR']]
                    ax.bar(range(len(df_plot)), df_plot['VALOR'], color=colors, alpha=0.75)
                    ax.axhline(y=0, color='#1A1A2E', linewidth=0.5)
                    ax.set_title('Movimientos Bancarios', fontweight='bold')
                    ax.set_ylabel('Valor (COP)')
                    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                    st.pyplot(fig)
        else:
            st.info("No hay datos bancarios cargados")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 3: AUXILIAR
    # ══════════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("📋 Asientos Auxiliar Contable")
        df = st.session_state.df_aux
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                col_filtro = st.selectbox("Columna", ['Todas', 'DEBITO', 'CREDITO'], key="aux_col")
            with col2:
                doc_filtro = st.text_input("🔍 Filtrar documento", key="aux_doc")
            with col3:
                busqueda = st.text_input("🔍 Buscar concepto", key="aux_buscar")
            
            df_filtrado = df.copy()
            if col_filtro != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['COLUMNA'] == col_filtro]
            if doc_filtro:
                df_filtrado = df_filtrado[df_filtrado['DOCUMENTO'].str.contains(doc_filtro, case=False, na=False)]
            if busqueda:
                df_filtrado = df_filtrado[df_filtrado['CONCEPTO'].str.contains(busqueda, case=False, na=False)]
            
            st.dataframe(
                df_filtrado[['DOCUMENTO', 'FECHA_RAW', 'CONCEPTO', 'DEBITO', 'CREDITO', 'COLUMNA', 'VALOR_NETO']],
                use_container_width=True,
                height=400
            )
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Asientos", len(df))
            with c2:
                st.metric("Débito", len(df[df['COLUMNA']=='DEBITO']))
            with c3:
                st.metric("Crédito", len(df[df['COLUMNA']=='CREDITO']))
            
            if len(df) > 0:
                fig, ax = plt.subplots(figsize=(10, 4))
                doc_counts = df['DOCUMENTO'].str[:2].value_counts()
                doc_counts.plot(kind='bar', ax=ax, color='#1F4E79')
                ax.set_title('Asientos por Tipo de Documento', fontweight='bold')
                ax.set_ylabel('Cantidad')
                plt.xticks(rotation=0)
                st.pyplot(fig)
        else:
            st.info("No hay datos de auxiliar cargados")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 4: COMPARACIÓN
    # ══════════════════════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("🔗 Resultados de Conciliación")
        matches = st.session_state.matches_df
        
        if not matches.empty:
            tipos = ['Todos'] + sorted(matches['tipo'].unique().tolist())
            tipo_sel = st.selectbox("Filtrar por tipo de match", tipos, key="match_tipo")
            
            df_show = matches if tipo_sel == 'Todos' else matches[matches['tipo'] == tipo_sel]
            
            display_cols = ['banco_idx', 'aux_idx', 'tipo', 'valor_banco', 'valor_aux', 'diff',
                           'concepto_banco', 'concepto_aux', 'documento_aux']
            df_display = df_show[display_cols].copy()
            df_display.columns = ['Idx Banco', 'Idx Aux', 'Tipo', 'Valor Banco', 'Valor Aux', 'Diferencia',
                                  'Concepto Banco', 'Concepto Aux', 'Documento']
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            st.markdown("#### 📊 Desglose por tipo de match")
            tipo_stats = matches['tipo'].value_counts()
            cols = st.columns(len(tipo_stats))
            for i, (t, c) in enumerate(tipo_stats.items()):
                with cols[i]:
                    st.metric(t, c)
        else:
            st.info("No hay coincidencias encontradas")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 5: DIFERENCIAS
    # ══════════════════════════════════════════════════════════════════════════════
    with tab5:
        st.subheader("⚠️ Diferencias y Pendientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔴 Solo en Banco (sin match)")
            solo_banco = st.session_state.solo_banco_df
            if not solo_banco.empty:
                st.dataframe(
                    solo_banco[['FECHA_RAW', 'DESCRIPCION', 'VALOR', 'SALDO', 'TIPO']],
                    use_container_width=True, height=300
                )
                st.metric("Total solo banco", f"{len(solo_banco)} mov | {cop(solo_banco['VALOR'].sum())}")
            else:
                st.success("✅ Todos los movimientos bancarios conciliados")
        
        with col2:
            st.markdown("#### 🔵 Solo en Auxiliar (sin match)")
            solo_aux = st.session_state.solo_aux_df
            if not solo_aux.empty:
                st.dataframe(
                    solo_aux[['DOCUMENTO', 'FECHA_RAW', 'CONCEPTO', 'DEBITO', 'CREDITO', 'VALOR_NETO']],
                    use_container_width=True, height=300
                )
                st.metric("Total solo aux", f"{len(solo_aux)} asientos | {cop(solo_aux['VALOR_NETO'].sum())}")
            else:
                st.success("✅ Todos los asientos auxiliares conciliados")
        
        st.markdown("---")
        st.markdown("#### 🔍 Validación Aritmética")
        diff_neta = stats.get('diferencia_neta', 0)
        if abs(diff_neta) > umbral_diff:
            st.error(f"⚠️ Diferencia neta: {cop(diff_neta)} — Supera el umbral de {cop(umbral_diff)}")
        else:
            st.success(f"✅ Diferencia neta: {cop(diff_neta)} — Dentro de tolerancia aceptable")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 6: CONCILIACIÓN FORMAL
    # ══════════════════════════════════════════════════════════════════════════════
    with tab6:
        st.subheader("📄 Acta de Conciliación Formal")
        
        st.markdown(f"""
        <div class="dash-card">
            <div class="card-title">DATOS DEL PROCESO</div>
            <table style="width:100%; font-size:0.85rem; margin-top:0.5rem;">
                <tr><td style="color:var(--text-secondary);">Período:</td><td><strong>{st.session_state.periodo}</strong></td></tr>
                <tr><td style="color:var(--text-secondary);">Extracto Bancario:</td><td><strong>{st.session_state.archivo_banco}</strong></td></tr>
                <tr><td style="color:var(--text-secondary);">Auxiliar Contable:</td><td><strong>{st.session_state.archivo_auxiliar}</strong></td></tr>
                <tr><td style="color:var(--text-secondary);">Fecha de Proceso:</td><td><strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Cuadre de Saldos")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="dash-card">
                <div class="card-title">🏦 SALDO SEGÚN BANCO</div>
                <div class="card-value">{cop(stats.get('saldo_banco', 0))}</div>
                <div class="card-sub">
                    (+) Pendientes banco: {cop(st.session_state.solo_banco_df['VALOR'].sum() if not st.session_state.solo_banco_df.empty else 0)}<br>
                    (−) Pendientes auxiliar: {cop(st.session_state.solo_aux_df['VALOR_NETO'].sum() if not st.session_state.solo_aux_df.empty else 0)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="dash-card">
                <div class="card-title">📋 SALDO SEGÚN AUXILIAR</div>
                <div class="card-value">{cop(stats.get('saldo_aux', 0))}</div>
                <div class="card-sub">
                    (+) Pendientes auxiliar: {cop(st.session_state.solo_aux_df['VALOR_NETO'].sum() if not st.session_state.solo_aux_df.empty else 0)}<br>
                    (−) Pendientes banco: {cop(st.session_state.solo_banco_df['VALOR'].sum() if not st.session_state.solo_banco_df.empty else 0)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📝 Observaciones")
        if stats.get('n_solo_banco', 0) > 0:
            st.warning(f"⚠️ {stats['n_solo_banco']} movimientos solo en banco — Revisar depósitos en tránsito o cheques no cobrados")
        if stats.get('n_solo_aux', 0) > 0:
            st.warning(f"⚠️ {stats['n_solo_aux']} asientos solo en auxiliar — Revisar cargos bancarios no registrados")
        diff_neta = stats.get('diferencia_neta', 0)
        if abs(diff_neta) <= umbral_diff:
            st.success("✅ Conciliación cuadrada dentro de tolerancia aceptable")
        else:
            st.error("❌ Conciliación con diferencia significativa — Requiere investigación")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 7: VISUALIZACIONES
    # ══════════════════════════════════════════════════════════════════════════════
    with tab7:
        st.subheader("📈 Visualizaciones")
        
        matches = st.session_state.matches_df
        
        if not matches.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig, ax = plt.subplots(figsize=(8, 6))
                exactas = matches[matches['tipo'] == 'EXACTA']
                aprox = matches[matches['tipo'] != 'EXACTA']
                
                if not exactas.empty:
                    ax.scatter(exactas['valor_banco'], exactas['valor_aux'],
                              alpha=0.6, label='Exacta', color='#28A745', s=50)
                if not aprox.empty:
                    ax.scatter(aprox['valor_banco'], aprox['valor_aux'],
                              alpha=0.6, label='Aproximada', color='#D4AF37', s=50)
                
                min_val = min(matches['valor_banco'].min(), matches['valor_aux'].min())
                max_val = max(matches['valor_banco'].max(), matches['valor_aux'].max())
                ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3)
                
                ax.set_xlabel('Valor Banco', fontweight='bold')
                ax.set_ylabel('Valor Auxiliar', fontweight='bold')
                ax.set_title('Valor Banco vs Auxiliar', fontweight='bold')
                ax.legend()
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                st.pyplot(fig)
            
            with col2:
                fig, ax = plt.subplots(figsize=(8, 6))
                diffs = matches['diff'].abs()
                ax.hist(diffs, bins=20, edgecolor='black', alpha=0.7, color='#1F4E79')
                ax.axvline(TOL_EXACTA, color='#28A745', linestyle='--', label=f'Tol. Exacta ({TOL_EXACTA})')
                ax.axvline(diffs.mean(), color='#DC3545', linestyle='--', label=f'Media ({diffs.mean():.2f})')
                ax.set_xlabel('Diferencia Absoluta (COP)', fontweight='bold')
                ax.set_ylabel('Frecuencia', fontweight='bold')
                ax.set_title('Distribución de Diferencias', fontweight='bold')
                ax.legend()
                st.pyplot(fig)
            
            st.markdown("### 📅 Timeline de Conciliación")
            if 'FECHA' in st.session_state.df_banco.columns:
                fig, ax = plt.subplots(figsize=(12, 4))
                df_b = st.session_state.df_banco.dropna(subset=['FECHA', 'VALOR'])
                if not df_b.empty:
                    df_b = df_b.sort_values('FECHA')
                    colors = ['#28A745' if m else '#DC3545' for m in df_b.index.isin(matches['banco_idx'])]
                    ax.bar(df_b['FECHA'], df_b['VALOR'], color=colors, alpha=0.7, width=0.8)
                    ax.set_title('Movimientos Bancarios (Verde=Conciliado, Rojo=Pendiente)', fontweight='bold')
                    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
        else:
            st.info("No hay datos para visualizar")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 8: EXPORTAR EXCEL
    # ══════════════════════════════════════════════════════════════════════════════
    with tab8:
        st.subheader("📤 Exportar Reporte")
        
        if st.button("📊 Generar Reporte Excel Profesional", type="primary", use_container_width=True):
            with st.spinner("Generando archivo Excel..."):
                try:
                    excel_bytes = generar_excel_conciliacion(
                        matches_df=st.session_state.matches_df,
                        solo_banco_df=st.session_state.solo_banco_df,
                        solo_aux_df=st.session_state.solo_aux_df,
                        stats=st.session_state.stats,
                        banco_meta=st.session_state.banco_meta,
                        aux_meta=st.session_state.aux_meta,
                        banco_fmt=st.session_state.banco_fmt,
                        aux_fmt=st.session_state.aux_fmt,
                        periodo=st.session_state.periodo,
                        archivo_banco=st.session_state.archivo_banco,
                        archivo_auxiliar=st.session_state.archivo_auxiliar,
                    )
                    
                    if OFFLINE_MODE:
                        ruta = _auto_guardar_excel(excel_bytes, f"conciliacion_{st.session_state.periodo.replace('/', '-')}.xlsx")
                        if ruta:
                            st.success(f"✅ Guardado en: {ruta}")
                    
                    st.download_button(
                        label="⬇️ Descargar Reporte Excel",
                        data=excel_bytes,
                        file_name=f"conciliacion_{st.session_state.periodo.replace('/', '-')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    if OFFLINE_MODE:
                        historial_data = {
                            'fecha_hora': datetime.now().isoformat(timespec='seconds'),
                            'archivo_banco': st.session_state.archivo_banco,
                            'archivo_auxiliar': st.session_state.archivo_auxiliar,
                            'periodo': st.session_state.periodo,
                            'n_banco': stats['n_banco'],
                            'n_aux': stats['n_aux'],
                            'n_exactas': stats['n_exactas'],
                            'n_aprox': stats['n_aprox'],
                            'n_solo_banco': stats['n_solo_banco'],
                            'n_solo_aux': stats['n_solo_aux'],
                            'tasa': stats['tasa'],
                            'saldo_banco': stats['saldo_banco'],
                            'saldo_aux': stats['saldo_aux'],
                            'diferencia_neta': stats['diferencia_neta'],
                            'excel_path': ruta if 'ruta' in locals() else '',
                        }
                        guardar_historial(historial_data)
                    
                except Exception as e:
                    st.error(f"❌ Error generando Excel: {e}")
                    logging.error(f"Error exportando Excel: {e}", exc_info=True)
        
        st.markdown("---")
        
        # ── EXPORTAR PDF FIRMADO ──────────────────────────────────────────
        st.markdown("### 📄 Reporte PDF Firmado Digitalmente")
        if st.button("🔐 Generar PDF con Firma Digital SHA-256", type="secondary", use_container_width=True):
            with st.spinner("Generando PDF firmado..."):
                try:
                    pdf_bytes, pdf_hash = generar_pdf_conciliacion(
                        matches_df=st.session_state.matches_df,
                        solo_banco_df=st.session_state.solo_banco_df,
                        solo_aux_df=st.session_state.solo_aux_df,
                        stats=st.session_state.stats,
                        periodo=st.session_state.periodo,
                        archivo_banco=st.session_state.archivo_banco,
                        archivo_auxiliar=st.session_state.archivo_auxiliar,
                    )
                    
                    st.download_button(
                        label="⬇️ Descargar PDF Firmado",
                        data=pdf_bytes,
                        file_name=f"conciliacion_{st.session_state.periodo.replace('/', '-')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.info(f"🔑 Hash SHA-256: `{pdf_hash}`")
                    st.caption("Este hash garantiza la integridad del documento para validez legal.")
                    
                except Exception as e:
                    st.error(f"❌ Error generando PDF: {e}")
                    logging.error(f"Error exportando PDF: {e}", exc_info=True)
        
        st.markdown("---")
        st.markdown("### 📑 Hojas incluidas en el reporte Excel:")
        for i, hoja in enumerate([
            "**Resumen** — KPIs ejecutivos y semáforo de conciliación",
            "**Exactas** — Matches exactos (verde)",
            "**Aproximados** — Matches NC, Agrupados, Rechazos (coloreados)",
            "**Solo_Banco** — Movimientos solo en banco (rosa)",
            "**Solo_Auxiliar** — Asientos solo en auxiliar (índigo)",
            "**Metadatos** — Información de archivos, formatos, fechas"
        ], 1):
            st.write(f"{i}. {hoja}")

# ═════════════════════════════════════════════════════════════════════════════════
# SECCIÓN META: HISTORIAL Y CATÁLOGO NC
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    with st.expander("📚 Historial de Conciliaciones", expanded=False):
        if OFFLINE_MODE:
            historial = leer_historial(8)
            if historial:
                df_hist = pd.DataFrame(historial, columns=[
                    'Fecha', 'Banco', 'Auxiliar', 'Período', 'Tasa%', 'Exactas', 'Mov.Banco', 'Diff Neta'
                ])
                st.dataframe(df_hist, use_container_width=True)
            else:
                st.info("No hay historial disponible aún")
        else:
            st.info("Historial disponible en modo local (SQLite)")

with col2:
    with st.expander("🧠 Catálogo NC — Aprendizaje Automático", expanded=False):
        if OFFLINE_MODE:
            rows, total, pend = listar_catalogo_nc(10)
            st.write(f"✅ Reglas aprobadas: **{total}** | ⏳ Candidatos: **{pend}**")
            if rows:
                df_cat = pd.DataFrame(rows, columns=[
                    'UUID', 'Tokens Banco', 'Tokens Aux', 'Confirmaciones', 'Nivel', 'Aprobado', 'Última vez'
                ])
                st.dataframe(df_cat, use_container_width=True)
            else:
                st.info("Catálogo vacío — Se llena al confirmar matches NC")
        else:
            st.info("Catálogo NC disponible en modo local (SQLite)")

# ═════════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="app-footer">
    <strong>CREDIEXPRESS POPAYÁN SAS</strong> &nbsp;|&nbsp; 
    Conciliación Bancaria v2.0 — Arquitectura Modular &nbsp;|&nbsp;
    © 2025 — Todos los derechos reservados
</div>
""", unsafe_allow_html=True)