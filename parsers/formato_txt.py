"""
Parser para auxiliares en formato TXT (plano)
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import pandas as pd
from parsers.banco_pdf import limpiar_num
from engine.columna import determinar_columna


def det_aux_txt(texto):
    """Detecta si el texto corresponde a formato auxiliar TXT."""
    # Buscar patrones típicos de documentos contables en TXT
    lineas = texto.split('\n')[:20]
    for linea in lineas:
        if re.match(r'^(CON|CE|CG|NC|RE|RG)-\d+', linea.strip()):
            return True
    return False


def par_aux_txt(ruta):
    """Parsea auxiliar desde archivo TXT."""
    with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
        texto = f.read()
    
    # Patrones iguales al parser PDF
    PAT_DOC    = re.compile(r'^((?:CON|CE|CG|NC|RE|RG)-\d+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.*)')
    PAT_MONTO  = re.compile(r'^([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)$')
    PAT_MPFX   = re.compile(r'^([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)\s+((?:CON|CE|CG|NC|RE|RG)-\d+.*)$')
    PAT_MSFX   = re.compile(r'\s([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)$')

    registros   = []
    lineas      = [l.strip() for l in texto.split('\n') if l.strip()]
    pending_doc = None

    def guardar(doc, fecha_str, concepto, monto_str):
        monto = limpiar_num(monto_str.replace(',', ''))
        if not monto or monto <= 0:
            return
        col = determinar_columna(concepto, doc)
        debito  = monto if col == 'DEBITO'  else None
        credito = monto if col == 'CREDITO' else None
        try:
            fdt = pd.to_datetime(fecha_str, format='%d/%m/%Y', errors='coerce')
        except:
            fdt = pd.NaT
        registros.append({
            'DOCUMENTO' : doc,
            'FECHA_RAW' : fecha_str,
            'FECHA'     : fdt,
            'CONCEPTO'  : concepto,
            'DEBITO'    : debito,
            'CREDITO'   : credito,
            'COLUMNA'   : col,
            'VALOR_NETO': (debito or 0) - (credito or 0),
        })

    for linea in lineas:
        m_pfx = PAT_MPFX.match(linea)
        if m_pfx:
            monto_ant = m_pfx.group(1)
            resto     = m_pfx.group(2)
            if pending_doc:
                guardar(pending_doc['doc'], pending_doc['date'],
                        pending_doc['concept'], monto_ant)
                pending_doc = None
            m_doc = PAT_DOC.match(resto)
            if m_doc:
                doc_c   = m_doc.group(1)
                fecha_s = m_doc.group(2)
                concepto_raw = m_doc.group(3)
                m_end = PAT_MSFX.search(concepto_raw)
                if m_end:
                    monto_end = m_end.group(1)
                    concepto_limpio = concepto_raw[:m_end.start()].strip()
                    guardar(doc_c, fecha_s, concepto_limpio, monto_end)
                else:
                    pending_doc = {'doc': doc_c, 'date': fecha_s, 'concept': concepto_raw}
            continue

        m_doc = PAT_DOC.match(linea)
        if m_doc:
            if pending_doc:
                pass
            doc_c   = m_doc.group(1)
            fecha_s = m_doc.group(2)
            concepto_raw = m_doc.group(3)
            m_end = PAT_MSFX.search(concepto_raw)
            if m_end:
                monto_end = m_end.group(1)
                concepto_limpio = concepto_raw[:m_end.start()].strip()
                guardar(doc_c, fecha_s, concepto_limpio, monto_end)
            else:
                pending_doc = {'doc': doc_c, 'date': fecha_s, 'concept': concepto_raw}
            continue

        m_num = PAT_MONTO.match(linea)
        if m_num and pending_doc:
            guardar(pending_doc['doc'], pending_doc['date'],
                    pending_doc['concept'], m_num.group(1))
            pending_doc = None
            continue

    if pending_doc:
        pass

    df = pd.DataFrame(registros)
    if df.empty:
        return df, {}
    df = df.drop_duplicates(subset=['DOCUMENTO', 'FECHA_RAW', 'CONCEPTO', 'VALOR_NETO'])
    df = df.sort_values('FECHA', na_position='last').reset_index(drop=True)
    df.index += 1
    return df, {}