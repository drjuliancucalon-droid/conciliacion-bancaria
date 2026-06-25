"""
Formateadores para UI y reportes
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import logging
import numpy as np


def cop(v):
    """Formatea un valor monetario con signo y separadores de miles."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '                 N/A'
    signo = '-' if v < 0 else ' '
    return f'{signo}$ {abs(v):>18,.2f}'


def pct_bar(p, width=20):
    """Genera una barra de progreso textual."""
    filled = int(p / 100 * width)
    return '[' + '█' * filled + '░' * (width - filled) + ']'


def semaforo_conciliacion(tasa, n_solo_banco, n_solo_aux):
    """
    Devuelve emoji semáforo según calidad de conciliación.
    🟢 Verde: tasa >= 90% y pocos pendientes
    🟡 Amarillo: tasa 70-90% o algunos pendientes
    🔴 Rojo: tasa < 70% o muchos pendientes
    """
    if tasa >= 90 and n_solo_banco <= 2 and n_solo_aux <= 2:
        return '🟢'
    elif tasa >= 70:
        return '🟡'
    else:
        return '🔴'