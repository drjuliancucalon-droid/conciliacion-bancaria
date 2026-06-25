"""
Parsers para formatos CSV/Excel de auxiliares (SIIGO, Helisa, WorldOffice, genérico)
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import pandas as pd
import re
from parsers.banco_pdf import limpiar_num
from engine.columna import determinar_columna


# ═════════════════════════════════════════════════════════════════════════════════
# SIIGO
# ════════════════════════════════════════════════════════════════════════════════

def det_siigo_aux_csv(df):
    """Detecta si el DataFrame corresponde a formato SIIGO auxiliar."""
    cols = [str(c).strip().upper() for c in df.columns]
    return ('COMPROBANTE' in cols and 'CONCEPTO' in cols and
            'DEBITO' in cols and 'CREDITO' in cols)


def par_siigo_aux_csv(ruta):
    """Parsea auxiliar SIIGO desde CSV/Excel."""
    df = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    registros = []
    for _, row in df.iterrows():
        doc = str(row.get('COMPROBANTE', '')).strip()
        if not doc or doc.upper() == 'NAN':
            continue
        fecha = str(row.get('FECHA', '')).strip()
        concepto = str(row.get('CONCEPTO', '')).strip()
        debito = limpiar_num(row.get('DEBITO', 0))
        credito = limpiar_num(row.get('CREDITO', 0))
        
        if not debito and not credito:
            continue
        
        col = determinar_columna(concepto, doc)
        # Forzar según columnas SIIGO
        if debito and not credito:
            col = 'DEBITO'
        elif credito and not debito:
            col = 'CREDITO'
        
        try:
            fdt = pd.to_datetime(fecha, format='%d/%m/%Y', errors='coerce')
        except:
            fdt = pd.NaT
        
        registros.append({
            'DOCUMENTO': doc,
            'FECHA_RAW': fecha,
            'FECHA': fdt,
            'CONCEPTO': concepto,
            'DEBITO': debito if col == 'DEBITO' else None,
            'CREDITO': credito if col == 'CREDITO' else None,
            'COLUMNA': col,
            'VALOR_NETO': (debito or 0) - (credito or 0),
        })
    
    return pd.DataFrame(registros), {}


# ═══════════════════════════════════════════════════════════════════════════════
# HELISA
# ═══════════════════════════════════════════════════════════════════════════════

def det_helisa_aux_csv(df):
    """Detecta si el DataFrame corresponde a formato Helisa auxiliar."""
    cols = [str(c).strip().upper() for c in df.columns]
    return ('DOCUMENTO' in cols and 'FECHA' in cols and
            'DESCRIPCION' in cols and 'VALOR' in cols and 'NATURALEZA' in cols)


def par_helisa_aux_csv(ruta):
    """Parsea auxiliar Helisa desde CSV/Excel."""
    df = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    registros = []
    for _, row in df.iterrows():
        doc = str(row.get('DOCUMENTO', '')).strip()
        if not doc or doc.upper() == 'NAN':
            continue
        fecha = str(row.get('FECHA', '')).strip()
        concepto = str(row.get('DESCRIPCION', '')).strip()
        valor = limpiar_num(row.get('VALOR', 0))
        naturaleza = str(row.get('NATURALEZA', '')).strip().upper()
        
        if not valor or valor <= 0:
            continue
        
        col = 'DEBITO' if naturaleza in ('D', 'DEBITO', 'DÉBITO') else 'CREDITO'
        col = determinar_columna(concepto, doc)  # Refinar por concepto
        
        try:
            fdt = pd.to_datetime(fecha, format='%d/%m/%Y', errors='coerce')
        except:
            fdt = pd.NaT
        
        registros.append({
            'DOCUMENTO': doc,
            'FECHA_RAW': fecha,
            'FECHA': fdt,
            'CONCEPTO': concepto,
            'DEBITO': valor if col == 'DEBITO' else None,
            'CREDITO': valor if col == 'CREDITO' else None,
            'COLUMNA': col,
            'VALOR_NETO': valor if col == 'DEBITO' else -valor,
        })
    
    return pd.DataFrame(registros), {}


# ═══════════════════════════════════════════════════════════════════════════════
# WORLDOFFICE
# ═══════════════════════════════════════════════════════════════════════════════

def det_worldoffice_aux_csv(df):
    """Detecta si el DataFrame corresponde a formato WorldOffice auxiliar."""
    cols = [str(c).strip().upper() for c in df.columns]
    return ('NUMERO' in cols and 'FECHA' in cols and
            'TERCERO' in cols and 'VALOR' in cols and 'TIPO' in cols)


def par_worldoffice_aux_csv(ruta):
    """Parsea auxiliar WorldOffice desde CSV/Excel."""
    df = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    registros = []
    for _, row in df.iterrows():
        doc = str(row.get('NUMERO', '')).strip()
        if not doc or doc.upper() == 'NAN':
            continue
        fecha = str(row.get('FECHA', '')).strip()
        tercero = str(row.get('TERCERO', '')).strip()
        concepto = f"{tercero} - {str(row.get('CONCEPTO', '')).strip()}"
        valor = limpiar_num(row.get('VALOR', 0))
        tipo = str(row.get('TIPO', '')).strip().upper()
        
        if not valor or valor <= 0:
            continue
        
        col = 'DEBITO' if tipo in ('D', 'DEBITO', 'DÉBITO', 'INGRESO') else 'CREDITO'
        col = determinar_columna(concepto, doc)
        
        try:
            fdt = pd.to_datetime(fecha, format='%d/%m/%Y', errors='coerce')
        except:
            fdt = pd.NaT
        
        registros.append({
            'DOCUMENTO': doc,
            'FECHA_RAW': fecha,
            'FECHA': fdt,
            'CONCEPTO': concepto,
            'DEBITO': valor if col == 'DEBITO' else None,
            'CREDITO': valor if col == 'CREDITO' else None,
            'COLUMNA': col,
            'VALOR_NETO': valor if col == 'DEBITO' else -valor,
        })
    
    return pd.DataFrame(registros), {}


# ═══════════════════════════════════════════════════════════════════════════════
# GENÉRICO CSV/EXCEL
# ═══════════════════════════════════════════════════════════════════════════════

def det_aux_csv_generico(df):
    """Detecta formato auxiliar genérico (columnas mínimas requeridas)."""
    cols = [str(c).strip().upper() for c in df.columns]
    # Buscar columnas típicas
    has_doc = any(c in cols for c in ['DOCUMENTO', 'COMPROBANTE', 'NUMERO', 'NUM'])
    has_fecha = any(c in cols for c in ['FECHA', 'DATE'])
    has_concepto = any(c in cols for c in ['CONCEPTO', 'DESCRIPCION', 'DETALLE', 'CONCEPT'])
    has_valor = any(c in cols for c in ['VALOR', 'MONTO', 'IMPORTE', 'DEBITO', 'CREDITO'])
    return has_doc and has_fecha and has_concepto and has_valor


def par_aux_csv_generico(ruta):
    """Parsea auxiliar genérico desde CSV/Excel."""
    df = pd.read_excel(ruta) if ruta.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(ruta)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Mapear columnas
    col_doc = next((c for c in df.columns if c in ['DOCUMENTO', 'COMPROBANTE', 'NUMERO', 'NUM']), None)
    col_fecha = next((c for c in df.columns if c in ['FECHA', 'DATE']), None)
    col_concepto = next((c for c in df.columns if c in ['CONCEPTO', 'DESCRIPCION', 'DETALLE', 'CONCEPT']), None)
    col_debito = next((c for c in df.columns if c in ['DEBITO', 'DÉBITO', 'DEBE']), None)
    col_credito = next((c for c in df.columns if c in ['CREDITO', 'CRÉDITO', 'HABER']), None)
    col_valor = next((c for c in df.columns if c in ['VALOR', 'MONTO', 'IMPORTE']), None)
    col_naturaleza = next((c for c in df.columns if c in ['NATURALEZA', 'TIPO', 'SIGNO']), None)
    
    if not col_doc or not col_fecha or not col_concepto:
        return pd.DataFrame(), {}
    
    registros = []
    for _, row in df.iterrows():
        doc = str(row.get(col_doc, '')).strip()
        if not doc or doc.upper() == 'NAN':
            continue
        fecha = str(row.get(col_fecha, '')).strip()
        concepto = str(row.get(col_concepto, '')).strip()
        
        debito = limpiar_num(row.get(col_debito, 0)) if col_debito else None
        credito = limpiar_num(row.get(col_credito, 0)) if col_credito else None
        valor = limpiar_num(row.get(col_valor, 0)) if col_valor else None
        naturaleza = str(row.get(col_naturaleza, '')).strip().upper() if col_naturaleza else ''
        
        if debito is not None and credito is not None:
            # Formato con columnas DEBITO/CREDITO separadas
            col = 'DEBITO' if (debito or 0) > 0 else 'CREDITO'
            val_neto = (debito or 0) - (credito or 0)
        elif valor is not None:
            # Formato con columna VALOR única + NATURALEZA
            if not valor or valor <= 0:
                continue
            if naturaleza in ('D', 'DEBITO', 'DÉBITO', 'DEBE', 'INGRESO'):
                col = 'DEBITO'
            elif naturaleza in ('C', 'CREDITO', 'CRÉDITO', 'HABER', 'EGRESO'):
                col = 'CREDITO'
            else:
                col = determinar_columna(concepto, doc)
            val_neto = valor if col == 'DEBITO' else -valor
            debito = valor if col == 'DEBITO' else None
            credito = valor if col == 'CREDITO' else None
        else:
            continue
        
        col = determinar_columna(concepto, doc)
        
        try:
            fdt = pd.to_datetime(fecha, format='%d/%m/%Y', errors='coerce')
        except:
            fdt = pd.NaT
        
        registros.append({
            'DOCUMENTO': doc,
            'FECHA_RAW': fecha,
            'FECHA': fdt,
            'CONCEPTO': concepto,
            'DEBITO': debito,
            'CREDITO': credito,
            'COLUMNA': col,
            'VALOR_NETO': val_neto,
        })
    
    return pd.DataFrame(registros), {}