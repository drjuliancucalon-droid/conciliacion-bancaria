"""
Detección proactiva de comisiones bancarias y alertas
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""
import re

# Patrones de comisiones con límites
UMBRALES_COMISIONES = [
    ('GMF 4x1000', re.compile(r'4\s*X\s*1000|4\s*POR\s*MIL|GRAVAMEN\s+FINANCIERO|GMF', re.I), 0.004, 50000),
    ('Cuota manejo', re.compile(r'CUOTA\s+MANEJO|CUOTA\s+ADMIN', re.I), None, 100000),
    ('Comisión transferencia', re.compile(r'COMISION\s+TRANSFERENCIA|COMISION\s+ACH', re.I), None, 50000),
    ('IVA comisiones', re.compile(r'IVA\s+COMISION|IVA\s+PAGOS', re.I), 0.19, 200000),
    ('Comisión NEQUI/PSE', re.compile(r'COMISION\s+(NEQUI|PSE|DAVIPLATA)', re.I), None, 15000),
    ('Intereses sobregiro', re.compile(r'INTERES\s+SOBREGIRO|INTERES\s+CREDITO\s+ROT', re.I), None, 200000),
    ('Seguro débito', re.compile(r'SEGURO\s+DEBITO|SEGURO\s+TARJETA', re.I), None, 50000),
]

def detectar_comisiones(df_banco):
    """
    Analiza movimientos bancarios y genera alertas de comisiones.
    Retorna lista de alertas: [{'tipo': str, 'desc': str, 'valor': float, 'alerta': str}, ...]
    """
    if df_banco.empty:
        return []

    alertas = []
    for nombre, patron, tasa_esperada, limite in UMBRALES_COMISIONES:
        coincidencias = df_banco[
            df_banco['DESCRIPCION'].astype(str).str.contains(patron, na=False) &
            (df_banco['VALOR'] < 0)
        ]
        total = abs(coincidencias['VALOR'].sum())
        n = len(coincidencias)

        if n > 0:
            nivel = 'info'
            mensaje = ''
            if limite and total > limite:
                nivel = 'warning'
                mensaje = f'Supera límite de ${limite:,.0f}'
            if tasa_esperada and n >= 3:
                nivel = 'danger'
                mensaje = f'Alta frecuencia ({n} ocurrencias)'

            alertas.append({
                'tipo': nombre,
                'ocurrencias': n,
                'total': total,
                'descripcion': f'{nombre}: {n} ocurrencias por ${total:,.2f}',
                'nivel': nivel,
                'mensaje': mensaje
            })

    return sorted(alertas, key=lambda x: abs(x['total']), reverse=True)

def generar_reporte_comisiones(df_banco):
    """Genera HTML con el reporte de comisiones detectadas."""
    alertas = detectar_comisiones(df_banco)
    if not alertas:
        return '<p style="color:var(--success);">✅ No se detectaron comisiones atípicas este período.</p>'

    iconos = {'info': 'ℹ️', 'warning': '⚠️', 'danger': '🔴'}
    html = '<div style="font-size:0.85rem;">'
    for a in alertas:
        color = {'info': '#17A2B8', 'warning': '#FFC107', 'danger': '#DC3545'}[a['nivel']]
        html += f'''
        <div style="border-left:3px solid {color}; padding:0.5rem; margin:0.5rem 0; background:var(--card-bg);">
            <strong>{iconos[a['nivel']]} {a['tipo']}</strong>
            <span style="float:right; color:{color};">${a['total']:,.2f}</span>
            <br><small>{a['ocurrencias']} ocurrencia(s) {a['mensaje']}</small>
        </div>'''
    html += '</div>'
    return html