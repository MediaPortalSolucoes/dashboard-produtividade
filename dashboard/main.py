import streamlit as st
import pandas as pd
from datetime import date
from data import carregar_dados_completos
import abas 

TXT_TITULO = "Dashboard de Produtividade"
TXT_TODOS = "Todos"
TXT_FILTROS = "Filtros"
TXT_ENCARREGADO = "Encarregado"
TXT_CONTRATO = "Contrato"
TXT_STATUS_TAR = "Status Tarefa"
TXT_LIMPAR = "Limpar Filtros"
TXT_SEM_MES = "Semana Mês"
TXT_PERIODO = "Período"
TXT_TOTAL_FILTRADAS = "Total Tarefas Filtradas"
TXT_ABA_SEMANA = "Semana"
TXT_ABA_MES = "Mês"
TXT_ABA_PRODUTIVIDADE = "Produtividade"
TXT_ABA_PONTUACAO = "Pontuação"

COL_ENC = "Encarregado"
COL_STATUS_FUNC = "Status_Funcionario"
COL_STATUS_TAR_DF = "Status_Tarefa"
COL_SEM_MES_DF = "Semana do Mês"
COL_DATA_FINAL = "Data Final (aberta)"

st.set_page_config(layout="wide", page_title=TXT_TITULO)

def carregar_versao():
    try:
        with open("VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "(Arquivo VERSION não encontrado)"

def extrair_limites_de_data(df_analise, df_notas_tabela1):
    all_dates = []
    if df_analise is not None and not df_analise.empty and COL_DATA_FINAL in df_analise.columns:
        all_dates.extend(pd.to_datetime(df_analise[COL_DATA_FINAL]).dt.date.dropna().tolist())
    if df_notas_tabela1 is not None:
        for c in df_notas_tabela1.columns:
            dt = pd.to_datetime(pd.Series([c]), dayfirst=True, errors='coerce')
            if pd.notna(dt[0]): all_dates.append(dt[0].date())
    return (min(all_dates), max(all_dates)) if all_dates else (date.today(), date.today())

def configurar_estado_inicial(min_date, max_date):
    if 'filtros_iniciados' not in st.session_state:
        st.session_state.encarregado_filtro = [TXT_TODOS]
        st.session_state.contrato_filtro = TXT_TODOS
        st.session_state.status_tarefa_filtro = TXT_TODOS
        st.session_state.semana_filtro = TXT_TODOS
        st.session_state.date_slider = (min_date, max_date)
        st.session_state.filtros_iniciados = True
        st.rerun() 

def limpar_filtros():
    st.session_state.encarregado_filtro = [TXT_TODOS]
    st.session_state.contrato_filtro = TXT_TODOS
    st.session_state.status_tarefa_filtro = TXT_TODOS
    st.session_state.semana_filtro = TXT_TODOS

def renderizar_sidebar(df_analise):
    with st.sidebar:
        st.title(TXT_FILTROS)
        if df_analise is not None and not df_analise.empty:
            if COL_ENC in df_analise.columns:
                st.multiselect(TXT_ENCARREGADO, [TXT_TODOS] + sorted(df_analise[COL_ENC].unique()), key='encarregado_filtro')
            if COL_STATUS_FUNC in df_analise.columns:
                st.selectbox(TXT_CONTRATO, [TXT_TODOS] + sorted(df_analise[COL_STATUS_FUNC].dropna().unique()), key='contrato_filtro')
            if COL_STATUS_TAR_DF in df_analise.columns:
                st.selectbox(TXT_STATUS_TAR, [TXT_TODOS] + sorted(df_analise[COL_STATUS_TAR_DF].unique()), key='status_tarefa_filtro')
        st.button(TXT_LIMPAR, on_click=limpar_filtros)

def aplicar_filtros_globais(df_analise):
    df_f = df_analise.copy() if df_analise is not None else pd.DataFrame()
    if not df_f.empty:
        if TXT_TODOS not in st.session_state.encarregado_filtro and COL_ENC in df_f.columns: 
            df_f = df_f[df_f[COL_ENC].isin(st.session_state.encarregado_filtro)]
        if st.session_state.contrato_filtro != TXT_TODOS and COL_STATUS_FUNC in df_f.columns: 
            df_f = df_f[df_f[COL_STATUS_FUNC] == st.session_state.contrato_filtro]
        if st.session_state.status_tarefa_filtro != TXT_TODOS and COL_STATUS_TAR_DF in df_f.columns: 
            df_f = df_f[df_f[COL_STATUS_TAR_DF] == st.session_state.status_tarefa_filtro]
    return df_f

def renderizar_header_e_refinar_tabela(df_analise, df_f, min_date, max_date):
    c1, c2, c3 = st.columns([2, 1, 3])
    with c1:
        sems = [TXT_TODOS] + sorted([x for x in df_analise[COL_SEM_MES_DF].unique() if pd.notna(x)]) if (not df_analise.empty and COL_SEM_MES_DF in df_analise.columns) else [TXT_TODOS]
        st.selectbox(TXT_SEM_MES, sems, key='semana_filtro')
    with c3:
        st.slider(TXT_PERIODO, min_value=min_date, max_value=max_date, key='date_slider')

    if st.session_state.semana_filtro != TXT_TODOS and COL_SEM_MES_DF in df_f.columns: 
        df_f = df_f[df_f[COL_SEM_MES_DF] == st.session_state.semana_filtro]
        
    d_ini, d_fim = st.session_state.date_slider
    with c2: st.metric(TXT_TOTAL_FILTRADAS, len(df_f))
    st.divider()
    return df_f, d_ini, d_fim

def main():
    st.title(TXT_TITULO)
    st.sidebar.caption(f"Versão do Dashboard: v{carregar_versao()}")
    df_analise, df_notas_tabela1, df_notas_tabela2, df_lideranca_mapa, df_equipe, df_backlog, df_source_analise = carregar_dados_completos()
    min_date, max_date = extrair_limites_de_data(df_analise, df_notas_tabela1)
    
    configurar_estado_inicial(min_date, max_date)
    renderizar_sidebar(df_analise)

    df_f_pre_header = aplicar_filtros_globais(df_analise)
    df_f_final, d_ini, d_fim = renderizar_header_e_refinar_tabela(df_analise, df_f_pre_header, min_date, max_date)

    t1, t2, t3 = st.tabs([TXT_ABA_SEMANA, TXT_ABA_MES, TXT_ABA_PRODUTIVIDADE])

    with t1: abas.renderizar_aba_semana(df_f_final)
    with t2: abas.renderizar_aba_mes(df_f_final, df_analise)
    with t3: abas.renderizar_aba_produtividade(df_f_final, df_analise, d_ini, d_fim, st.session_state.encarregado_filtro, st.session_state.contrato_filtro, st.session_state.status_tarefa_filtro)
    # with t4: abas.renderizar_aba_pontuacao(df_equipe, df_notas_tabela1, df_notas_tabela2, df_lideranca_mapa, st.session_state.encarregado_filtro, st.session_state.contrato_filtro, d_ini, d_fim)

if __name__ == "__main__":
    main()