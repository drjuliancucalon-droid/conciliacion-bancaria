"""
Configuración global — Constantes y parámetros compartidos
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import os
import re

# ══════════════════════════════════════════════════════════════════════════════
# RUTAS Y ENTORNO
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OFFLINE_MODE = not os.path.exists("/mount/src")  # True=local, False=Streamlit Cloud
DB_PATH = os.path.join(BASE_DIR, "conciliaciones.db")

# ══════════════════════════════════════════════════════════════════════════════
# TOLERANCIAS DE MATCHING
# ══════════════════════════════════════════════════════════════════════════════

TOL_EXACTA = 1.0      # Diferencia máxima en COP para match exacto
TOL_APROX = 0.005     # 0.5% de tolerancia relativa para match aproximado

# ══════════════════════════════════════════════════════════════════════════════
# STOPWORDS PARA APRENDIZAJE NC
# ══════════════════════════════════════════════════════════════════════════════

_STOP_NC = {
    'de','la','el','en','a','y','con','por','para','del','un','una','los','las',
    'al','se','su','que','no','es','pago','transferencia','nota','contable',
    'banco','bancario','cobro','cargo','por','desde','hasta','entre','sin',
    'mas','los','las','este','esta','fue','han','hay','bien','ser','tiene',
    'son','sus','les','nos','fue','era','ese','esa'
}

# ══════════════════════════════════════════════════════════════════════════════
# REGLAS DE CLASIFICACIÓN DÉBITO/CRÉDITO (orden importa: más específico primero)
# ══════════════════════════════════════════════════════════════════════════════

REGLAS_COL = [
    # ── DÉBITOS (entradas a la cuenta) ────────────────────────────────────────
    (re.compile(r'ABONO\s+A\s+PRESTAMO',             re.I), 'DEBITO'),
    (re.compile(r'RENDIMIENTO|INTERES\s+AHORROS',     re.I), 'DEBITO'),
    (re.compile(r'RECAUDO|INGRESO\s+CAJA|CONSIGNACI', re.I), 'DEBITO'),
    (re.compile(r'ABONO\s+CARTERA|ABONO\s+CUENTA',   re.I), 'DEBITO'),
    (re.compile(r'\bN\.D\.\b',                     re.I), 'DEBITO'),
    # ── CRÉDITOS (salidas / cargos bancarios) ─────────────────────────────────
    (re.compile(r'COMISION|COBRO\s+IVA|IVA\s+PAGOS', re.I), 'CREDITO'),
    (re.compile(r'4\s*POR\s*MIL|IMPTO\s+GOB|GRAVAMEN', re.I), 'CREDITO'),
    (re.compile(r'NOTA\s+CONTABLE|CARGO\s+BANC',     re.I), 'CREDITO'),
    (re.compile(r'NEQUI|PSE|DAVIPLATA|TRANSFIYA',      re.I), 'CREDITO'),
    (re.compile(r'\bPRESTAMO\b(?!.*ABONO)',           re.I), 'CREDITO'),
    (re.compile(r'RETIRO\s+PARA\s+PAGO',             re.I), 'CREDITO'),
    (re.compile(r'CANCELACION\s+NOMINA',              re.I), 'CREDITO'),
    (re.compile(r'GASTO\s+BANCAR|\bN\.C\.\b',     re.I), 'CREDITO'),
    (re.compile(r'IMPUESTO\s+MOVIMIENTO|GMF|4X1000',  re.I), 'CREDITO'),
    (re.compile(r'ND\s+POR\s+RECHAZO|RECHAZO\s+PAGO', re.I), 'CREDITO'),
    (re.compile(r'CUOTA\s+CREDITO|CUOTA\s+PRESTAMO', re.I), 'CREDITO'),
]

# ══════════════════════════════════════════════════════════════════════════════
# UMBRAL DE VALIDACIÓN ARITMÉTICA
# ══════════════════════════════════════════════════════════════════════════════

UMBRAL_DIF_NETA = 100  # COP — Umbral para alerta de diferencia neta en conciliación
