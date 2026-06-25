"""
Extracción de período bancario
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import logging
from datetime import datetime


def extraer_periodo_banco(texto):
    """
    Extrae el período del extracto bancario (mes/año).
    Busca patrones como 'PERIODO 01/2025', 'ENERO 2025', etc.
    """
    # Patrones comunes en extractos bancarios colombianos
    patrones = [
        r'PERIODO\s+(\d{1,2})[/\-](\d{4})',
        r'PERIODO\s+(\w+)\s+(\d{4})',
        r'EXTRACTO\s+(\w+)\s+(\d{4})',
        r'DEL\s+\d{1,2}\s+DE\s+(\w+)\s+DE\s+(\d{4})',
        r'(\d{1,2})[/\-](\d{4})\s+AL\s+\d{1,2}[/\-](\d{4})',
    ]
    
    meses = {
        'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
        'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
        'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
        'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12,
    }
    
    for pat in patrones:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            try:
                if m.lastindex >= 2:
                    mes_str = m.group(1)
                    anio = int(m.group(2))
                    if mes_str.isdigit():
                        mes = int(mes_str)
                    else:
                        mes = meses.get(mes_str.upper()[:3], 1)
                    if 1 <= mes <= 12 and 2020 <= anio <= 2030:
                        return f"{mes:02d}/{anio}"
            except (ValueError, IndexError):
                continue
    
    # Fallback: mes/año actual
    return datetime.now().strftime("%m/%Y")