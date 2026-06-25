"""
Diagnóstico de legibilidad de PDF y OCR
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import os
import logging
import pdfplumber

# ══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN AUTOMÁTICA DE TESSERACT EN WINDOWS
# ══════════════════════════════════════════════════════════════════════════════

OCR_AVAILABLE = False
try:
    from pdf2image import convert_from_path
    import pytesseract

    # Auto-detectar Tesseract en rutas comunes de Windows
    TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(
            os.environ.get("USERNAME", "")
        ),
    ]
    tesseract_found = False
    for tp in TESSERACT_PATHS:
        if os.path.exists(tp):
            pytesseract.pytesseract.tesseract_cmd = tp
            OCR_AVAILABLE = True
            tesseract_found = True
            break

    # Intentar con PATH del sistema
    if not tesseract_found:
        import shutil
        sys_tesseract = shutil.which("tesseract")
        if sys_tesseract:
            pytesseract.pytesseract.tesseract_cmd = sys_tesseract
            OCR_AVAILABLE = True

    # Verificar que Tesseract realmente funcione
    if OCR_AVAILABLE:
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            OCR_AVAILABLE = False
            logging.warning(
                "Tesseract-OCR encontrado pero no funciona. "
                "Descárguelo de https://github.com/UB-Mannheim/tesseract/wiki"
            )
except ImportError:
    pass

# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES OCR
# ══════════════════════════════════════════════════════════════════════════════

def ocr_pdf_page(pdf_path, page_number):
    """Devuelve el texto de una página específica usando OCR."""
    if not OCR_AVAILABLE:
        return ""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(
            pdf_path,
            first_page=page_number,
            last_page=page_number,
            poppler_path=None  # Usa PATH del sistema o detecta automático
        )
        if images:
            return pytesseract.image_to_string(images[0], lang='spa')
    except Exception as e:
        logging.warning(f"Error OCR en página {page_number}: {e}")
    return ""


def _get_poppler_path():
    """Detecta poppler en rutas comunes de Windows."""
    import shutil
    poppler_bin = shutil.which("pdftoppm")
    if poppler_bin:
        return os.path.dirname(poppler_bin)
    # Rutas comunes de poppler para Windows
    for p in [
        r"C:\poppler\Library\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\poppler-24.08.0\Library\bin",
    ]:
        if os.path.exists(p):
            return p
    return None


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO DE PDF
# ══════════════════════════════════════════════════════════════════════════════

def diagnosticar_pdf(ruta, tipo):
    resultado = {
        'archivo': ruta, 'tipo': tipo,
        'paginas_total': 0, 'paginas_con_texto': 0, 'paginas_sin_texto': 0,
        'total_chars': 0, 'total_words': 0, 'lineas_doc_encontradas': 0,
        'pct_paginas_legibles': 0.0, 'pct_estimado_datos': 0.0,
        'calidad': '', 'advertencias': [], 'ocr_usado': False
    }

    pat_doc = re.compile(r'(?:CON|CE|CG|NC|RE|RG)-\d+')
    pat_mov_banco = re.compile(r'^\d{1,2}/\d{2}\s+', re.MULTILINE)

    try:
        with pdfplumber.open(ruta) as pdf:
            resultado['paginas_total'] = len(pdf.pages)
            for pag in pdf.pages:
                texto = pag.extract_text() or ''
                if len(texto.strip()) > 30:
                    resultado['paginas_con_texto'] += 1
                    resultado['total_chars'] += len(texto)
                    resultado['total_words'] += len(texto.split())
                    if tipo == 'AUXILIAR':
                        resultado['lineas_doc_encontradas'] += len(pat_doc.findall(texto))
                    else:
                        resultado['lineas_doc_encontradas'] += len(pat_mov_banco.findall(texto))
                else:
                    # Intentar OCR
                    if OCR_AVAILABLE:
                        ocr_text = ocr_pdf_page(ruta, pag.page_number)
                        if len(ocr_text.strip()) > 30:
                            resultado['paginas_con_texto'] += 1
                            resultado['total_chars'] += len(ocr_text)
                            resultado['total_words'] += len(ocr_text.split())
                            resultado['advertencias'].append(
                                f'Pág. {pag.page_number}: texto extraído con OCR')
                            resultado['ocr_usado'] = True
                            if tipo == 'AUXILIAR':
                                resultado['lineas_doc_encontradas'] += len(pat_doc.findall(ocr_text))
                            else:
                                resultado['lineas_doc_encontradas'] += len(pat_mov_banco.findall(ocr_text))
                        else:
                            resultado['paginas_sin_texto'] += 1
                            resultado['advertencias'].append(
                                f'Pág. {pag.page_number}: sin texto (imagen sin OCR disponible o ilegible)')
                    else:
                        resultado['paginas_sin_texto'] += 1
                        resultado['advertencias'].append(
                            f'Pág. {pag.page_number}: sin texto (imagen escaneada y OCR no instalado)')
    except Exception as e:
        resultado['advertencias'].append(f'Error al abrir: {e}')
        return resultado

    n_tot = resultado['paginas_total']
    n_ok = resultado['paginas_con_texto']
    resultado['pct_paginas_legibles'] = (n_ok / n_tot * 100) if n_tot > 0 else 0

    if resultado['lineas_doc_encontradas'] > 0:
        pct_datos = min(100, resultado['pct_paginas_legibles'] * 0.98 +
                        min(2, resultado['lineas_doc_encontradas'] / 10))
    else:
        pct_datos = resultado['pct_paginas_legibles'] * 0.5

    resultado['pct_estimado_datos'] = round(pct_datos, 1)
    if pct_datos >= 95:
        resultado['calidad'] = '🟢 EXCELENTE'
    elif pct_datos >= 80:
        resultado['calidad'] = '🟡 BUENA'
    elif pct_datos >= 50:
        resultado['calidad'] = '🟠 PARCIAL'
    else:
        resultado['calidad'] = '🔴 BAJA'
    return resultado