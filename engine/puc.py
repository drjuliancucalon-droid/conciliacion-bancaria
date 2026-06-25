"""
Plan Único de Cuentas (PUC) Colombiano — Asignación automática
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import re

# ══════════════════════════════════════════════════════════════════════════════
# MAPEO DE CONCEPTOS BANCARIOS COMUNES → CÓDIGOS PUC
# ══════════════════════════════════════════════════════════════════════════════

PUC_MAPEO = [
    # ── BANCOS Y ENTIDADES FINANCIERAS ──
    (re.compile(r'CHEQUE\s+DE\s+GERENCIA|CHEQUE', re.I), '111005', 'Bancos — Moneda Nacional'),
    (re.compile(r'CONSIGNACION\s+NACIONAL|CONSIGNACION', re.I), '111005', 'Bancos — Moneda Nacional'),
    (re.compile(r'TRANSFERENCIA\s+ACH|TRANSFERENCIA\s+ELECT', re.I), '111005', 'Bancos — Moneda Nacional'),

    # ── GASTOS BANCARIOS ──
    (re.compile(r'COMISION\s+BANCARIA|COMISION\s+ADMIN|CUOTA\s+MANEJO', re.I), '530520', 'Gastos Bancarios — Comisiones'),
    (re.compile(r'4\s*X\s*1000|4\s*POR\s*MIL|GRAVAMEN\s+FINANCIERO|GMF', re.I), '530525', 'Gastos Bancarios — Gravamen Financiero'),
    (re.compile(r'IVA\s+COMISION|IVA\s+PAGOS', re.I), '530530', 'Gastos Bancarios — IVA'),
    (re.compile(r'IMPUESTO\s+MOVIMIENTO', re.I), '530525', 'Gastos Bancarios — Gravamen Financiero'),
    (re.compile(r'INTERES\s+SOBREGIRO|INTERES\s+CREDITO', re.I), '530505', 'Gastos Bancarios — Intereses'),

    # ── INGRESOS FINANCIEROS ──
    (re.compile(r'RENDIMIENTO\s+FINANCIERO|INTERES\s+AHORROS|RENDIMIENTOS', re.I), '421005', 'Ingresos Financieros — Intereses'),
    (re.compile(r'ABONO\s+A\s+PRESTAMO|DESEMBOLSO\s+PRESTAMO', re.I), '421005', 'Ingresos Financieros'),

    # ── PROVEEDORES ──
    (re.compile(r'PAGO\s+PROVEEDOR|PAGO\s+A\s+TERCEROS', re.I), '220505', 'Proveedores Nacionales'),
    (re.compile(r'PAGO\s+NOMINA|NOMINA', re.I), '250505', 'Obligaciones Laborales — Salarios'),

    # ── IMPUESTOS ──
    (re.compile(r'RETENCION\s+EN\s+LA\s+FUENTE|RETE\s*FUENTE|RETEFUENTE', re.I), '236505', 'Retención en la Fuente'),
    (re.compile(r'RETENCION\s+IVA|RETE\s*IVA', re.I), '236701', 'Retención de IVA'),
    (re.compile(r'RETENCION\s+ICA|RETE\s*ICA', re.I), '236801', 'Retención de ICA'),
    (re.compile(r'IMPUESTO\s+PREDIAL|PREDIAL', re.I), '511505', 'Impuestos — Predial'),
    (re.compile(r'IMPUESTO\s+RENTA|RETENCION\s+RENTA', re.I), '236505', 'Retención en la Fuente'),

    # ── SERVICIOS PÚBLICOS ──
    (re.compile(r'PAGO\s+SERVICIO\s+PUBLICO|ENERGIA|ENERGÍA|ACUEDUCTO|GAS\s+NATURAL', re.I), '513505', 'Servicios Públicos'),
    (re.compile(r'TELEFONIA|INTERNET|TELECOMUNICACIONES', re.I), '513505', 'Servicios Públicos — Telecomunicaciones'),

    # ── SEGUROS ──
    (re.compile(r'SEGURO\s+VIDA|SEGURO\s+POLIZA|POLIZA\s+SEGURO', re.I), '513005', 'Seguros'),

    # ── ARRENDAMIENTOS ──
    (re.compile(r'CANON\s+ARRENDAMIENTO|ARRENDAMIENTO|ARRIENDO', re.I), '512005', 'Arrendamientos'),

    # ── MANTENIMIENTO ──
    (re.compile(r'MANTENIMIENTO\s+EQUIPO|MANTENIMIENTO\s+VEHIC', re.I), '514505', 'Mantenimiento y Reparaciones'),

    # ── RECAUDO / CAJA ──
    (re.compile(r'RECAUDO|INGRESO\s+CAJA', re.I), '110505', 'Caja General'),

    # ── PRÉSTAMOS ──
    (re.compile(r'PAGO\s+CUOTA\s+PRESTAMO|CUOTA\s+CREDITO|ABONO\s+OBLIGACION', re.I), '210505', 'Obligaciones Financieras'),

    # ── NEQUI / PSE / DAVIPLATA ──
    (re.compile(r'NEQUI|PSE|DAVIPLATA|TRANSFIYA', re.I), '111005', 'Bancos — Moneda Nacional'),

    # ── HONORARIOS ──
    (re.compile(r'HONORARIOS|PAGO\s+ABOGADO|PAGO\s+CONTADOR', re.I), '511005', 'Honorarios'),

    # ── PAPELERÍA ──
    (re.compile(r'PAPELERIA|UTILES\s+OFICINA|SUMINISTROS', re.I), '519505', 'Útiles y Papelería'),
]

# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN DE ASIGNACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def asignar_puc(descripcion, tipo='CARGO'):
    """
    Asigna el código PUC más probable a una descripción de movimiento bancario.
    Retorna (codigo_puc, nombre_cuenta) o (None, None) si no se encuentra.
    """
    if not descripcion:
        return None, None
    for pat, codigo, nombre in PUC_MAPEO:
        if pat.search(descripcion):
            return codigo, nombre
    # Fallback según tipo
    if tipo == 'CARGO':
        return '530520', 'Gastos Bancarios — Comisiones (por defecto)'
    return '421005', 'Ingresos Financieros (por defecto)'


def asignar_puc_a_dataframe(df):
    """
    Añade columnas 'PUC' y 'CUENTA_PUC' a un DataFrame de movimientos.
    El DataFrame debe tener columnas 'DESCRIPCION' y 'TIPO'.
    """
    import pandas as pd
    df = df.copy()
    puc_codes = []
    puc_names = []
    for _, row in df.iterrows():
        cod, nom = asignar_puc(row.get('DESCRIPCION', ''), row.get('TIPO', 'CARGO'))
        puc_codes.append(cod or '')
        puc_names.append(nom or '')
    df['PUC'] = puc_codes
    df['CUENTA_PUC'] = puc_names
    return df


def resumen_por_puc(df):
    """
    Genera un resumen de movimientos agrupados por código PUC.
    Retorna DataFrame con columnas: PUC, Cuenta, Cantidad, Total.
    """
    import pandas as pd
    if df.empty or 'PUC' not in df.columns:
        return pd.DataFrame(columns=['PUC', 'Cuenta', 'Cantidad', 'Total'])
    df_puc = asignar_puc_a_dataframe(df)
    resumen = df_puc.groupby(['PUC', 'CUENTA_PUC']).agg(
        Cantidad=('VALOR', 'count'),
        Total=('VALOR', 'sum')
    ).reset_index()
    resumen = resumen.sort_values('Total', ascending=False)
    return resumen