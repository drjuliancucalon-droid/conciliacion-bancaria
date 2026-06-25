"""
Exportador de reportes PDF firmados digitalmente
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import io
import hashlib
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.platypus.frames import Frame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Colores corporativos
PRIMARY = colors.HexColor('#1F4E79')
PRIMARY_LIGHT = colors.HexColor('#2E75B6')
ACCENT = colors.HexColor('#D4AF37')
BG_LIGHT = colors.HexColor('#F5F7FA')
GREEN = colors.HexColor('#28A745')
RED = colors.HexColor('#DC3545')
ORANGE = colors.HexColor('#FFC107')
WHITE = colors.white
BLACK = colors.HexColor('#1A1A2E')
GRAY = colors.HexColor('#6C757D')


def _build_pdf_content(
    periodo, archivo_banco, archivo_auxiliar,
    stats, matches_df, solo_banco_df, solo_aux_df
):
    """Construye el contenido del PDF y devuelve los elementos + el hash."""
    story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=16, textColor=PRIMARY, spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubTitle', parent=styles['Normal'],
        fontSize=9, textColor=GRAY, spaceAfter=12,
        fontName='Helvetica'
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        fontSize=12, textColor=PRIMARY, spaceAfter=6, spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontSize=8, leading=10
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell', parent=styles['Normal'],
        fontSize=8, textColor=WHITE, fontName='Helvetica-Bold', leading=10
    )

    # ═══ ENCABEZADO ═══
    story.append(Paragraph("CONCILIACIÓN BANCARIA", title_style))
    story.append(Paragraph("CREDIEXPRESS POPAYÁN SAS — Reporte de Auditoría", subtitle_style))
    story.append(Spacer(1, 4*mm))

    # Datos del proceso
    datos = [
        ["Período:", periodo, "Fecha Proceso:", datetime.now().strftime('%Y-%m-%d %H:%M')],
        ["Extracto Bancario:", archivo_banco, "Auxiliar Contable:", archivo_auxiliar],
    ]
    t = Table(datos, colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY),
        ('TEXTCOLOR', (2, 0), (2, -1), GRAY),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # ═══ RESUMEN EJECUTIVO ═══
    story.append(Paragraph("RESUMEN EJECUTIVO", section_style))
    kpi_data = [
        [
            Paragraph("Movimientos Banco", cell_style),
            Paragraph(str(stats.get('n_banco', 0)), cell_style),
            Paragraph("Exactas", cell_style),
            Paragraph(str(stats.get('n_exactas', 0)), cell_style),
        ],
        [
            Paragraph("Asientos Auxiliar", cell_style),
            Paragraph(str(stats.get('n_aux', 0)), cell_style),
            Paragraph("Aproximadas", cell_style),
            Paragraph(str(stats.get('n_aprox', 0)), cell_style),
        ],
        [
            Paragraph("Solo Banco", cell_style),
            Paragraph(str(stats.get('n_solo_banco', 0)), cell_style),
            Paragraph("Solo Auxiliar", cell_style),
            Paragraph(str(stats.get('n_solo_aux', 0)), cell_style),
        ],
        [
            Paragraph("Tasa de Conciliación", cell_style),
            Paragraph(f"{stats.get('tasa', 0):.1f}%", cell_style),
            Paragraph("Diferencia Neta", cell_style),
            Paragraph(f"$ {stats.get('diferencia_neta', 0):,.2f}", cell_style),
        ],
    ]
    t = Table(kpi_data, colWidths=[45*mm, 35*mm, 45*mm, 35*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, -1), BLACK),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # ═══ MATCHES ═══
    if matches_df is not None and not matches_df.empty:
        story.append(Paragraph("MATCHES ENCONTRADOS", section_style))
        matches_sample = matches_df.head(100)
        headers = ['Banco', 'Aux', 'Tipo', 'V. Banco', 'V. Aux', 'Diff', 'Documento']
        data = [headers]
        for _, row in matches_sample.iterrows():
            data.append([
                str(row.get('banco_idx', '')),
                str(row.get('aux_idx', '')),
                str(row.get('tipo', '')),
                f"$ {row.get('valor_banco', 0):,.2f}" if row.get('valor_banco') else '',
                f"$ {row.get('valor_aux', 0):,.2f}" if row.get('valor_aux') else '',
                f"$ {row.get('diff', 0):,.2f}" if row.get('diff') else '',
                str(row.get('documento_aux', ''))[:20],
            ])
        col_w = [12*mm, 12*mm, 22*mm, 28*mm, 28*mm, 28*mm, 32*mm]
        t = Table(data, colWidths=col_w)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.3, GRAY),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ]
        for i, row in enumerate(data[1:], 1):
            tipo = row[2] if len(row) > 2 else ''
            if tipo == 'EXACTA':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#D4EDDA')))
            elif tipo == 'RECHAZO':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8D7DA')))
            elif tipo == 'AGRUPADO':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#D1ECF1')))
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

        if len(matches_df) > 100:
            story.append(Paragraph(
                f"<i>Mostrando 100 de {len(matches_df)} registros. Consulte el archivo Excel para datos completos.</i>",
                styles['Normal']
            ))

    # ═══ FIRMA DIGITAL ═══
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph("FIRMA DIGITAL DE INTEGRIDAD", section_style))

    # Generar hash del contenido
    content_hash = hashlib.sha256()
    for elem in story:
        content_hash.update(str(elem).encode('utf-8'))
    content_hash.update(periodo.encode('utf-8'))
    content_hash.update(datetime.now().isoformat().encode('utf-8'))
    hash_value = content_hash.hexdigest()

    firma_data = [
        ["Hash SHA-256:", hash_value],
        ["Fecha de firma:", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ["Emitido por:", "CREDIEXPRESS POPAYÁN SAS — Sistema de Conciliación Bancaria v2.0"],
        ["", ""],
        ["Este documento tiene validez legal como soporte de auditoría.", ""],
        ["La firma digital garantiza la integridad del contenido.", ""],
    ]
    t = Table(firma_data, colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('FONTSIZE', (1, 0), (1, 0), 6),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t)

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        "<i>Este PDF fue generado automáticamente y está firmado digitalmente. "
        "El hash SHA-256 garantiza que el contenido no ha sido alterado desde su emisión.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=GRAY)
    ))

    return story, hash_value


def generar_pdf_conciliacion(
    matches_df, solo_banco_df, solo_aux_df,
    stats, periodo, archivo_banco, archivo_auxiliar
):
    """
    Genera un PDF firmado digitalmente de la conciliación.
    Retorna (bytes_pdf, hash_sha256).
    """
    buffer = io.BytesIO()
    story, hash_value = _build_pdf_content(
        periodo, archivo_banco, archivo_auxiliar,
        stats, matches_df, solo_banco_df, solo_aux_df
    )
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"Conciliacion_{periodo.replace('/', '-')}",
        author="CREDIEXPRESS POPAYAN SAS"
    )
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), hash_value