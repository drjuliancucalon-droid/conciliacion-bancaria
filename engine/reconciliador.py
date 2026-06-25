"""
Motor de conciliación bancaria - Fases A/B/C/D
CREDIEXPRESS POPAYÁN SAS — Conciliación Bancaria
"""

import pandas as pd
import numpy as np
from config import TOL_EXACTA, TOL_APROX
from engine.nc_learning import buscar_en_catalogo_nc, _aprender_match_nc


def _prefijo_doc(doc):
    if not doc:
        return ''
    doc = str(doc).upper().strip()
    if doc.startswith(('CE-', 'NC-', 'CG-', 'CON-', 'CO-', 'RE-', 'RG-')):
        return doc[:3] if doc[2] == '-' else doc[:2]
    return doc[:2]


def _num_doc(doc):
    if not doc:
        return ''
    doc = str(doc).upper().strip()
    for pref in ['CE-', 'NC-', 'CG-', 'CON-', 'CO-', 'RE-', 'RG-']:
        if doc.startswith(pref):
            return doc[len(pref):]
    return doc


def score_concepto(desc_banco, concepto_aux):
    if not desc_banco or not concepto_aux:
        return 0.0
    db = set(str(desc_banco).lower().split())
    ca = set(str(concepto_aux).lower().split())
    if not db or not ca:
        return 0.0
    inter = db & ca
    union = db | ca
    return len(inter) / len(union) if union else 0.0


def comparar_documentos(df_banco, df_aux, banco_meta=None, aux_meta=None,
                        tol_exacta=None, tol_aprox=None):
    """
    Motor principal de conciliación con 4 fases:
    A: Match exacto por valor (+/- tol_exacta)
    B: Match aproximado por valor (tol_aprox %)
    C: Match por concepto NC aprendido
    D: Match 1:N (agrupados) y rechazos
    
    Retorna: (matches, solo_banco, solo_aux, stats)
    """
    # Usar tolerancias pasadas o las de config
    _tol_exacta = tol_exacta if tol_exacta is not None else TOL_EXACTA
    _tol_aprox = tol_aprox if tol_aprox is not None else TOL_APROX
    
    # Copias de trabajo
    banco = df_banco.copy()
    aux = df_aux.copy()
    
    # Agregar columnas de control
    banco['_matched'] = False
    banco['_match_type'] = ''
    banco['_match_ref'] = ''
    aux['_matched'] = False
    aux['_match_type'] = ''
    aux['_match_ref'] = ''
    
    matches = []
    
    # ─── FASE A: Match exacto por valor ─────────────────────────────────────
    for i, b_row in banco.iterrows():
        if b_row['_matched']:
            continue
        vb = b_row['VALOR']
        if vb is None or pd.isna(vb):
            continue
        
        # Buscar en auxiliar no coincidentes
        candidatos = aux[~aux['_matched']].copy()
        if candidatos.empty:
            continue
        
        # Calcular diferencia absoluta
        candidatos['_diff'] = (candidatos['VALOR_NETO'] - vb).abs()
        exactos = candidatos[candidatos['_diff'] <= _tol_exacta]
        
        if not exactos.empty:
            # Tomar el de menor diferencia
            best = exactos.nsmallest(1, '_diff').iloc[0]
            aux_idx = best.name
            
            # Marcar coincidencia
            banco.at[i, '_matched'] = True
            banco.at[i, '_match_type'] = 'EXACTA'
            banco.at[i, '_match_ref'] = str(aux_idx)
            aux.at[aux_idx, '_matched'] = True
            aux.at[aux_idx, '_match_type'] = 'EXACTA'
            aux.at[aux_idx, '_match_ref'] = str(i)
            
            matches.append({
                'banco_idx': i,
                'aux_idx': aux_idx,
                'tipo': 'EXACTA',
                'valor_banco': vb,
                'valor_aux': best['VALOR_NETO'],
                'diff': best['_diff'],
                'concepto_banco': b_row['DESCRIPCION'],
                'concepto_aux': best.get('CONCEPTO', ''),
                'documento_aux': best.get('DOCUMENTO', ''),
            })
    
    # ─── FASE B: Match aproximado por valor ────────────────────────────────
    for i, b_row in banco.iterrows():
        if b_row['_matched']:
            continue
        vb = b_row['VALOR']
        if vb is None or pd.isna(vb) or vb == 0:
            continue
        
        candidatos = aux[~aux['_matched']].copy()
        if candidatos.empty:
            continue
        
        # Diferencia relativa
        candidatos['_diff_rel'] = ((candidatos['VALOR_NETO'] - vb).abs() / abs(vb))
        aprox = candidatos[candidatos['_diff_rel'] <= _tol_aprox]
        
        if not aprox.empty:
            best = aprox.nsmallest(1, '_diff_rel').iloc[0]
            aux_idx = best.name
            
            banco.at[i, '_matched'] = True
            banco.at[i, '_match_type'] = 'APROX'
            banco.at[i, '_match_ref'] = str(aux_idx)
            aux.at[aux_idx, '_matched'] = True
            aux.at[aux_idx, '_match_type'] = 'APROX'
            aux.at[aux_idx, '_match_ref'] = str(i)
            
            matches.append({
                'banco_idx': i,
                'aux_idx': aux_idx,
                'tipo': 'APROX',
                'valor_banco': vb,
                'valor_aux': best['VALOR_NETO'],
                'diff': best['_diff_rel'] * abs(vb),
                'concepto_banco': b_row['DESCRIPCION'],
                'concepto_aux': best.get('CONCEPTO', ''),
                'documento_aux': best.get('DOCUMENTO', ''),
            })
    
    # ─── PRE-PASE NC: Buscar matches por catálogo NC aprendido ───────────────
    for i, b_row in banco.iterrows():
        if b_row['_matched']:
            continue
        vb = b_row['VALOR']
        if vb is None or pd.isna(vb):
            continue
        
        # Solo buscar NC si es cargo bancario (valor negativo)
        if vb >= 0:
            continue
        
        candidatos = aux[~aux['_matched']].copy()
        # Filtrar solo documentos NC-
        candidatos = candidatos[candidatos['DOCUMENTO'].astype(str).str.upper().str.startswith('NC-')]
        if candidatos.empty:
            continue
        
        # Buscar en catálogo NC
        uuid, sim = buscar_en_catalogo_nc(b_row['DESCRIPCION'], candidatos.iloc[0]['CONCEPTO'])
        if uuid and sim >= 0.30:
            # Buscar el mejor candidato NC por valor también
            candidatos['_diff'] = (candidatos['VALOR_NETO'] - vb).abs()
            # Permitir tolerancia más amplia para NC (5% para rechazos)
            nc_candidatos = candidatos[candidatos['_diff'] <= abs(vb) * 0.05]
            if not nc_candidatos.empty:
                best = nc_candidatos.nsmallest(1, '_diff').iloc[0]
                aux_idx = best.name
                
                banco.at[i, '_matched'] = True
                banco.at[i, '_match_type'] = 'NC_CATALOGO'
                banco.at[i, '_match_ref'] = str(aux_idx)
                aux.at[aux_idx, '_matched'] = True
                aux.at[aux_idx, '_match_type'] = 'NC_CATALOGO'
                aux.at[aux_idx, '_match_ref'] = str(i)
                
                matches.append({
                    'banco_idx': i,
                    'aux_idx': aux_idx,
                    'tipo': 'NC_CATALOGO',
                    'valor_banco': vb,
                    'valor_aux': best['VALOR_NETO'],
                    'diff': best['_diff'],
                    'concepto_banco': b_row['DESCRIPCION'],
                    'concepto_aux': best.get('CONCEPTO', ''),
                    'documento_aux': best.get('DOCUMENTO', ''),
                    'nc_uuid': uuid,
                    'nc_similitud': sim,
                })
                
                # Registrar aprendizaje
                _aprender_match_nc(b_row['DESCRIPCION'], best.get('DOCUMENTO', ''),
                                  best.get('CONCEPTO', ''), 'NC_CATALOGO',
                                  vb, best['VALOR_NETO'])
    
    # ─── FASE C: Match 1:N (Agrupados) - Banco tiene N cargos, Aux tiene 1 NC ───
    # Primero identificar NCs no coincidentes en auxiliar
    aux_nc = aux[(~aux['_matched']) & (aux['DOCUMENTO'].astype(str).str.upper().str.startswith('NC-'))]
    banco_cargos = banco[(~banco['_matched']) & (banco['VALOR'] < 0)]
    
    for aux_idx, a_row in aux_nc.iterrows():
        v_aux = a_row['VALOR_NETO']
        if v_aux is None or pd.isna(v_aux) or v_aux <= 0:
            continue
        
        # Buscar combinación de cargos bancarios que sumen el valor de la NC
        # Usar aproximación con tolerancia 5%
        cargos_vals = banco_cargos[~banco_cargos['_matched']]['VALOR'].abs()
        if len(cargos_vals) < 2:
            continue
        
        # Buscar pares/tríos que sumen ~ v_aux (simplificado: buscar 2 cargos)
        from itertools import combinations
        cargos_disponibles = banco_cargos[~banco_cargos['_matched']]
        if len(cargos_disponibles) >= 2:
            for combo_idx in combinations(cargos_disponibles.index, 2):
                suma = cargos_disponibles.loc[list(combo_idx), 'VALOR'].sum()
                diff_rel = abs(suma + v_aux) / v_aux  # v_aux es positivo, cargos son negativos
                if diff_rel <= 0.05:  # 5% tolerancia
                    # Match agrupado encontrado
                    for bi in combo_idx:
                        banco.at[bi, '_matched'] = True
                        banco.at[bi, '_match_type'] = 'AGRUPADO'
                        banco.at[bi, '_match_ref'] = str(aux_idx)
                    
                    aux.at[aux_idx, '_matched'] = True
                    aux.at[aux_idx, '_match_type'] = 'AGRUPADO'
                    aux.at[aux_idx, '_match_ref'] = ','.join(str(x) for x in combo_idx)
                    
                    for bi in combo_idx:
                        b_row = banco.loc[bi]
                        matches.append({
                            'banco_idx': bi,
                            'aux_idx': aux_idx,
                            'tipo': 'AGRUPADO',
                            'valor_banco': b_row['VALOR'],
                            'valor_aux': v_aux,
                            'diff': abs(suma + v_aux),
                            'concepto_banco': b_row['DESCRIPCION'],
                            'concepto_aux': a_row.get('CONCEPTO', ''),
                            'documento_aux': a_row.get('DOCUMENTO', ''),
                        })
                    break
    
    # ─── FASE D: Match Rechazos (cargo banco + NC devolución) ───────────────
    # Buscar cargo bancario seguido de NC con valor similar (rechazo)
    for i, b_row in banco.iterrows():
        if b_row['_matched']:
            continue
        vb = b_row['VALOR']
        if vb is None or pd.isna(vb) or vb >= 0:
            continue  # Solo cargos
        
        # Buscar NC en auxiliar con valor positivo similar (devolución)
        candidatos = aux[(~aux['_matched']) & 
                         (aux['DOCUMENTO'].astype(str).str.upper().str.startswith('NC-')) &
                         (aux['VALOR_NETO'] > 0)].copy()
        if candidatos.empty:
            continue
        
        candidatos['_diff'] = (candidatos['VALOR_NETO'] - abs(vb)).abs()
        rechazo = candidatos[candidatos['_diff'] <= abs(vb) * 0.05]
        
        if not rechazo.empty:
            best = rechazo.nsmallest(1, '_diff').iloc[0]
            aux_idx = best.name
            
            banco.at[i, '_matched'] = True
            banco.at[i, '_match_type'] = 'RECHAZO'
            banco.at[i, '_match_ref'] = str(aux_idx)
            aux.at[aux_idx, '_matched'] = True
            aux.at[aux_idx, '_match_type'] = 'RECHAZO'
            aux.at[aux_idx, '_match_ref'] = str(i)
            
            matches.append({
                'banco_idx': i,
                'aux_idx': aux_idx,
                'tipo': 'RECHAZO',
                'valor_banco': vb,
                'valor_aux': best['VALOR_NETO'],
                'diff': best['_diff'],
                'concepto_banco': b_row['DESCRIPCION'],
                'concepto_aux': best.get('CONCEPTO', ''),
                'documento_aux': best.get('DOCUMENTO', ''),
            })
    
    # ─── Preparar resultados ────────────────────────────────────────────────
    # DataFrames de no coincidentes
    solo_banco = banco[~banco['_matched']].copy()
    solo_aux = aux[~aux['_matched']].copy()
    
    # Estadísticas
    n_exactas = len([m for m in matches if m['tipo'] == 'EXACTA'])
    n_aprox = len([m for m in matches if m['tipo'] == 'APROX'])
    n_nc = len([m for m in matches if m['tipo'] == 'NC_CATALOGO'])
    n_agrup = len([m for m in matches if m['tipo'] == 'AGRUPADO'])
    n_rech = len([m for m in matches if m['tipo'] == 'RECHAZO'])
    
    stats = {
        'n_banco': len(df_banco),
        'n_aux': len(df_aux),
        'n_exactas': n_exactas,
        'n_aprox': n_aprox + n_nc + n_agrup + n_rech,  # todos los no exactos
        'n_solo_banco': len(solo_banco),
        'n_solo_aux': len(solo_aux),
        'tasa': (len(matches) / max(len(df_banco), 1)) * 100,
        'saldo_banco': df_banco['VALOR'].sum() if 'VALOR' in df_banco.columns else 0,
        'saldo_aux': df_aux['VALOR_NETO'].sum() if 'VALOR_NETO' in df_aux.columns else 0,
    }
    stats['diferencia_neta'] = stats['saldo_banco'] - stats['saldo_aux']
    
    # Limpiar columnas temporales
    for df in [banco, aux, solo_banco, solo_aux]:
        for col in ['_matched', '_match_type', '_match_ref', '_diff', '_diff_rel']:
            if col in df.columns:
                df.drop(columns=[col], inplace=True, errors='ignore')
    
    return pd.DataFrame(matches), solo_banco, solo_aux, stats
