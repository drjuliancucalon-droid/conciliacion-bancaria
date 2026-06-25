"""
Despachador de parsers - Registro de formatos y detección automática
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import os
import pandas as pd
from parsers.banco_pdf import parsear_banco_pdf
from parsers.auxiliar_pdf import parsear_auxiliar_pdf
from parsers.formatos_csv import (
    det_siigo_aux_csv, par_siigo_aux_csv,
    det_helisa_aux_csv, par_helisa_aux_csv,
    det_worldoffice_aux_csv, par_worldoffice_aux_csv,
    det_aux_csv_generico, par_aux_csv_generico,
)
from parsers.formato_txt import det_aux_txt, par_aux_txt


# ═════════════════════════════════════════════════════════════════════════════════
# REGISTRO DE FORMATOS BANCO
# ═════════════════════════════════════════════════════════════════════════════════

FORMATOS_BANCO = [
    {
        'nombre': 'Banco PDF (extracto estándar)',
        'extensiones': ['.pdf'],
        'detector': lambda ruta: ruta.lower().endswith('.pdf'),
        'parser': parsear_banco_pdf,
        'args': ['usar_ocr'],
    },
]

# ═════════════════════════════════════════════════════════════════════════════════
# REGISTRO DE FORMATOS AUXILIAR
# ═════════════════════════════════════════════════════════════════════════════════

FORMATOS_AUXILIAR = [
    # PDF
    {
        'nombre': 'Auxiliar PDF (SIIGO/Helisa/WorldOffice/Genérico)',
        'extensiones': ['.pdf'],
        'detector': lambda ruta: ruta.lower().endswith('.pdf'),
        'parser': parsear_auxiliar_pdf,
        'args': ['usar_ocr'],
    },
    # SIIGO CSV/Excel
    {
        'nombre': 'SIIGO Auxiliar (CSV/Excel)',
        'extensiones': ['.csv', '.xlsx', '.xls'],
        'detector': lambda ruta, df=None: (
            ruta.lower().endswith(('.csv', '.xlsx', '.xls')) and
            (df is not None and det_siigo_aux_csv(df))
        ),
        'parser': par_siigo_aux_csv,
        'args': [],
    },
    # Helisa CSV/Excel
    {
        'nombre': 'Helisa Auxiliar (CSV/Excel)',
        'extensiones': ['.csv', '.xlsx', '.xls'],
        'detector': lambda ruta, df=None: (
            ruta.lower().endswith(('.csv', '.xlsx', '.xls')) and
            (df is not None and det_helisa_aux_csv(df))
        ),
        'parser': par_helisa_aux_csv,
        'args': [],
    },
    # WorldOffice CSV/Excel
    {
        'nombre': 'WorldOffice Auxiliar (CSV/Excel)',
        'extensiones': ['.csv', '.xlsx', '.xls'],
        'detector': lambda ruta, df=None: (
            ruta.lower().endswith(('.csv', '.xlsx', '.xls')) and
            (df is not None and det_worldoffice_aux_csv(df))
        ),
        'parser': par_worldoffice_aux_csv,
        'args': [],
    },
    # Genérico CSV/Excel
    {
        'nombre': 'Auxiliar Genérico (CSV/Excel)',
        'extensiones': ['.csv', '.xlsx', '.xls'],
        'detector': lambda ruta, df=None: (
            ruta.lower().endswith(('.csv', '.xlsx', '.xls')) and
            (df is not None and det_aux_csv_generico(df))
        ),
        'parser': par_aux_csv_generico,
        'args': [],
    },
    # TXT
    {
        'nombre': 'Auxiliar TXT (plano)',
        'extensiones': ['.txt'],
        'detector': lambda ruta: (
            ruta.lower().endswith('.txt') and
            det_aux_txt(open(ruta, 'r', encoding='utf-8', errors='ignore').read(2000))
        ),
        'parser': par_aux_txt,
        'args': [],
    },
]

# Combinar todos los formatos
REGISTRO_FORMATOS = {
    'BANCO': FORMATOS_BANCO,
    'AUXILIAR': FORMATOS_AUXILIAR,
}


def muestra_texto(ruta, max_chars=500):
    """Devuelve una muestra del texto del archivo para diagnóstico."""
    try:
        if ruta.lower().endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                texto = ''
                for pag in pdf.pages[:2]:
                    t = pag.extract_text() or ''
                    texto += t
                return texto[:max_chars]
        elif ruta.lower().endswith(('.csv', '.xlsx', '.xls')):
            df = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
            return df.head(3).to_string()
        elif ruta.lower().endswith('.txt'):
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(max_chars)
    except Exception:
        pass
    return ''


def despachar_ruta(ruta, tipo, usar_ocr=False):
    """
    Despacha el archivo al parser correspondiente según tipo y formato.
    Retorna (DataFrame, meta_dict, formato_usado).
    """
    formatos = REGISTRO_FORMATOS.get(tipo.upper(), [])
    
    # Para CSV/Excel, leer una vez para detectar
    df_muestra = None
    if ruta.lower().endswith(('.csv', '.xlsx', '.xls')):
        try:
            df_muestra = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
        except Exception:
            pass
    
    for fmt in formatos:
        try:
            detector = fmt['detector']
            # Llamar detector con o sin df_muestra según su firma
            import inspect
            sig = inspect.signature(detector)
            if 'df' in sig.parameters:
                if detector(ruta, df=df_muestra):
                    parser = fmt['parser']
                    args = {}
                    if 'usar_ocr' in fmt['args']:
                        args['usar_ocr'] = usar_ocr
                    df, meta = parser(ruta, **args)
                    return df, meta, fmt['nombre']
            else:
                if detector(ruta):
                    parser = fmt['parser']
                    args = {}
                    if 'usar_ocr' in fmt['args']:
                        args['usar_ocr'] = usar_ocr
                    df, meta = parser(ruta, **args)
                    return df, meta, fmt['nombre']
        except Exception as e:
            import logging
            logging.warning(f"Error en detector {fmt['nombre']}: {e}")
            continue
    
    # Fallback: intentar parser genérico según extensión
    if tipo.upper() == 'BANCO' and ruta.lower().endswith('.pdf'):
        df, meta = parsear_banco_pdf(ruta, usar_ocr=usar_ocr)
        return df, meta, 'Banco PDF (fallback)'
    
    if tipo.upper() == 'AUXILIAR':
        if ruta.lower().endswith('.pdf'):
            df, meta = parsear_auxiliar_pdf(ruta, usar_ocr=usar_ocr)
            return df, meta, 'Auxiliar PDF (fallback)'
        elif ruta.lower().endswith(('.csv', '.xlsx', '.xls')):
            df, meta = par_aux_csv_generico(ruta)
            return df, meta, 'Auxiliar Genérico (fallback)'
        elif ruta.lower().endswith('.txt'):
            df, meta = par_aux_txt(ruta)
            return df, meta, 'Auxiliar TXT (fallback)'
    
    return pd.DataFrame(), {}, 'DESCONOCIDO'


def cargar_y_parsear_uploaded_file(uploaded_file, tipo, usar_ocr=False):
    """
    Guarda archivo subido temporalmente y lo parsea.
    Retorna (DataFrame, meta_dict, formato_usado, ruta_temp).
    """
    import tempfile
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    try:
        df, meta, fmt = despachar_ruta(tmp_path, tipo, usar_ocr)
        return df, meta, fmt, tmp_path
    except Exception as e:
        import logging
        logging.error(f"Error parseando {uploaded_file.name}: {e}")
        os.unlink(tmp_path)
        return pd.DataFrame(), {}, 'ERROR', None