# dashboard/utils.py
import pandas as pd
import numpy as np

def converter_data_robusta(series):
    series = series.astype(str).str.strip()
    series = series.replace(['nan', 'None', '', 'NaT', '0', '#N/A', 'nan'], np.nan)
    return pd.to_datetime(series, format='mixed', dayfirst=True, errors='coerce')

def tornar_colunas_unicas(lista_colunas):
    seen = {}
    nova_lista = []
    for col in lista_colunas:
        c = str(col).strip()
        if c in seen:
            seen[c] += 1
            nova_lista.append(f"{c}.{seen[c]}")
        else:
            seen[c] = 0
            nova_lista.append(c)
    return nova_lista

def recortar_zeros_pontas(series_dados):
    lista = series_dados.tolist()
    idx_inicio = -1
    idx_fim = -1
    for i, v in enumerate(lista):
        if v > 0:
            if idx_inicio == -1: idx_inicio = i
            idx_fim = i
    
    if idx_inicio == -1: return [np.nan] * len(lista)
    
    resultado = []
    for i, v in enumerate(lista):
        if i < idx_inicio or i > idx_fim: resultado.append(np.nan)
        else: resultado.append(v)
    return resultado

def aplicar_heatmap_vermelho(df):
    return df.style.background_gradient(cmap='Reds', axis=None).format(precision=0)