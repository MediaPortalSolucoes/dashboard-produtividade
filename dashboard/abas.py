import streamlit as st
import pandas as pd
import graficos as gf
from utils import aplicar_heatmap_vermelho

COL_ENC = 'Encarregado'
COL_DATA_FINAL_ABERTA = 'Data Final (aberta)'
COL_DATA_INI = 'Data Inicial'
COL_DATA_FIM = 'Data Final'
COL_NOME_TASK = 'Nome Task'
COL_LINK = 'Link'
COL_ATIV_SEM = 'Atividades Semanal'

TXT_TOTAL = "Total"
TXT_TOTAL_ACUMULADO = "Total Acumulado"
TXT_ABERTAS = "🔴 Abertas"
TXT_FECHADAS = "🟢 Fechadas"
TXT_RESUMO = "Resumo"
TXT_DETALHES = "Detalhes"
TXT_LINK_UI = "Link"
TXT_ABRIR_LINK = "Abrir ↗"
TXT_SEM_DADOS = "Sem dados disponíveis."
TXT_PROG_SEMANA = "Progresso da Semana"
TXT_PROG_MES = "Progresso do Mês"
TXT_SEL_SEMANA = "Semana (Sexta-feira referência):"
TXT_SEL_MES_VISUALIZAR = "Selecione o Mês para Visualizar:"
TXT_SEL_MES_REFERENCIA = "Selecione o Mês de Referência:"
TXT_CURVA_PRODUTIVIDADE = "Curva de Produtividade (Acumulada)"
TXT_ESCOPO_TEMPO = "Escolha o escopo de tempo:"
TXT_VISAO_MENSAL = "📅 Visão Mensal"
TXT_VISAO_GERAL = "📈 Visão Geral (Histórico Completo)"
TXT_SEL_ENC_COMPARAR = "Selecione Encarregados para Comparar:"
TXT_SEM_DATAS_VALIDAS = "Não há datas válidas."
TXT_SEM_DADOS_PERIODO = "Sem dados de tarefas executadas para o período."
TXT_DADOS_INDIVIDUAIS = "Dados Individuais"

def _renderizar_lista_expansivel(df_filtrado, col_status_ref, val_aberto, val_fechado):
    column_config = {
        TXT_LINK_UI: st.column_config.LinkColumn(TXT_LINK_UI, display_text=TXT_ABRIR_LINK), 
        COL_DATA_INI: st.column_config.DateColumn(COL_DATA_INI, format="DD/MM/YYYY"), 
        COL_DATA_FIM: st.column_config.DateColumn(COL_DATA_FIM, format="DD/MM/YYYY")
    }
    for enc in sorted(df_filtrado[COL_ENC].unique()):
        d_e = df_filtrado[df_filtrado[COL_ENC] == enc]
        ab = d_e[d_e[col_status_ref] == val_aberto].sort_values(by=COL_DATA_INI, ascending=True)
        fe = d_e[d_e[col_status_ref] == val_fechado].sort_values(by=COL_DATA_FIM, ascending=True)
        with st.expander(f"{enc} ({len(ab) + len(fe)}) - {TXT_ABERTAS}: {len(ab)} | {TXT_FECHADAS}: {len(fe)}"):
            if not ab.empty:
                st.caption(TXT_ABERTAS)
                st.dataframe(ab[[COL_NOME_TASK, COL_DATA_INI, COL_LINK]], width='stretch', hide_index=True, column_config=column_config)
            if not fe.empty:
                st.caption(TXT_FECHADAS)
                st.dataframe(fe[[COL_NOME_TASK, COL_DATA_FIM, COL_LINK]], width='stretch', hide_index=True, column_config=column_config)

def _obter_opcoes_de_semana(df_f):
    set_semanas = set()
    hj = pd.Timestamp.now().normalize()
    sexta_atual = hj - pd.to_timedelta(hj.dayofweek, unit='D') + pd.to_timedelta(4, unit='D')
    set_semanas.add(sexta_atual)
    
    if not df_f.empty and COL_DATA_FINAL_ABERTA in df_f.columns:
        dates = pd.to_datetime(df_f[COL_DATA_FINAL_ABERTA], errors='coerce').dropna()
        fridays = dates - pd.to_timedelta(dates.dt.dayofweek, unit='D') + pd.to_timedelta(4, unit='D')
        set_semanas.update(fridays.unique())
        
    lista_semanas = sorted([d for d in list(set_semanas) if pd.notnull(d)], reverse=True)
    lista_str = [d.strftime('%d/%m/%Y') for d in lista_semanas]
    idx_padrao = lista_str.index(sexta_atual.strftime('%d/%m/%Y')) if sexta_atual.strftime('%d/%m/%Y') in lista_str else 0
    return lista_str, idx_padrao

def _filtrar_tabela_semana(df_f, dt_sel):
    d_seg_sem, d_sex_sem = dt_sel - pd.Timedelta(days=4), dt_sel
    dt_ini_tmp = pd.to_datetime(df_f.get('Data Inicial', pd.Series()), dayfirst=True, errors='coerce').dt.date
    dt_fim_tmp = pd.to_datetime(df_f.get('Data Final', pd.Series()), dayfirst=True, errors='coerce').dt.date
    
    mask_viva = (dt_ini_tmp <= d_sex_sem.date()) & (dt_fim_tmp.isna() | (dt_fim_tmp >= d_seg_sem.date()))
    
    df_sem = df_f[mask_viva].drop_duplicates(subset=['ID'], keep='last').copy()
    if not df_sem.empty:
        df_sem['Status_Na_Semana'] = 'Aberto'
        mask_fechou = dt_fim_tmp.notna() & (dt_fim_tmp >= d_seg_sem.date()) & (dt_fim_tmp <= d_sex_sem.date())
        df_sem.loc[mask_fechou, 'Status_Na_Semana'] = 'Executado'
    return df_sem

def renderizar_aba_semana(df_f):
    lista_str, idx_padrao = _obter_opcoes_de_semana(df_f)
    sem_sel = st.selectbox(TXT_SEL_SEMANA, lista_str, index=idx_padrao)
    dt_sel = pd.to_datetime(sem_sel, dayfirst=True)
    d_seg, d_dom = dt_sel - pd.Timedelta(days=4), dt_sel + pd.Timedelta(days=2)
    
    st.subheader(f"{TXT_PROG_SEMANA} ({d_seg.strftime('%d/%m')} a {d_dom.strftime('%d/%m')})")
    
    df_sem = _filtrar_tabela_semana(df_f, dt_sel)
    fig_h, last_h = gf.criar_grafico_historico_semanal(df_sem, sem_sel)
    
    if last_h is not None:
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric(TXT_TOTAL, last_h['Total_Tarefas'])
        c_m2.metric(TXT_ABERTAS, last_h['Total_Tarefas'] - last_h['Total_Fechadas'])
        c_m3.metric(TXT_FECHADAS, last_h['Total_Fechadas'])
    st.plotly_chart(fig_h, width='stretch')
    
    if not df_sem.empty:
        piv = pd.pivot_table(df_sem[df_sem['Status_Na_Semana']=='Executado'], index=COL_ENC, columns='Nome Dia Semana', values='ID', aggfunc='count', fill_value=0)
        piv = piv.reindex(columns=['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'], fill_value=0)
        st.subheader(f"{TXT_RESUMO} da Semana")
        st.dataframe(aplicar_heatmap_vermelho(piv), width='stretch')
        st.markdown("---")
        st.subheader(f"{TXT_DETALHES} da Semana")
        _renderizar_lista_expansivel(df_sem, 'Status_Na_Semana', 'Aberto', 'Executado')

def _obter_opcoes_de_mes(df_analise):
    df_analise['Periodo_Mes_Ref'] = df_analise[COL_DATA_FINAL_ABERTA].dt.to_period('M')
    periodos_unicos_mes = sorted(df_analise['Periodo_Mes_Ref'].dropna().unique(), reverse=True)
    if not periodos_unicos_mes: periodos_unicos_mes = [pd.Timestamp.now().to_period('M')]
    meses_full_list = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Jun', 7: 'Jul', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    opcoes_formatadas_mes = [f"{meses_full_list[p.month]} {p.year}" for p in periodos_unicos_mes]
    hj_periodo = pd.Timestamp.now().to_period('M')
    idx_default_mes = periodos_unicos_mes.index(hj_periodo) if hj_periodo in periodos_unicos_mes else 0
    return periodos_unicos_mes, opcoes_formatadas_mes, idx_default_mes, meses_full_list

def _filtrar_tabela_mes(df_f, periodo_selecionado_mes):
    d1_m, d2_m = periodo_selecionado_mes.start_time.date(), periodo_selecionado_mes.end_time.date()
    dt_ini_tmp_m = pd.to_datetime(df_f.get('Data Inicial', pd.Series()), dayfirst=True, errors='coerce').dt.date
    dt_fim_tmp_m = pd.to_datetime(df_f.get('Data Final', pd.Series()), dayfirst=True, errors='coerce').dt.date
    
    mask_viva_m = (dt_ini_tmp_m <= d2_m) & (dt_fim_tmp_m.isna() | (dt_fim_tmp_m >= d1_m))
    
    df_m = df_f[mask_viva_m].drop_duplicates(subset=['ID'], keep='last').copy()
    if not df_m.empty:
        df_m['Status_No_Mes'] = 'Aberto'
        mask_fechou_m = dt_fim_tmp_m.notna() & (dt_fim_tmp_m >= d1_m) & (dt_fim_tmp_m <= d2_m)
        df_m.loc[mask_fechou_m, 'Status_No_Mes'] = 'Executado'
    return df_m

def renderizar_aba_mes(df_f, df_analise):
    if df_f.empty or COL_DATA_FINAL_ABERTA not in df_f.columns:
        st.info(TXT_SEM_DADOS)
        return
    periodos_unicos_mes, opcoes_formatadas_mes, idx_default_mes, meses_full_list = _obter_opcoes_de_mes(df_analise)
    sel_mes_aba2_str = st.selectbox(TXT_SEL_MES_VISUALIZAR, opcoes_formatadas_mes, index=idx_default_mes)
    periodo_selecionado_mes = periodos_unicos_mes[opcoes_formatadas_mes.index(sel_mes_aba2_str)]
    
    st.markdown(f"### {TXT_PROG_MES} ({meses_full_list.get(periodo_selecionado_mes.month, '').lower()})")
    
    df_m = _filtrar_tabela_mes(df_f, periodo_selecionado_mes)
    fig_hm, last_hm = gf.criar_grafico_historico_mensal(df_m, periodo_selecionado_mes)
    
    if last_hm is not None:
        col_met_m1, col_met_m2, col_met_m3 = st.columns(3)
        col_met_m1.metric(TXT_TOTAL_ACUMULADO, f"{last_hm['Mensal_Tarefas']:.0f}")
        col_met_m2.metric(TXT_ABERTAS, f"{last_hm['Mensal_Tarefas'] - last_hm['Mensal_Fechadas']:.0f}")
        col_met_m3.metric(TXT_FECHADAS, f"{last_hm['Mensal_Fechadas']:.0f}")
    st.plotly_chart(fig_hm, width='stretch')
    
    if not df_m.empty:
        piv = pd.pivot_table(df_m[df_m['Status_No_Mes']=='Executado'], index=COL_ENC, columns=df_m[COL_DATA_FINAL_ABERTA].dt.day, values='ID', aggfunc='count', fill_value=0)
        st.subheader(f"{TXT_RESUMO} do Mês")
        st.dataframe(aplicar_heatmap_vermelho(piv), width='stretch')
        st.markdown("---")
        st.subheader(f"{TXT_DETALHES} do Mês")
        _renderizar_lista_expansivel(df_m, 'Status_No_Mes', 'Aberto', 'Executado')

def _obter_dados_produtividade_mensal(df_prod_base):
    df_prod_base['Periodo_Mes'] = df_prod_base[COL_DATA_FINAL_ABERTA].dt.to_period('M')
    periodos_unicos = sorted(df_prod_base['Periodo_Mes'].dropna().unique(), reverse=True)
    if not periodos_unicos: return pd.DataFrame(), ""
        
    meses_full_prod = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Jun', 7: 'Jul', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    opcoes_formatadas = [f"{meses_full_prod[p.month]} {p.year}" for p in periodos_unicos]
    hj_periodo = pd.Timestamp.now().to_period('M')
    idx_default = periodos_unicos.index(hj_periodo) if hj_periodo in periodos_unicos else 0
    
    sel_mes_str = st.selectbox(TXT_SEL_MES_REFERENCIA, opcoes_formatadas, index=idx_default)
    periodo_selecionado = periodos_unicos[opcoes_formatadas.index(sel_mes_str)]
    
    df_prod_plot = df_prod_base[df_prod_base['Periodo_Mes'] == periodo_selecionado].copy()
    titulo_legenda = f"crescimento diário em **{sel_mes_str}**"
    return df_prod_plot, titulo_legenda

def renderizar_aba_produtividade(df_f, df_analise, d_ini, d_fim, encarregados_filtro, contrato_filtro, status_tarefa_filtro):
    st.header(TXT_CURVA_PRODUTIVIDADE)
    modo_visualizacao = st.radio(TXT_ESCOPO_TEMPO, [TXT_VISAO_MENSAL, TXT_VISAO_GERAL], horizontal=True)
    st.markdown("---")
    
    if df_analise is None or df_analise.empty or COL_DATA_FINAL_ABERTA not in df_analise.columns:
        st.info(TXT_SEM_DADOS)
        return
        
    df_prod_base = df_analise.copy()
    if "Todos" not in encarregados_filtro: df_prod_base = df_prod_base[df_prod_base[COL_ENC].isin(encarregados_filtro)]
    if contrato_filtro != "Todos": df_prod_base = df_prod_base[df_prod_base['Status_Funcionario'] == contrato_filtro]
    if status_tarefa_filtro != "Todos": df_prod_base = df_prod_base[df_prod_base['Status_Tarefa'] == status_tarefa_filtro]

    if modo_visualizacao == TXT_VISAO_MENSAL:
        df_prod_plot, titulo_legenda = _obter_dados_produtividade_mensal(df_prod_base)
        if df_prod_plot.empty:
            st.info(TXT_SEM_DATAS_VALIDAS)
            return
    else:
        df_prod_plot = df_prod_base[(df_prod_base[COL_DATA_FINAL_ABERTA].dt.date >= d_ini) & (df_prod_base[COL_DATA_FINAL_ABERTA].dt.date <= d_fim)].copy()
        titulo_legenda = "crescimento acumulado de **todo o período selecionado**"

    if not df_prod_plot.empty:
        todos_enc = sorted(df_prod_plot[COL_ENC].unique())
        sel_enc_prod = st.multiselect(TXT_SEL_ENC_COMPARAR, options=todos_enc, default=todos_enc)
        st.caption(f"Exibindo {titulo_legenda}")
        
        fig_cresc = gf.criar_grafico_crescimento_acumulado(df_prod_plot, sel_enc_prod, df_context=df_analise)
        st.plotly_chart(fig_cresc, width='stretch')
        st.markdown("---")
    else: 
        st.info(TXT_SEM_DADOS_PERIODO)

def _definir_nomes_alvo(df_equipe, encarregados_filtro, contrato_filtro):
    nomes = []
    if df_equipe is not None and not df_equipe.empty:
        if contrato_filtro == "Todos": nomes = df_equipe['Nome'].unique().tolist()
        else: nomes = df_equipe[df_equipe['Status_Funcionario'] == contrato_filtro]['Nome'].unique().tolist()
    if "Todos" not in encarregados_filtro:
        if not nomes: nomes = encarregados_filtro
        else: nomes = list(set(nomes) & set(encarregados_filtro))
    return nomes

def renderizar_aba_pontuacao(df_equipe, df_notas_tabela1, df_notas_tabela2, df_lideranca_mapa, encarregados_filtro, contrato_filtro, d_ini, d_fim):
    nomes = _definir_nomes_alvo(df_equipe, encarregados_filtro, contrato_filtro)
    f_ind, df_ind_t = gf.criar_grafico_pontuacao_individual(df_notas_tabela1, nomes, d_ini, d_fim)
    st.plotly_chart(f_ind, width='stretch')
    with st.expander(TXT_DADOS_INDIVIDUAIS): st.dataframe(df_ind_t, width='stretch', hide_index=True)
    st.markdown("---")
    f_lid, df_lid_t, _ = gf.criar_grafico_pontuacao_lideres(df_lideranca_mapa, df_notas_tabela2, nomes, d_ini, d_fim)
    st.plotly_chart(f_lid, width='stretch')
    st.markdown("---")
    f_tot = gf.criar_grafico_pontuacao_combinada(df_notas_tabela1, df_notas_tabela2, df_lideranca_mapa, nomes, d_ini, d_fim)
    st.plotly_chart(f_tot, width='stretch')