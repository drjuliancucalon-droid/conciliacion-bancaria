"""
Punto de almacenamiento (SQLite offline / Google Sheets cloud)
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

from config import OFFLINE_MODE

if OFFLINE_MODE:
    from storage.db import (
        _guardar_historial_sqlite as _guardar_historial_impl,
        leer_historial_sqlite as leer_historial_impl,
        registrar_formato_pdf,
        buscar_formato_pdf,
        listar_formatos_aprendidos,
        _auto_guardar_archivo,
        _auto_guardar_excel,
        _init_db,
    )
    from engine.nc_learning import _aprender_match_nc as _aprender_match_nc_impl
else:
    from storage.sheets import (
        _guardar_historial_sheets as _guardar_historial_impl,
    )
    def leer_historial_impl(limite=8):
        return []
    from storage.db import (
        registrar_formato_pdf,
        buscar_formato_pdf,
        listar_formatos_aprendidos,
        _auto_guardar_archivo,
        _auto_guardar_excel,
        _init_db,
    )
    from storage.sheets import (
        _aprender_match_nc_cloud as _aprender_match_nc_impl,
        sincronizar_catalogo_nc,
    )


def guardar_historial(d):
    _guardar_historial_impl(d)


def leer_historial(limite=8):
    return leer_historial_impl(limite)


def registrar_aprendizaje_nc(banco_desc, aux_doc, aux_concepto, metodo,
                             valor_banco=None, valor_aux=None):
    _aprender_match_nc_impl(banco_desc, aux_doc, aux_concepto, metodo,
                            valor_banco, valor_aux)


__all__ = [
    'guardar_historial',
    'leer_historial',
    'registrar_aprendizaje_nc',
    'registrar_formato_pdf',
    'buscar_formato_pdf',
    'listar_formatos_aprendidos',
    '_auto_guardar_archivo',
    '_auto_guardar_excel',
    '_init_db',
]