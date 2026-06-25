"""
Reglas de clasificación DÉBITO/CRÉDITO para asientos contables
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re
import logging
from config import REGLAS_COL


def determinar_columna(concepto, doc_code):
    """
    Determina si un asiento va a DÉBITO o CRÉDITO.
    Prioridad: 1) Concepto (REGLAS_COL)  2) Prefijo del documento
    Prefijos conocidos:
        CE- Comprobante Egreso     → CRÉDITO  (pago a proveedor)
        NC- Nota Contable          → CRÉDITO  (comisión/cargo bancario)
        CG- Comprobante Ingreso    → DÉBITO   (entrada de dinero)
        CON- Comprobante General   → DÉBITO   (por defecto)
        CO- igual que CON-         → DÉBITO
    """
    for pat, col in REGLAS_COL:
        if pat.search(concepto or ''):
            return col
    doc_prefix = (doc_code[:3].upper() if doc_code and len(doc_code) >= 3
                  else (doc_code or '')[:2].upper())
    # Prefijos de egreso / cargo
    if doc_prefix in ('CE-', 'NC-'):
        return 'CREDITO'
    if doc_prefix[:2] in ('CE', 'NC'):
        return 'CREDITO'
    # Prefijos de ingreso / abono
    if doc_prefix in ('CG-', 'CON'):
        return 'DEBITO'
    if doc_prefix[:2] in ('CG', 'CO'):
        return 'DEBITO'
    # Fallback conservador: la mayoría de asientos auxiliares son egresos
    return 'CREDITO'