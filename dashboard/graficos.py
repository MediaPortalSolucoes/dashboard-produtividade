import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from utils import converter_data_robusta, recortar_zeros_pontas

def criar_grafico_historico_semanal(df_sem, data_referencia_str):
    if df_sem is None or df_sem.empty: 
        return go.Figure().update_layout(title="Sem dados para a semana", template='plotly_white'), None
        
    try: data_ref = pd.to_datetime(data_referencia_str, format='%d/%m/%Y').date()
    except: return go.Figure(), None
        
    segunda, sexta = data_ref - pd.Timedelta(days=4), data_ref
    df = df_sem.copy()
    
    if 'Atividades Semanal' in df.columns and 'Sub-Lista / Grupo' in df.columns:
        mask_lista = df['Atividades Semanal'].astype(str).str.upper().str.contains('ATIVIDADES DA SEMANA', na=False)
        mask_grupo = df['Sub-Lista / Grupo'].astype(str).str.upper().str.contains('ATIVIDADES', na=False)
        df = df[mask_lista & mask_grupo].copy()
    
    if 'Data Inicial' in df.columns: df['Data_Ini_DT'] = pd.to_datetime(df['Data Inicial'], dayfirst=True, errors='coerce').dt.date
    else: df['Data_Ini_DT'] = pd.NaT
    if 'Data Final' in df.columns: df['Data_Fim_DT'] = pd.to_datetime(df['Data Final'], dayfirst=True, errors='coerce').dt.date
    else: df['Data_Fim_DT'] = pd.NaT
    
    historico = []
    dias_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
    
    for d in pd.date_range(segunda, sexta, freq='D'):
        dia_alvo = d.date()
        
        mask_tot = (df['Data_Ini_DT'] <= dia_alvo) & (df['Data_Fim_DT'].isna() | (df['Data_Fim_DT'] >= segunda))
        tot = len(df[mask_tot])
        
        mask_fec = df['Data_Fim_DT'].notna() & (df['Data_Fim_DT'] >= segunda) & (df['Data_Fim_DT'] <= dia_alvo)
        fec = len(df[mask_fec])
        
        historico.append({'DiaStr': f"{dias_pt[d.dayofweek]} ({d.strftime('%d/%m')})", 'Total': tot, 'Fechadas': fec})

    df_hist = pd.DataFrame(historico)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_hist['DiaStr'], y=df_hist['Total'], mode='lines+markers+text', name='Total Mês', line=dict(color='red', width=3), text=df_hist['Total'], textposition='top center'))
    fig.add_trace(go.Scatter(x=df_hist['DiaStr'], y=df_hist['Fechadas'], mode='lines+markers+text', name='Fechadas Mês', line=dict(color='green', width=3), text=df_hist['Fechadas'], textposition='bottom center'))
    fig.update_layout(title=f"<b>Progresso ({segunda.strftime('%d/%m')} a {sexta.strftime('%d/%m')})</b>", template='plotly_white', legend=dict(orientation="h", y=1.1))
    
    return fig, {'Total_Tarefas': df_hist.iloc[-1]['Total'], 'Total_Fechadas': df_hist.iloc[-1]['Fechadas']}

def criar_grafico_historico_mensal(df_mes, periodo_selecionado_mes):
    if df_mes is None or df_mes.empty: 
        return go.Figure().update_layout(title="Sem dados para o mês", template='plotly_white'), None
        
    d1, d2 = periodo_selecionado_mes.start_time.date(), periodo_selecionado_mes.end_time.date()
    fim_range = pd.Timestamp.now().date() if (d2 > pd.Timestamp.now().date() and d1 <= pd.Timestamp.now().date()) else d2
        
    df = df_mes.copy()
    
    if 'Atividades Semanal' in df.columns and 'Sub-Lista / Grupo' in df.columns:
        mask_lista = df['Atividades Semanal'].astype(str).str.upper().str.contains('ATIVIDADES DA SEMANA', na=False)
        mask_grupo = df['Sub-Lista / Grupo'].astype(str).str.upper().str.contains('ATIVIDADES', na=False)
        df = df[mask_lista & mask_grupo].copy()
        
    if 'Data Inicial' in df.columns: df['Data_Ini_DT'] = pd.to_datetime(df['Data Inicial'], dayfirst=True, errors='coerce').dt.date
    else: df['Data_Ini_DT'] = pd.NaT
    if 'Data Final' in df.columns: df['Data_Fim_DT'] = pd.to_datetime(df['Data Final'], dayfirst=True, errors='coerce').dt.date
    else: df['Data_Fim_DT'] = pd.NaT
    
    historico = []
    for d in pd.date_range(d1, fim_range, freq='D'):
        dia_alvo = d.date()
        
        mask_tot = (df['Data_Ini_DT'] <= dia_alvo) & (df['Data_Fim_DT'].isna() | (df['Data_Fim_DT'] >= d1))
        tot = len(df[mask_tot])
        
        mask_fec = df['Data_Fim_DT'].notna() & (df['Data_Fim_DT'] >= d1) & (df['Data_Fim_DT'] <= dia_alvo)
        fec = len(df[mask_fec])
        
        historico.append({'Data': d, 'Total': tot, 'Fechadas': fec})

    df_hist = pd.DataFrame(historico)
    meses_full = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    nome_mes_pt = meses_full.get(d1.month, '').lower()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_hist['Data'], y=df_hist['Total'], name='Total Mês', mode='lines+markers', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=df_hist['Data'], y=df_hist['Fechadas'], name='Fechadas Mês', mode='lines+markers', line=dict(color='green')))
    fig.update_layout(title=f"<b>Evolução Diária ({nome_mes_pt})</b>", template='plotly_white', legend=dict(orientation="h", y=1.1))
    fig.update_xaxes(tickformat="%d/%m")
    
    return fig, {'Mensal_Tarefas': df_hist.iloc[-1]['Total'], 'Mensal_Fechadas': df_hist.iloc[-1]['Fechadas']}

def criar_grafico_produtividade_mensal(df):
    if df.empty: return go.Figure()
    agg = df.groupby(['Ano-Mês', 'Mes_Ano_Abrev']).agg(qtd=('ID', 'count')).reset_index().sort_values('Ano-Mês')
    fig = px.bar(agg, x='Mes_Ano_Abrev', y='qtd', text='qtd', title="<b>Produtividade Mensal</b>")
    fig.update_layout(template='plotly_white', margin=dict(l=50, r=50, t=40, b=40))
    return fig

def criar_grafico_principal(df):
    if df.empty: return go.Figure().update_layout(title="<b>Gráfico Principal</b>")
    
    ordem_dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    
    df_dia = df.groupby(['Ano-Mês', 'Mes_Ano_Abrev', 'Dia']).size().reset_index(name='Contagem')
    df_dia_total = df_dia.groupby('Dia')['Contagem'].sum().reset_index()
    
    if 'Semana do Mês' in df.columns:
        df['Semana do Mês'] = pd.to_numeric(df['Semana do Mês'], errors='coerce')
        
    df_semana = df.groupby(['Ano-Mês', 'Mes_Ano_Abrev', 'Semana do Mês']).size().reset_index(name='Contagem')
    df_semana_total = df_semana.groupby('Semana do Mês')['Contagem'].sum().reset_index()
    
    df_diasemana_full = df.groupby(['Ano-Mês', 'Mes_Ano_Abrev', 'Semana do Mês', 'Nome Dia Semana']).size().reset_index(name='Contagem')
    df_diasemana_total = df_diasemana_full.groupby('Nome Dia Semana')['Contagem'].sum().reindex(ordem_dias).fillna(0).reset_index()
    df_diasemana_total['Contagem'] = recortar_zeros_pontas(df_diasemana_total['Contagem'])
    df_diasemana_total = df_diasemana_total.dropna(subset=['Contagem'])
    
    mes_map = df[['Ano-Mês', 'Mes_Ano_Abrev']].drop_duplicates().sort_values('Ano-Mês')
    opcoes_meses = mes_map['Mes_Ano_Abrev'].tolist()

    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df_dia_total['Dia'], y=df_dia_total['Contagem'], name='Soma Dias', visible=True, mode='lines+markers+text', text=df_dia_total['Contagem'], textposition='top center', line=dict(color='royalblue', width=3))) 
    fig.add_trace(go.Scatter(x=df_semana_total['Semana do Mês'], y=df_semana_total['Contagem'], name='Soma Semanas', visible=False, mode='lines+markers+text', text=df_semana_total['Contagem'], textposition='top center', line=dict(color='royalblue', width=3))) 
    fig.add_trace(go.Scatter(x=df_diasemana_total['Nome Dia Semana'], y=df_diasemana_total['Contagem'], name='Soma Dia Semana', visible=False, mode='lines+markers+text', text=df_diasemana_total['Contagem'], textposition='top center', line=dict(color='royalblue', width=3))) 
    
    offset_dia = 3
    for mes in opcoes_meses:
        d = df_dia[df_dia['Mes_Ano_Abrev'] == mes].sort_values('Dia')
        d['Contagem'] = d['Contagem'].replace(0, np.nan)
        fig.add_trace(go.Scatter(x=d['Dia'], y=d['Contagem'], name=mes, visible=False, mode='lines+markers+text', text=d['Contagem'], textposition='top center'))
    count_dia = len(opcoes_meses)

    offset_semana = offset_dia + count_dia
    for mes in opcoes_meses:
        d = df_semana[df_semana['Mes_Ano_Abrev'] == mes].sort_values('Semana do Mês')
        d['Contagem'] = d['Contagem'].replace(0, np.nan)
        fig.add_trace(go.Scatter(x=d['Semana do Mês'], y=d['Contagem'], name=mes, visible=False, mode='lines+markers+text', text=d['Contagem'], textposition='top center'))
    count_semana = len(opcoes_meses)

    offset_diasemana = offset_semana + count_semana
    diasemana_trace_map = [] 
    for mes in opcoes_meses:
        d_mes = df_diasemana_full[df_diasemana_full['Mes_Ano_Abrev'] == mes].groupby('Nome Dia Semana')['Contagem'].sum().reindex(ordem_dias).fillna(0).reset_index()
        d_mes['Contagem'] = recortar_zeros_pontas(d_mes['Contagem'])
        d_mes = d_mes.dropna(subset=['Contagem'])
        fig.add_trace(go.Scatter(x=d_mes['Nome Dia Semana'], y=d_mes['Contagem'], name=f"{mes} Agregado", visible=False, mode='lines+markers+text', text=d_mes['Contagem'], textposition='top center'))
        
        semanas_do_mes = sorted(df_diasemana_full[df_diasemana_full['Mes_Ano_Abrev'] == mes]['Semana do Mês'].unique())
        for sem in semanas_do_mes:
            d_sem = df_diasemana_full[(df_diasemana_full['Mes_Ano_Abrev'] == mes) & (df_diasemana_full['Semana do Mês'] == sem)].set_index('Nome Dia Semana').reindex(ordem_dias).fillna(0).reset_index()
            d_sem['Contagem'] = recortar_zeros_pontas(d_sem['Contagem'])
            d_sem = d_sem.dropna(subset=['Contagem'])
            fig.add_trace(go.Scatter(x=d_sem['Nome Dia Semana'], y=d_sem['Contagem'], name=f"{mes} Sem {sem}", visible=False, mode='lines+markers+text', text=d_sem['Contagem'], textposition='top center'))
        diasemana_trace_map.append({'mes': mes, 'num_semanas': len(semanas_do_mes)})

    total_traces = len(fig.data)
    
    vis_total_agregado_dia = [False] * total_traces
    for i in range(count_dia): vis_total_agregado_dia[offset_dia + i] = True
    buttons_dia = [dict(label="Total Agregado", method="update", args=[{"visible": vis_total_agregado_dia}])]
    for i, mes in enumerate(opcoes_meses):
        vis = [False]*total_traces; vis[offset_dia + i] = True
        buttons_dia.append(dict(label=mes, method="update", args=[{"visible": vis}]))

    vis_total_agregado_semana = [False] * total_traces
    for i in range(count_semana): vis_total_agregado_semana[offset_semana + i] = True
    buttons_semana = [dict(label="Total Agregado", method="update", args=[{"visible": vis_total_agregado_semana}])]
    for i, mes in enumerate(opcoes_meses):
        vis = [False]*total_traces; vis[offset_semana + i] = True
        buttons_semana.append(dict(label=mes, method="update", args=[{"visible": vis}]))

    vis_total_agregado_diasemana = [False] * total_traces
    temp_idx = offset_diasemana
    for item in diasemana_trace_map:
        vis_total_agregado_diasemana[temp_idx] = True 
        temp_idx += 1 + item['num_semanas']
    buttons_diasemana = [dict(label="Total Agregado", method="update", args=[{"visible": vis_total_agregado_diasemana}])]
    
    current_idx = offset_diasemana
    for item in diasemana_trace_map:
        mes = item['mes']
        vis_mes_zoom = [False]*total_traces
        for k in range(item['num_semanas']): vis_mes_zoom[current_idx + 1 + k] = True
        buttons_diasemana.append(dict(label=f"{mes} Agregado", method="update", args=[{"visible": vis_mes_zoom}]))
        current_idx += 1 
        for s in range(item['num_semanas']):
            vis_sem = [False]*total_traces; vis_sem[current_idx] = True
            buttons_diasemana.append(dict(label=f"{mes} Semana {s+1}", method="update", args=[{"visible": vis_sem}]))
            current_idx += 1

    vis_init_dia = [False]*total_traces; vis_init_dia[0] = True
    vis_init_semana = [False]*total_traces; vis_init_semana[1] = True
    vis_init_diasemana = [False]*total_traces; vis_init_diasemana[2] = True

    fig.update_layout(
        title={'text': "<b>Gráfico Principal</b>", 'y': 0.97, 'x': 0.1, 'xanchor': 'center', 'yanchor': 'top'},
        height=432, 
        margin=dict(l=0, r=40, t=70, b=30), 
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.13, xanchor="right", x=1),
        updatemenus=[
            dict(type="buttons", direction="right", x=1.0, y=1.13, xanchor="right", yanchor="top", buttons=[
                dict(label="Dia do Mês", method="update", args=[{"visible": vis_init_dia}, {"updatemenus[1].buttons": buttons_dia, "xaxis.title": "Dia", "xaxis.type": "linear", "xaxis.categoryarray": None}]),
                dict(label="Semana do Mês", method="update", args=[{"visible": vis_init_semana}, {"updatemenus[1].buttons": buttons_semana, "xaxis.title": "Semana", "xaxis.type": "linear", "xaxis.categoryarray": None}]),
                dict(label="Dia da Semana", method="update", args=[{"visible": vis_init_diasemana}, {"updatemenus[1].buttons": buttons_diasemana, "xaxis.title": "Dia da Semana", "xaxis.type": "category", "xaxis.categoryorder": "array", "xaxis.categoryarray": ordem_dias}])
            ]),
            dict(direction="down", x=-0.01, y=1.13, xanchor="left", yanchor="top", showactive=True, buttons=buttons_dia)
        ],
        xaxis=dict(title="Tempo", showgrid=False, showline=True, linecolor='black'),
        yaxis=dict(title="Quantidade", showgrid=True, gridcolor='lightgray')
    )
    return fig

def criar_grafico_tarefas_funcionarios(df):
    if df.empty: return go.Figure()
    v = df['Encarregado'].value_counts().reset_index()
    v.columns = ['Encarregado', 'count']
    v['Encarregado'] = v['Encarregado'].apply(lambda x: f"{x.split()[0]} {x.split()[-1]}" if isinstance(x, str) and len(x.split()) > 1 else x)
    v = v.sort_values('count', ascending=True) 
    altura_dinamica = max(400, len(v) * 28)
    fig = px.bar(v, x='count', y='Encarregado', orientation='h', text='count', title="<b>Tarefas por Pessoa</b>", color='count', color_continuous_scale='Blues')
    fig.update_layout(template='plotly_white', height=altura_dinamica, margin=dict(l=150, r=20, t=60, b=20), yaxis=dict(title=None, tickfont=dict(size=12), dtick=1), xaxis=dict(title="Quantidade de Tarefas"))
    return fig

def criar_grafico_status_tarefas(df):
    if df.empty: return go.Figure().update_layout(title="<b>Distribuição por Status</b>")
    v = df['Status_Tarefa'].value_counts().reset_index()
    v.columns = ['Status', 'Contagem']
    fig = px.pie(v, names='Status', values='Contagem', title="<b>Distribuição por Status</b>", hole=0.4, color='Status', color_discrete_map={'Executado': 'royalblue', 'Aberto': 'firebrick', 'Desconhecido': 'gray'})
    fig.update_traces(textinfo='value+percent')
    return fig

def criar_grafico_crescimento_acumulado(df_plot, lista_encarregados, df_context=None):
    if df_plot.empty or not lista_encarregados: return go.Figure().update_layout(title="Sem dados ou nenhum encarregado selecionado", template='plotly_white')
    df_ex = df_plot[df_plot['Status_Tarefa'] == 'Executado'].copy()
    if df_ex.empty: return go.Figure().update_layout(title="Nenhuma tarefa executada no período", template='plotly_white')
    df_ex['Data'] = pd.to_datetime(df_ex['Data Final (aberta)']).dt.date
    d_min, d_max = df_ex['Data'].min(), df_ex['Data'].max()
    if pd.isna(d_min) or pd.isna(d_max): return go.Figure()
    idx = pd.date_range(d_min, d_max)

    fig = go.Figure()
    df_history = df_context if df_context is not None else df_plot
    start_dates = df_history.groupby('Encarregado')['Data de Entrada'].first() if 'Data de Entrada' in df_history.columns else pd.Series(pd.NaT)
    fallback_starts = df_history[df_history['Status_Tarefa'] == 'Executado'].groupby('Encarregado')['Data Final (aberta)'].min()
    end_dates = df_history.groupby('Encarregado')['Data de Saída'].first() if 'Data de Saída' in df_history.columns else pd.Series(pd.NaT)
    all_employees = set(df_history['Encarregado'].unique())
    active_counts_list = []
    
    for current_day_ts in idx:
        current_date, count_active = current_day_ts.date(), 0
        for enc in all_employees:
            dt_ent = start_dates.get(enc, pd.NaT)
            if pd.isna(dt_ent) or pd.isnull(dt_ent): 
                val = fallback_starts.get(enc, pd.NaT)
                if pd.notna(val): dt_ent = val.date() if isinstance(val, pd.Timestamp) else val
            elif isinstance(dt_ent, pd.Timestamp): dt_ent = dt_ent.date()

            dt_sai = end_dates.get(enc, pd.NaT)
            if isinstance(dt_sai, pd.Timestamp): dt_sai = dt_sai.date()
            if pd.notna(dt_ent) and current_date >= dt_ent:
                if pd.isna(dt_sai) or current_date <= dt_sai: count_active += 1
        active_counts_list.append(count_active)
            
    active_team_size = pd.Series(active_counts_list, index=idx).replace(0, 1)
    daily_total_tasks = df_ex.groupby('Data').size()
    daily_total_tasks.index = pd.to_datetime(daily_total_tasks.index)
    daily_total_tasks = daily_total_tasks.reindex(idx, fill_value=0)
    
    daily_avg_productivity = daily_total_tasks / active_team_size
    s_media_acumulada = daily_avg_productivity.cumsum()
    
    fig.add_trace(go.Scatter(x=s_media_acumulada.index, y=s_media_acumulada.values, name='Média Per Capita Acumulada', line=dict(color='gray', width=4, dash='dot'), mode='lines', hovertemplate='Data: %{x}<br>Média Acumulada: %{y:.1f}<br>Equipe Ativa: %{customdata} pessoas<extra></extra>', customdata=active_team_size))
    
    colors = px.colors.qualitative.Plotly
    for i, nome in enumerate(lista_encarregados):
        df_u = df_ex[df_ex['Encarregado'] == nome]
        if df_u.empty: continue
        s_u = df_u.groupby('Data').size()
        s_u.index = pd.to_datetime(s_u.index)
        s_u = s_u.reindex(idx, fill_value=0).cumsum()
        c = colors[i % len(colors)]
        fig.add_trace(go.Scatter(x=s_u.index, y=s_u.values, name=nome, mode='lines+markers', line=dict(color=c, width=2)))
        
    fig.update_layout(title="<b>Curva de Produtividade Acumulada (Entregas)</b>", template='plotly_white', xaxis=dict(title="Tempo"), yaxis=dict(title="Tarefas Entregues"), hovermode="x unified")
    return fig

def criar_grafico_pontuacao_individual(df, nomes, d_ini, d_fim):
    if df is None or df.empty: return go.Figure(), pd.DataFrame()
    df_c = df.copy()
    cols_validas = []
    for c in df_c.columns:
        if str(c).lower() != 'encarregado':
            dt = converter_data_robusta(pd.Series([c]))
            if pd.notna(dt[0]) and d_ini <= dt[0].date() <= d_fim:
                cols_validas.append(c); df_c[c] = pd.to_numeric(df_c[c], errors='coerce').fillna(0)
    if not cols_validas: return go.Figure().update_layout(title="Sem dados período"), pd.DataFrame()
    df_c['Total'] = df_c[cols_validas].sum(axis=1)
    df_f = df_c[df_c['Encarregado'].isin(nomes)].sort_values('Total', ascending=True)
    fig = px.bar(df_f, x='Total', y='Encarregado', orientation='h', text='Total', title="<b>Pontuação Individual</b>", color='Total', color_continuous_scale='Viridis')
    fig.update_layout(template='plotly_white', yaxis_title=None)
    return fig, df_f[['Encarregado', 'Total'] + cols_validas].sort_values('Total', ascending=False)

def criar_grafico_pontuacao_lideres(df_mapa, df_pt, nomes, d_ini, d_fim):
    if df_mapa is None or df_pt is None: return go.Figure(), pd.DataFrame(), pd.DataFrame()
    df_c = df_pt.copy()
    cols_validas = []
    for c in df_c.columns:
        if str(c).lower() != 'encarregado':
            dt = converter_data_robusta(pd.Series([c]))
            if pd.notna(dt[0]) and d_ini <= dt[0].date() <= d_fim:
                cols_validas.append(c); df_c[c] = pd.to_numeric(df_c[c], errors='coerce').fillna(0)
    if not cols_validas: return go.Figure().update_layout(title="Sem dados período"), pd.DataFrame(), pd.DataFrame()
    df_c['Pontos'] = df_c[cols_validas].sum(axis=1)
    df_mapa['Lider'] = df_mapa['Lider'].astype(str).str.strip()
    df_mapa['Liderado'] = df_mapa['Liderado'].astype(str).str.strip()
    df_c['Encarregado'] = df_c['Encarregado'].astype(str).str.strip()
    merge = pd.merge(df_mapa, df_c[['Encarregado', 'Pontos']], left_on='Liderado', right_on='Encarregado')
    rank = merge.groupby('Lider')['Pontos'].sum().reset_index()
    rank = rank[rank['Lider'].isin(nomes)].sort_values('Pontos', ascending=True)
    fig = px.bar(rank, x='Pontos', y='Lider', orientation='h', text='Pontos', title="<b>Pontuação Liderança</b>", color='Pontos', color_continuous_scale='Plasma')
    fig.update_layout(template='plotly_white', yaxis_title=None)
    return fig, rank.sort_values('Pontos', ascending=False), df_c

def criar_grafico_pontuacao_combinada(df_ind, df_lid, df_mapa, nomes, d_ini, d_fim):
    fig_i, df_i = criar_grafico_pontuacao_individual(df_ind, df_ind['Encarregado'].unique() if df_ind is not None else [], d_ini, d_fim)
    fig_l, df_l, _ = criar_grafico_pontuacao_lideres(df_mapa, df_lid, df_mapa['Lider'].unique() if df_mapa is not None else [], d_ini, d_fim)
    res = pd.DataFrame(columns=['Pessoa', 'Total'])
    if not df_i.empty: 
        temp = df_i[['Encarregado', 'Total']].rename(columns={'Encarregado':'Pessoa', 'Total':'Ind'})
        res = pd.merge(res, temp, on='Pessoa', how='outer')
    if not df_l.empty:
        temp = df_l[['Lider', 'Pontos']].rename(columns={'Lider':'Pessoa', 'Pontos':'Lid'})
        res = pd.merge(res, temp, on='Pessoa', how='outer')
    res = res.fillna(0)
    res['Final'] = res.get('Ind', 0) + res.get('Lid', 0)
    res = res[res['Pessoa'].isin(nomes)].sort_values('Final', ascending=True)
    if res.empty: return go.Figure()
    fig = px.bar(res, x='Final', y='Pessoa', orientation='h', text='Final', title="<b>Pontuação Total Combinada</b>", color='Final', color_continuous_scale='Viridis')
    fig.update_layout(template='plotly_white', yaxis_title=None)
    return fig