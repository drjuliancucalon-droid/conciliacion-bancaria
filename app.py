"""
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria Interactiva Premium
Soporte multiformato (PDF, CSV, Excel, TXT) + OCR para PDF escaneados
Arquitectura modular refactorizada
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
)

from utils.pdf_diagnostico import OCR_AVAILABLE

# Configuración de página
st.set_page_config(
    page_title="Conciliación CREDIEXPRESS",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS PERSONALIZADO
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1F4E79 0%, #2E75B6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2E75B6;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F4E79 !important;
        color: white !important;
    }
    .dataframe-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #28a745;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 1px solid #17a2b8;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN BÁSICA (FASE 7)
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
    
    st.text_input(
        "Contraseña", type="password",
        on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Contraseña incorrecta")
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
# SIDEBAR - CARGA DE ARCHIVOS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div class="main-header">
        <h2>🏦 Conciliación Bancaria</h2>
        <p>CREDIEXPRESS POPAYÁN SAS</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📁 Cargar Archivos")
    
    # Archivo Banco
    banco_file = st.file_uploader(
        "Extracto Bancario (PDF)",
        type=['pdf'],
        key="banco_uploader",
        help="PDF del extracto bancario"
    )
    
    # Archivo Auxiliar
    aux_file = st.file_uploader(
        "Auxiliar Contable (PDF, CSV, Excel, TXT)",
        type=['pdf', 'csv', 'xlsx', 'xls', 'txt'],
        key="aux_uploader",
        help="Auxiliar contable en múltiples formatos"
    )
    
    st.markdown("---")
    
    # Opciones OCR
    st.markdown("### ⚙️ Opciones")
    usar_ocr = st.checkbox(
        "Usar OCR para PDF escaneados",
        value=False,
        disabled=not OCR_AVAILABLE,
        help="Requiere pdf2image y pytesseract instalados"
    )
    if not OCR_AVAILABLE:
        st.caption("⚠️ OCR no disponible. Instale pdf2image y pytesseract.")
    
    # Tolerancias
    st.markdown("### 🎯 Tolerancias")
    tol_exacta = st.number_input(
        "Tolerancia Exacta (COP)",
        min_value=0.0, max_value=1000.0, value=TOL_EXACTA, step=1.0
    )
    tol_aprox = st.number_input(
        "Tolerancia Aproximada (%)",
        min_value=0.1, max_value=10.0, value=TOL_APROX*100, step=0.1
    ) / 100
    
    # Validación
    st.markdown("### 🔍 Validación")
    umbral_diff = st.number_input(
        "Umbral Diferencia Neta (COP)",
        min_value=1.0, max_value=1000000.0, value=float(UMBRAL_DIF_NETA), step=100.0
    )
    
    st.markdown("---")
    
    # Botón procesar
    procesar = st.button(
        "🔄 Procesar Conciliación",
        type="primary",
        use_container_width=True,
        disabled=not (banco_file and aux_file)
    )
    
    # Información del entorno
    st.markdown("---")
    st.caption(f"Modo: {'🖥️ Local (SQLite)' if OFFLINE_MODE else '☁️ Cloud (Google Sheets)'}")
    if OCR_AVAILABLE:
        st.caption("✅ OCR disponible")

# ══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

if procesar and banco_file and aux_file:
    with st.spinner("Procesando archivos..."):
        try:
            # Guardar archivos temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_banco:
                tmp_banco.write(banco_file.getvalue())
                banco_path = tmp_banco.name
            
            aux_suffix = os.path.splitext(aux_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=aux_suffix) as tmp_aux:
                tmp_aux.write(aux_file.getvalue())
                aux_path = tmp_aux.name
            
            # Parsear banco
            st.session_state.df_banco, st.session_state.banco_meta = parsear_banco_pdf(
                banco_path, usar_ocr=usar_ocr
            )
            st.session_state.banco_fmt = 'Banco PDF'
            st.session_state.archivo_banco = banco_file.name
            
            # Parsear auxiliar
            st.session_state.df_aux, st.session_state.aux_meta = parsear_auxiliar_pdf(
                aux_path, usar_ocr=usar_ocr
            )
            st.session_state.aux_fmt = 'Auxiliar PDF'
            st.session_state.archivo_auxiliar = aux_file.name
            
            # Extraer período
            with pdfplumber.open(banco_path) as pdf:
                texto_primera = pdf.pages[0].extract_text() or ''
            st.session_state.periodo = extraer_periodo_banco(texto_primera)
            
            # Ejecutar conciliación
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
            
            # Guardar rutas para exportación
            st.session_state.banco_ruta = banco_path
            st.session_state.aux_ruta = aux_path
            
            # Guardar en historial
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
            
            # Registrar formatos aprendidos
            if st.session_state.banco_meta:
                registrar_formato_pdf(
                    st.session_state.archivo_banco, 'BANCO',
                    list(st.session_state.df_banco.columns),
                    '', [], ''
                )
            if st.session_state.aux_meta:
                registrar_formato_pdf(
                    st.session_state.archivo_auxiliar, 'AUXILIAR',
                    list(st.session_state.df_aux.columns),
                    '', [], ''
                )
            
            st.success("✅ Conciliación completada exitosamente")
            
        except Exception as e:
            st.error(f"Error procesando: {e}")
            logging.error(f"Error en procesamiento: {e}", exc_info=True)
        finally:
            # Limpiar archivos temporales
            for path in [st.session_state.get('banco_ruta'), st.session_state.get('aux_ruta')]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass

# ══════════════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.df_banco.empty and st.session_state.df_aux.empty:
    st.info("👈 Cargue los archivos en el panel lateral y presione 'Procesar Conciliación'")
else:
    # Métricas superiores
    col1, col2, col3, col4, col5 = st.columns(5)
    stats = st.session_state.stats
    
    with col1:
        st.metric("Mov. Banco", stats.get('n_banco', 0))
    with col2:
        st.metric("Asientos Aux", stats.get('n_aux', 0))
    with col3:
        st.metric("Exactas", stats.get('n_exactas', 0))
    with col4:
        st.metric("Aprox.", stats.get('n_aprox', 0))
    with col5:
        sem = semaforo_conciliacion(
            stats.get('tasa', 0),
            stats.get('n_solo_banco', 0),
            stats.get('n_solo_aux', 0)
        )
        st.metric("Tasa", f"{stats.get('tasa', 0):.1f}% {sem}")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Diagnóstico", "🏦 Banco", "📋 Auxiliar", "🔗 Comparación",
        "⚠️ Diferencias", "📄 Conciliación Formal", "📈 Visualizaciones", "📤 Exportar Excel"
    ])
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 1: DIAGNÓSTICO
    # ══════════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("📊 Diagnóstico de Archivos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Extracto Bancario")
            if st.session_state.banco_ruta:
                diag = diagnosticar_pdf(st.session_state.banco_ruta, 'BANCO')
                st.write(f"**Calidad:** {diag['calidad']}")
                st.write(f"Páginas legibles: {diag['paginas_con_texto']}/{diag['paginas_total']} ({diag['pct_paginas_legibles']:.1f}%)")
                st.write(f"Datos estimados: {diag['pct_estimado_datos']:.1f}%")
                if diag['advertencias']:
                    for adv in diag['advertencias']:
                        st.warning(adv)
                if diag['ocr_usado']:
                    st.info("🔍 OCR utilizado en algunas páginas")
        
        with col2:
            st.markdown("#### Auxiliar Contable")
            if st.session_state.aux_ruta:
                diag = diagnosticar_pdf(st.session_state.aux_ruta, 'AUXILIAR')
                st.write(f"**Calidad:** {diag['calidad']}")
                st.write(f"Páginas legibles: {diag['paginas_con_texto']}/{diag['paginas_total']} ({diag['pct_paginas_legibles']:.1f}%)")
                st.write(f"Datos estimados: {diag['pct_estimado_datos']:.1f}%")
                st.write(f"Documentos encontrados: {diag['lineas_doc_encontradas']}")
                if diag['advertencias']:
                    for adv in diag['advertencias']:
                        st.warning(adv)
                if diag['ocr_usado']:
                    st.info("🔍 OCR utilizado en algunas páginas")
        
        # Muestra de texto
        st.markdown("---")
        st.markdown("#### Muestra de Texto Extraído")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.banco_ruta:
                st.text_area("Banco", muestra_texto(st.session_state.banco_ruta), height=200)
        with col2:
            if st.session_state.aux_ruta:
                st.text_area("Auxiliar", muestra_texto(st.session_state.aux_ruta), height=200)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 2: BANCO
    # ══════════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("🏦 Movimientos Bancarios")
        df = st.session_state.df_banco
        if not df.empty:
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_filtro = st.selectbox("Tipo", ['Todos', 'ABONO', 'CARGO'], key="banco_tipo")
            with col2:
                fecha_min = df['FECHA'].min()
                fecha_max = df['FECHA'].max()
                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    rango = st.date_input("Rango fechas", [fecha_min, fecha_max], key="banco_fecha")
            with col3:
                busqueda = st.text_input("Buscar descripción", key="banco_buscar")
            
            # Aplicar filtros
            df_filtrado = df.copy()
            if tipo_filtro != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['TIPO'] == tipo_filtro]
            if busqueda:
                df_filtrado = df_filtrado[df_filtrado['DESCRIPCION'].str.contains(busqueda, case=False, na=False)]
            
            # Mostrar
            st.dataframe(
                df_filtrado[['FECHA_RAW', 'DESCRIPCION', 'VALOR', 'SALDO', 'TIPO', 'PAGINA']],
                use_container_width=True,
                height=400
            )
            
            # Resumen
            st.markdown("**Resumen:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"Total: {len(df)} movimientos")
            with c2:
                st.write(f"Abonos: {len(df[df['TIPO']=='ABONO'])}")
            with c3:
                st.write(f"Cargos: {len(df[df['TIPO']=='CARGO'])}")
            
            # Gráfico
            if len(df) > 0:
                fig, ax = plt.subplots(figsize=(10, 4))
                df_plot = df.dropna(subset=['FECHA', 'VALOR']).copy()
                if not df_plot.empty:
                    df_plot = df_plot.sort_values('FECHA')
                    colors = ['green' if v >= 0 else 'red' for v in df_plot['VALOR']]
                    ax.bar(range(len(df_plot)), df_plot['VALOR'], color=colors, alpha=0.7)
                    ax.axhline(y=0, color='black', linewidth=0.5)
                    ax.set_title('Movimientos Bancarios (Verde=Abono, Rojo=Cargo)')
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
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                col_filtro = st.selectbox("Columna", ['Todas', 'DEBITO', 'CREDITO'], key="aux_col")
            with col2:
                doc_filtro = st.text_input("Filtrar documento", key="aux_doc")
            with col3:
                busqueda = st.text_input("Buscar concepto", key="aux_buscar")
            
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
            
            # Resumen
            st.markdown("**Resumen:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"Total: {len(df)} asientos")
            with c2:
                st.write(f"Débito: {len(df[df['COLUMNA']=='DEBITO'])}")
            with c3:
                st.write(f"Crédito: {len(df[df['COLUMNA']=='CREDITO'])}")
            
            # Gráfico por tipo de documento
            if len(df) > 0:
                fig, ax = plt.subplots(figsize=(10, 4))
                doc_counts = df['DOCUMENTO'].str[:2].value_counts()
                doc_counts.plot(kind='bar', ax=ax, color='steelblue')
                ax.set_title('Asientos por Tipo de Documento')
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
            # Filtro por tipo
            tipos = ['Todos'] + sorted(matches['tipo'].unique().tolist())
            tipo_sel = st.selectbox("Filtrar por tipo", tipos, key="match_tipo")
            
            df_show = matches if tipo_sel == 'Todos' else matches[matches['tipo'] == tipo_sel]
            
            # Formatear para mostrar
            display_cols = ['banco_idx', 'aux_idx', 'tipo', 'valor_banco', 'valor_aux', 'diff',
                           'concepto_banco', 'concepto_aux', 'documento_aux']
            df_display = df_show[display_cols].copy()
            df_display.columns = ['Idx Banco', 'Idx Aux', 'Tipo', 'Valor Banco', 'Valor Aux', 'Diferencia',
                                  'Concepto Banco', 'Concepto Aux', 'Documento']
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Estadísticas por tipo
            st.markdown("**Desglose por tipo:**")
            tipo_stats = matches['tipo'].value_counts()
            for t, c in tipo_stats.items():
                st.write(f"  • {t}: {c}")
        else:
            st.info("No hay coincidencias encontradas")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 5: DIFERENCIAS
    # ══════════════════════════════════════════════════════════════════════════════
    with tab5:
        st.subheader("⚠️ Diferencias y Pendientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Solo en Banco (sin match)")
            solo_banco = st.session_state.solo_banco_df
            if not solo_banco.empty:
                st.dataframe(
                    solo_banco[['FECHA_RAW', 'DESCRIPCION', 'VALOR', 'SALDO', 'TIPO']],
                    use_container_width=True,
                    height=300
                )
                st.write(f"Total: {len(solo_banco)} | Suma: {cop(solo_banco['VALOR'].sum())}")
            else:
                st.success("✅ Todos los movimientos bancarios conciliados")
        
        with col2:
            st.markdown("#### Solo en Auxiliar (sin match)")
            solo_aux = st.session_state.solo_aux_df
            if not solo_aux.empty:
                st.dataframe(
                    solo_aux[['DOCUMENTO', 'FECHA_RAW', 'CONCEPTO', 'DEBITO', 'CREDITO', 'VALOR_NETO']],
                    use_container_width=True,
                    height=300
                )
                st.write(f"Total: {len(solo_aux)} | Suma: {cop(solo_aux['VALOR_NETO'].sum())}")
            else:
                st.success("✅ Todos los asientos auxiliares conciliados")
        
        # Validación aritmética (FASE 7)
        st.markdown("---")
        st.markdown("#### 🔍 Validación Aritmética")
        diff_neta = stats.get('diferencia_neta', 0)
        if abs(diff_neta) > umbral_diff:
            st.error(f"⚠️ Diferencia neta: {cop(diff_neta)} (supera umbral de {cop(umbral_diff)})")
        else:
            st.success(f"✅ Diferencia neta: {cop(diff_neta)} (dentro de tolerancia)")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 6: CONCILIACIÓN FORMAL
    # ══════════════════════════════════════════════════════════════════════════════
    with tab6:
        st.subheader("📄 Conciliación Formal")
        
        st.markdown(f"""
        **Período:** {st.session_state.periodo}  
        **Extracto Bancario:** {st.session_state.archivo_banco}  
        **Auxiliar Contable:** {st.session_state.archivo_auxiliar}  
        **Fecha Proceso:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
        
        # Cuadro de conciliación
        st.markdown("### Cuadro de Conciliación")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**SALDO BANCO**")
            st.write(f"Saldo según banco: {cop(stats.get('saldo_banco', 0))}")
            st.write(f"(+) Movimientos solo en banco: {cop(st.session_state.solo_banco_df['VALOR'].sum() if not st.session_state.solo_banco_df.empty else 0)}")
            st.write(f"(-) Movimientos solo en auxiliar: {cop(st.session_state.solo_aux_df['VALOR_NETO'].sum() if not st.session_state.solo_aux_df.empty else 0)}")
            st.write(f"**Saldo conciliado banco: {cop(stats.get('saldo_banco', 0) - st.session_state.solo_banco_df['VALOR'].sum() + st.session_state.solo_aux_df['VALOR_NETO'].sum() if not st.session_state.solo_aux_df.empty else stats.get('saldo_banco', 0))}**")
        
        with col2:
            st.markdown("**SALDO AUXILIAR**")
            st.write(f"Saldo según auxiliar: {cop(stats.get('saldo_aux', 0))}")
            st.write(f"(+) Asientos solo en auxiliar: {cop(st.session_state.solo_aux_df['VALOR_NETO'].sum() if not st.session_state.solo_aux_df.empty else 0)}")
            st.write(f"(-) Movimientos solo en banco: {cop(st.session_state.solo_banco_df['VALOR'].sum() if not st.session_state.solo_banco_df.empty else 0)}")
            st.write(f"**Saldo conciliado auxiliar: {cop(stats.get('saldo_aux', 0) + st.session_state.solo_aux_df['VALOR_NETO'].sum() - st.session_state.solo_banco_df['VALOR'].sum() if not st.session_state.solo_banco_df.empty else stats.get('saldo_aux', 0))}**")
        
        st.markdown("---")
        st.markdown("### Observaciones")
        if stats.get('n_solo_banco', 0) > 0:
            st.warning(f"⚠️ {stats['n_solo_banco']} movimientos solo en banco - revisar depósitos en tránsito o cheques no cobrados")
        if stats.get('n_solo_aux', 0) > 0:
            st.warning(f"⚠️ {stats['n_solo_aux']} asientos solo en auxiliar - revisar cargos bancarios no registrados")
        if abs(diff_neta) <= umbral_diff:
            st.success("✅ Conciliación cuadrada dentro de tolerancia aceptable")
        else:
            st.error("❌ Conciliación con diferencia significativa - requiere investigación")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 7: VISUALIZACIONES
    # ══════════════════════════════════════════════════════════════════════════════
    with tab7:
        st.subheader("📈 Visualizaciones")
        
        matches = st.session_state.matches_df
        
        if not matches.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de dispersión valor banco vs auxiliar
                fig, ax = plt.subplots(figsize=(8, 6))
                exactas = matches[matches['tipo'] == 'EXACTA']
                aprox = matches[matches['tipo'] != 'EXACTA']
                
                if not exactas.empty:
                    ax.scatter(exactas['valor_banco'], exactas['valor_aux'], 
                              alpha=0.6, label='Exacta', color='green', s=50)
                if not aprox.empty:
                    ax.scatter(aprox['valor_banco'], aprox['valor_aux'], 
                              alpha=0.6, label='Aproximada', color='orange', s=50)
                
                # Línea identidad
                min_val = min(matches['valor_banco'].min(), matches['valor_aux'].min())
                max_val = max(matches['valor_banco'].max(), matches['valor_aux'].max())
                ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3)
                
                ax.set_xlabel('Valor Banco')
                ax.set_ylabel('Valor Auxiliar')
                ax.set_title('Valor Banco vs Auxiliar')
                ax.legend()
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                st.pyplot(fig)
            
            with col2:
                # Distribución de diferencias
                fig, ax = plt.subplots(figsize=(8, 6))
                diffs = matches['diff'].abs()
                ax.hist(diffs, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
                ax.axvline(TOL_EXACTA, color='green', linestyle='--', label=f'Tol. Exacta ({TOL_EXACTA})')
                ax.axvline(diffs.mean(), color='red', linestyle='--', label=f'Media ({diffs.mean():.2f})')
                ax.set_xlabel('Diferencia Absoluta (COP)')
                ax.set_ylabel('Frecuencia')
                ax.set_title('Distribución de Diferencias')
                ax.legend()
                st.pyplot(fig)
            
            # Timeline de matches
            st.markdown("### Timeline de Conciliación")
            if 'FECHA' in st.session_state.df_banco.columns:
                fig, ax = plt.subplots(figsize=(12, 4))
                df_b = st.session_state.df_banco.dropna(subset=['FECHA', 'VALOR'])
                if not df_b.empty:
                    df_b = df_b.sort_values('FECHA')
                    colors = ['green' if m else 'red' for m in df_b.index.isin(matches['banco_idx'])]
                    ax.bar(df_b['FECHA'], df_b['VALOR'], color=colors, alpha=0.7, width=0.8)
                    ax.set_title('Movimientos Bancarios (Verde=Conciliado, Rojo=Pendiente)')
                    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
        else:
            st.info("No hay datos para visualizar")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 8: EXPORTAR EXCEL
    # ══════════════════════════════════════════════════════════════════════════════
    with tab8:
        st.subheader("📤 Exportar a Excel")
        
        if st.button("📊 Generar Reporte Excel", type="primary", use_container_width=True):
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
                    
                    # Guardar localmente si es modo offline
                    if OFFLINE_MODE:
                        ruta = _auto_guardar_excel(excel_bytes, f"conciliacion_{st.session_state.periodo.replace('/', '-')}.xlsx")
                        if ruta:
                            st.success(f"✅ Guardado en: {ruta}")
                    
                    # Botón de descarga
                    st.download_button(
                        label="⬇️ Descargar Excel",
                        data=excel_bytes,
                        file_name=f"conciliacion_{st.session_state.periodo.replace('/', '-')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    # Actualizar historial con ruta del Excel
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
                    st.error(f"Error generando Excel: {e}")
                    logging.error(f"Error exportando Excel: {e}", exc_info=True)
        
        st.markdown("---")
        st.markdown("### Hojas incluidas en el reporte:")
        st.write("1. **Resumen** - KPIs ejecutivos y semáforo")
        st.write("2. **Exactas** - Matches exactos (verde)")
        st.write("3. **Aproximados** - Matches aproximados, NC, Agrupados, Rechazos (coloreados)")
        st.write("4. **Solo_Banco** - Movimientos solo en banco (rosa)")
        st.write("5. **Solo_Auxiliar** - Asientos solo en auxiliar (índigo)")
        st.write("6. **Metadatos** - Información de archivos, formatos, fechas")

# ═════════════════════════════════════════════════════════════════════════════════
# SECCIÓN META: HISTORIAL Y CATÁLOGO NC
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
with st.expander("📚 Historial de Conciliaciones"):
    if OFFLINE_MODE:
        historial = leer_historial(8)
        if historial:
            df_hist = pd.DataFrame(historial, columns=[
                'Fecha', 'Banco', 'Auxiliar', 'Período', 'Tasa%', 'Exactas', 'Mov.Banco', 'Diff Neta'
            ])
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("No hay historial disponible")
    else:
        st.info("Historial solo disponible en modo local (SQLite)")

with st.expander("🧠 Catálogo NC (Aprendizaje Automático)"):
    if OFFLINE_MODE:
        rows, total, pend = listar_catalogo_nc(10)
        st.write(f"Reglas aprobadas: {total} | Candidatos pendientes: {pend}")
        if rows:
            df_cat = pd.DataFrame(rows, columns=[
                'UUID', 'Tokens Banco', 'Tokens Aux', 'Confirmaciones', 'Nivel', 'Aprobado', 'Última vez'
            ])
            st.dataframe(df_cat, use_container_width=True)
        else:
            st.info("Catálogo vacío - se llena automáticamente al confirmar matches NC")
    else:
        st.info("Catálogo NC solo disponible en modo local (SQLite)")

# Footer
st.markdown("---")
st.caption("CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria v2.0 (Arquitectura Modular)")