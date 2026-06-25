"""
Parser de auxiliares contables PDF
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import logging
import pdfplumber
import pandas as pd
from utils.pdf_diagnostico import ocr_pdf_page

# OCR (opcional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
from parsers.banco_pdf import limpiar_num
from engine.columna import determinar_columna


def parsear_auxiliar_pdf(ruta, usar_ocr=False):
    texto_completo = ''
    n_pags_ok = 0
    n_pags_mal = 0
    meta = {}

    with pdfplumber.open(ruta) as pdf:
        for pag in pdf.pages:
            t = pag.extract_text() or ''
            if len(t.strip()) <= 30 and usar_ocr and OCR_AVAILABLE:
                t = ocr_pdf_page(ruta, pag.page_number)
            if len(t.strip()) > 30:
                n_pags_ok += 1
                texto_completo += '\n' + t
            else:
                n_pags_mal += 1

    m_si = re.search(r'Saldo\s+Inicial[:\s]+([\d,\.]+)', texto_completo, re.I)
    m_sf = re.search(r'Saldo\s+Final[:\s]+([\d,\.]+)', texto_completo, re.I)
    m_td = re.search(r'Subtotales.*?([\d]{1,3}(?:[,\\.][\d]{3})+(?:\.[\d]+)?)'
                     r'\s+([\d]{1,3}(?:[,\\.][\d]{3})+(?:\.[\d]+)?)',
                     texto_completo, re.I | re.DOTALL)
    meta['SALDO_INICIAL']  = limpiar_num((m_si.group(1) if m_si else '0').replace(',', ''))
    meta['SALDO_FINAL']    = limpiar_num((m_sf.group(1) if m_sf else '0').replace(',', ''))
    if m_td:
        meta['TOTAL_DEBITOS']  = limpiar_num(m_td.group(1).replace(',', ''))
        meta['TOTAL_CREDITOS'] = limpiar_num(m_td.group(2).replace(',', ''))
    else:
        meta['TOTAL_DEBITOS'] = meta['TOTAL_CREDITOS'] = 0
    meta['N_PAGS_OK']  = n_pags_ok
    meta['N_PAGS_MAL'] = n_pags_mal

    # ── Parseo línea a línea ─────────────────────────
    PAT_DOC    = re.compile(r'^((?:CON|CE|CG|NC|RE|RG)-\d+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.*)')
    PAT_MONTO  = re.compile(r'^([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)$')
    PAT_MPFX   = re.compile(r'^([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)\s+((?:CON|CE|CG|NC|RE|RG)-\d+.*)$')
    PAT_MSFX   = re.compile(r'\s([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)$')

    registros   = []
    lineas      = [l.strip() for l in texto_completo.split('\n') if l.strip()]
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
        return df, meta
    df = df.drop_duplicates(subset=['DOCUMENTO', 'FECHA_RAW', 'CONCEPTO', 'VALOR_NETO'])
    df = df.sort_values('FECHA', na_position='last').reset_index(drop=True)
    df.index += 1
    return df, meta


def parsear_auxiliar_generico(ruta, usar_ocr=False):
    """Alias para compatibilidad."""
    return parsear_auxiliar_pdf(ruta, usar_ocr)