"""
Parser de extractos bancarios PDF
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import logging
import pdfplumber
import pandas as pd
from datetime import datetime
from utils.pdf_diagnostico import ocr_pdf_page

# OCR (opcional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def limpiar_num(t):
    t = str(t or '').strip()
    if not t:
        return None
    neg = t.startswith('-') or (t.startswith('(') and t.endswith(')'))
    t = re.sub(r'[\$\(\)\s]', '', t).replace(',', '')
    try:
        v = float(t)
        return -abs(v) if neg else v
    except:
        return None


def es_fecha_banco(t):
    return bool(re.match(r'^\d{1,2}/\d{2}$', str(t or '').strip()))


def parsear_banco_pdf(ruta, usar_ocr=False):
    registros = []
    resumen = {}
    pat_res = {
        'SALDO_ANTERIOR': r'SALDO\s+ANTERIOR\s+\$?\s*([\d,\.]+)',
        'TOTAL_ABONOS'  : r'TOTAL\s+ABONOS\s+\$?\s*([\d,\.]+)',
        'TOTAL_CARGOS'  : r'TOTAL\s+CARGOS\s+\$?\s*([\d,\.]+)',
        'SALDO_ACTUAL'  : r'SALDO\s+ACTUAL\s+\$?\s*([\d,\.]+)',
    }

    anio_extracto = datetime.now().year

    with pdfplumber.open(ruta) as pdf:
        for n_pag, pag in enumerate(pdf.pages):
            texto = pag.extract_text() or ''
            if len(texto.strip()) <= 30 and usar_ocr and OCR_AVAILABLE:
                texto = ocr_pdf_page(ruta, pag.page_number)

            if n_pag == 0:
                _m_anio = re.search(r'\b(20\d{2})\b', texto)
                if _m_anio:
                    anio_extracto = int(_m_anio.group(1))
                for clave, pat in pat_res.items():
                    m = re.search(pat, texto, re.IGNORECASE)
                    if m and clave not in resumen:
                        v = m.group(1).replace(',', '')
                        resumen[clave] = limpiar_num(v)

            tabla = pag.extract_table({
                'vertical_strategy': 'lines',
                'horizontal_strategy': 'lines',
            })
            if not tabla:
                tabla = pag.extract_table()

            if tabla:
                for fila in tabla:
                    if not fila:
                        continue
                    celdas = [str(c or '').strip() for c in fila]
                    fecha_raw = next((c for c in celdas if es_fecha_banco(c)), None)
                    if not fecha_raw:
                        continue
                    nums = []
                    for c in reversed(celdas):
                        v = limpiar_num(c)
                        if v is not None:
                            nums.insert(0, v)
                        elif nums:
                            break
                    if len(nums) < 1:
                        continue
                    saldo = nums[-1]
                    valor = nums[-2] if len(nums) >= 2 else None
                    idx_f = celdas.index(fecha_raw)
                    n_num = len(nums)
                    desc = ' '.join(c for c in celdas[idx_f+1:len(celdas)-n_num]
                                     if c and not es_fecha_banco(c))
                    desc = re.sub(r'\s+', ' ', desc).strip()
                    registros.append({
                        'FECHA_RAW': fecha_raw,
                        'FECHA': pd.to_datetime(f'{anio_extracto}/' + fecha_raw,
                                        format='%Y/%d/%m', errors='coerce'),
                        'DESCRIPCION': desc,
                        'VALOR': valor,
                        'SALDO': saldo,
                        'TIPO': 'ABONO' if (valor or 0) >= 0 else 'CARGO',
                        'PAGINA': n_pag + 1,
                    })
            else:
                for linea in texto.split('\n'):
                    partes = linea.strip().split()
                    if not partes or not es_fecha_banco(partes[0]):
                        continue
                    fecha_raw = partes[0]
                    nums = []; desc_p = []
                    for p in partes[1:]:
                        v = limpiar_num(p)
                        if v is not None:
                            nums.append(v)
                        elif not nums:
                            desc_p.append(p)
                    if not nums:
                        continue
                    saldo = nums[-1]
                    valor = nums[-2] if len(nums) >= 2 else nums[0]
                    registros.append({
                        'FECHA_RAW': fecha_raw,
                        'FECHA': pd.to_datetime(f'{anio_extracto}/' + fecha_raw,
                                        format='%Y/%d/%m', errors='coerce'),
                        'DESCRIPCION': ' '.join(desc_p),
                        'VALOR': valor,
                        'SALDO': saldo,
                        'TIPO': 'ABONO' if (valor or 0) >= 0 else 'CARGO',
                        'PAGINA': n_pag + 1,
                    })

    df = pd.DataFrame(registros)
    if df.empty:
        return df, resumen
    df = df[df['VALOR'].notna()].copy()
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')
    df = df.drop_duplicates(subset=['FECHA_RAW', 'DESCRIPCION', 'VALOR', 'SALDO'])
    df = df.sort_values('FECHA', na_position='last').reset_index(drop=True)
    df.index += 1
    return df, resumen