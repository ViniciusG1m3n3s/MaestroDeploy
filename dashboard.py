import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from diario import diario  # Importa o diário de bordo
    
# Função para carregar os dados do Excel do usuário logado
def load_data(usuario):
    excel_file = f'dados_acumulados_{usuario}.xlsx'  # Nome do arquivo específico do usuário
    if os.path.exists(excel_file):
        df_total = pd.read_excel(excel_file, engine='openpyxl')
    else:
        df_total = pd.DataFrame(columns=['NÚMERO DO PROTOCOLO', 'USUÁRIO QUE CONCLUIU A TAREFA', 'SITUAÇÃO DA TAREFA', 'TEMPO MÉDIO OPERACIONAL', 'DATA DE INÍCIO DA TAREFA'])
    return df_total

# Função para salvar os dados no Excel do usuário logado
def save_data(df, usuario):
    excel_file = f'dados_acumulados_{usuario}.xlsx'  # Nome do arquivo específico do usuário
    df['TEMPO MÉDIO OPERACIONAL'] = df['TEMPO MÉDIO OPERACIONAL'].astype(str)
    with pd.ExcelWriter(excel_file, engine='openpyxl', mode='w') as writer:
        df.to_excel(writer, index=False)

# Função para garantir que a coluna 'TEMPO MÉDIO OPERACIONAL' esteja no formato timedelta para cálculos
def convert_to_timedelta_for_calculations(df):
    df['TEMPO MÉDIO OPERACIONAL'] = pd.to_timedelta(df['TEMPO MÉDIO OPERACIONAL'], errors='coerce')
    return df

# Função para garantir que a coluna 'DATA CRIAÇÃO DA TAREFA' esteja no formato de datetime
def convert_to_datetime_for_calculations(df):
    df['DATA DE INÍCIO DA TAREFA'] = pd.to_datetime(df['DATA DE INÍCIO DA TAREFA'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    return df

# Função para formatar timedelta no formato HH:MM:SS
def format_timedelta(td):
    if pd.isnull(td):
        return "0 min"
    total_seconds = int(td.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes} min {seconds}s"

# Função para calcular o TMO por dia
def calcular_tmo_por_dia(df):
    df['Dia'] = pd.to_datetime(df['DATA DE INÍCIO DA TAREFA']).dt.date
    df_finalizados = df[df['SITUAÇÃO DA TAREFA'].isin(['Finalizada', 'Cancelada'])].copy()
    
    # Agrupando por dia
    df_tmo = df_finalizados.groupby('Dia').agg(
        Tempo_Total=('TEMPO MÉDIO OPERACIONAL', 'sum'),  # Soma total do tempo
        Total_Finalizados_Cancelados=('SITUAÇÃO DA TAREFA', 'count')  # Total de tarefas finalizadas ou canceladas
    ).reset_index()

    # Calcula o TMO (Tempo Médio Operacional)
    df_tmo['TMO'] = df_tmo['Tempo_Total'] / df_tmo['Total_Finalizados_Cancelados']
    
    # Formata o tempo médio no formato HH:MM:SS
    df_tmo['TMO'] = df_tmo['TMO'].apply(format_timedelta)
    return df_tmo[['Dia', 'TMO']]

def calcular_tmo_por_dia_geral(df):
    # Certifica-se de que a coluna de data está no formato correto
    df['Dia'] = pd.to_datetime(df['DATA DE INÍCIO DA TAREFA']).dt.date

    # Filtra tarefas finalizadas ou canceladas, pois estas são relevantes para o cálculo do TMO
    df_finalizados = df[df['SITUAÇÃO DA TAREFA'].isin(['Finalizada', 'Cancelada'])].copy()
    
    # Agrupamento por dia para calcular o tempo médio diário
    df_tmo = df_finalizados.groupby('Dia').agg(
        Tempo_Total=('TEMPO MÉDIO OPERACIONAL', 'sum'),  # Soma total do tempo por dia
        Total_Finalizados_Cancelados=('SITUAÇÃO DA TAREFA', 'count')  # Total de tarefas finalizadas/canceladas por dia
    ).reset_index()

    # Calcula o TMO (Tempo Médio Operacional) diário
    df_tmo['TMO'] = df_tmo['Tempo_Total'] / df_tmo['Total_Finalizados_Cancelados']
    
    # Remove valores nulos e formata o tempo médio para o gráfico
    df_tmo['TMO'] = df_tmo['TMO'].fillna(pd.Timedelta(seconds=0))  # Preenche com zero se houver NaN
    df_tmo['TMO_Formatado'] = df_tmo['TMO'].apply(format_timedelta)  # Formata para exibição
    
    return df_tmo[['Dia', 'TMO', 'TMO_Formatado']]

def calcular_produtividade_diaria(df):
    # Garante que a coluna 'Próximo' esteja em formato de data
    df['Dia'] = df['DATA DE INÍCIO DA TAREFA'].dt.date

    # Agrupa e soma os status para calcular a produtividade
    df_produtividade = df.groupby('Dia').agg(
        Finalizado=('SITUAÇÃO DA TAREFA', lambda x: x[x == 'Finalizada'].count()),
        Cancelada=('SITUAÇÃO DA TAREFA', lambda x: x[x == 'Cancelada'].count())
    ).reset_index()

    # Calcula a produtividade total
    df_produtividade['Produtividade'] = + df_produtividade['Finalizado'] + df_produtividade['Cancelada']
    return df_produtividade

# Função principal da dashboard
def dashboard():
    st.title("Dashboard de Produtividade")
    
    # Carregar dados acumulados do arquivo Excel do usuário logado
    usuario_logado = st.session_state.usuario_logado  # Obtém o usuário logado
    df_total = load_data(usuario_logado)  # Carrega dados específicos do usuário

    st.sidebar.image("https://finchsolucoes.com.br/img/eb28739f-bef7-4366-9a17-6d629cf5e0d9.png", width=100)
    st.sidebar.text('')

    # Sidebar para navegação
    st.sidebar.header("Navegação")
    opcao_selecionada = st.sidebar.selectbox("Escolha uma visão", ["Visão Geral", "Métricas Individuais", "Diário de Bordo"])

    # Upload de planilha na sidebar
    uploaded_file = st.sidebar.file_uploader("Carregar nova planilha", type=["xlsx"])

    if uploaded_file is not None:
        df_new = pd.read_excel(uploaded_file)
        df_total = pd.concat([df_total, df_new], ignore_index=True)
        save_data(df_total, usuario_logado)  # Atualiza a planilha específica do usuário
        st.sidebar.success(f'Arquivo "{uploaded_file.name}" carregado e processado com sucesso!')

    # Converte para timedelta e datetime apenas para operações temporárias
    df_total = convert_to_timedelta_for_calculations(df_total)
    df_total = convert_to_datetime_for_calculations(df_total)

    custom_colors = ['#ff571c', '#7f2b0e', '#4c1908']

    # Função para calcular TMO por dia
    df_tmo = calcular_tmo_por_dia(df_total)

    def calcular_tmo_por_analista(df):
        df_finalizados = df[df['SITUAÇÃO DA TAREFA'].isin(['Finalizada', 'Cancelada'])].copy()

        # Agrupando por analista
        df_tmo_analista = df_finalizados.groupby('USUÁRIO QUE CONCLUIU A TAREFA').agg(
            Tempo_Total=('TEMPO MÉDIO OPERACIONAL', 'sum'),  # Soma total do tempo por analista
            Total_Tarefas=('SITUAÇÃO DA TAREFA', 'count')  # Total de tarefas finalizadas ou canceladas por analista
        ).reset_index()

        # Calcula o TMO (Tempo Médio Operacional) como média
        df_tmo_analista['TMO'] = df_tmo_analista['Tempo_Total'] / df_tmo_analista['Total_Tarefas']

        # Formata o tempo médio no formato de minutos e segundos
        df_tmo_analista['TMO_Formatado'] = df_tmo_analista['TMO'].apply(format_timedelta)
        return df_tmo_analista[['USUÁRIO QUE CONCLUIU A TAREFA', 'TMO_Formatado', 'TMO']]
    

    # Verifica qual opção foi escolhida no dropdown
    if opcao_selecionada == "Visão Geral":
        st.header("Visão Geral")

            # Adiciona filtros de datas 
        min_date = df_total['DATA DE INÍCIO DA TAREFA'].min().date() if not df_total.empty else datetime.today().date()
        max_date = df_total['DATA DE INÍCIO DA TAREFA'].max().date() if not df_total.empty else datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            data_inicial = st.date_input("Data Inicial", min_date)
        with col2:
            data_final = st.date_input("Data Final", max_date)

        if data_inicial > data_final:
            st.sidebar.error("A data inicial não pode ser posterior à data final!")

        df_total = df_total[(df_total['DATA DE INÍCIO DA TAREFA'].dt.date >= data_inicial) & (df_total['DATA DE INÍCIO DA TAREFA'].dt.date <= data_final)]

        total_finalizados = len(df_total[df_total['SITUAÇÃO DA TAREFA'] == 'Finalizada'])
        total_reclass = len(df_total[df_total['SITUAÇÃO DA TAREFA'] == 'Cancelada'])
        # Verifique se o denominador não é zero
        if (total_finalizados + total_reclass) > 0:
            # Se houver cadastros finalizados ou reclassificados, calcula o tempo médio
            tempo_medio = (df_total[df_total['SITUAÇÃO DA TAREFA'] == 'Finalizada']['TEMPO MÉDIO OPERACIONAL'].sum() + 
                        df_total[df_total['SITUAÇÃO DA TAREFA'] == 'Cancelada']['TEMPO MÉDIO OPERACIONAL'].sum()) / (total_finalizados + total_reclass)
        else:
            # Se não houver cadastros finalizados ou reclassificados, define o tempo médio como zero ou outro valor padrão
            tempo_medio = pd.Timedelta(0)  # ou "0 min"

        # with st.container(border=True):
        #     col1, col2, col3 = st.columns(3)
        #     col1.metric("Total de Cadastros", total_finalizados)
        #     col2.metric("Reclassificações", total_reclass)
        #     col3.metric("Tempo Médio por Cadastro", format_timedelta(tempo_medio))

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            with st.container(border=True):
                total_geral = total_finalizados + total_reclass
                st.metric("Total Geral", total_geral)

        with col2:
            with st.container(border=True):
                st.metric("Total Tarefas Finalizadas", total_finalizados)

        with col3:
            with st.container(border=True):
                st.metric("Total Tarefas Canceladas", total_reclass)

        with col4:
            with st.container(border=True):
                st.metric("Tempo Médio por Cadastro", format_timedelta(tempo_medio))

        df_produtividade = calcular_produtividade_diaria(df_total)

        # melhor_dia = df_produtividade.loc[df_produtividade['Produtividade'].idxmax()]
        # with col1:
        #     st.success("Melhor Dia de Produtividade: " + str(melhor_dia['Dia']) + " - " + str(melhor_dia['Produtividade']) + " Cadastros")

        # col1, col2, col3 = st.columns(3)
        # with col1:
        #     st.success("Total de Cadastros: " + str(total_finalizados))

        # Gráfico de linhas de produtividade
        col1, col2 = st.columns(2)
        with col1:      
            with st.container(border=True):
                st.subheader("Produtividade Diária")
                fig_produtividade = px.line(
                    df_produtividade,
                    x='Dia',
                    y='Produtividade',
                    title='Produtividade Diária',
                    color_discrete_sequence=custom_colors,
                    labels={'Produtividade': 'Total de Cadastros'},
                    line_shape='linear',
                    markers=True
                )
                fig_produtividade.update_traces(
                    hovertemplate='Dia = %{x|%d/%m/%Y}<br>Produtividade = %{y}'
                )
                st.plotly_chart(fig_produtividade)

        with col2:
            with st.container(border=True):
                st.subheader("TMO por Dia da Equipe")
                df_tmo = calcular_tmo_por_dia_geral(df_total)
                fig_tmo = px.line(
                    df_tmo,
                    x='Dia',
                    y=df_tmo['TMO'].dt.total_seconds() / 60,  # Converte TMO para minutos
                    title='TMO por Dia da Equipe (em minutos)',
                    labels={'y': 'Tempo Médio Operacional (min)', 'Dia': 'Data'},
                    line_shape='linear',
                    markers=True,
                    color_discrete_sequence=custom_colors
                )
                fig_tmo.update_traces(
                    hovertemplate='Data = %{x|%d/%m/%Y}<br>TMO = %{text}',
                    text=df_tmo['TMO_Formatado']
                )
                st.plotly_chart(fig_tmo)

        # Gráfico de pizza para o status
        with st.container(border=True):
            st.subheader("Status das Tarefas")
            fig_status = px.pie(
                names=['Finalizada', 'Cancelado'],
                values=[total_finalizados, total_reclass],
                title='Distribuição de Status',
                color_discrete_sequence=custom_colors
            )
            fig_status.update_traces(
                hovertemplate='Tarefas %{label} = %{value}<extra></extra>',
            )
            st.plotly_chart(fig_status)

        with st.container(border=True):
            # Calcula o TMO por analista e exibe o gráfico
            df_tmo_analista = calcular_tmo_por_analista(df_total)
            
            # Gráfico de barras de TMO por analista em minutos
            st.subheader("Tempo Médio de Operação (TMO) por Analista")
            fig_tmo_analista = px.bar(
                df_tmo_analista,
                x='USUÁRIO QUE CONCLUIU A TAREFA',
                y=df_tmo_analista['TMO'].dt.total_seconds() / 60,  # TMO em minutos
                title='TMO por Analista (em minutos e segundos)',
                labels={'y': 'TMO (min)', 'USUÁRIO QUE CONCLUIU A TAREFA': 'Analista'},
                text=df_tmo_analista['TMO_Formatado'],
                color_discrete_sequence=custom_colors
            )
            fig_tmo_analista.update_traces(
                textposition='outside',  # Exibe o tempo formatado fora das barras
                hovertemplate='Analista = %{x}<br>TMO = %{text}<extra></extra>',
                text=df_tmo_analista['TMO_Formatado']
            )
            st.plotly_chart(fig_tmo_analista)

        with st.container(border=True):
            # Gráfico de ranking dinâmico
            st.subheader("Ranking Dinâmico")
            df_ranking = df_total.groupby('USUÁRIO QUE CONCLUIU A TAREFA').agg(
                Finalizado=('SITUAÇÃO DA TAREFA', lambda x: x[x == 'Finalizada'].count()),
                Cancelado=('SITUAÇÃO DA TAREFA', lambda x: x[x == 'Cancelada'].count())
            ).reset_index()
            df_ranking['Total'] = df_ranking['Finalizado'] + df_ranking['Cancelado']
            df_ranking = df_ranking.sort_values(by='Total', ascending=False).reset_index(drop=True)
            df_ranking.index += 1
            df_ranking.index.name = 'Posição'
            df_ranking = df_ranking.rename(columns={'USUÁRIO QUE CONCLUIU A TAREFA': 'Usuário', 'Finalizado': 'Finalizado', 'Cancelada': 'Cancelada'})
            st.dataframe(df_ranking.style.format({'Finalizado': '{:.0f}', 'Cancelado': '{:.0f}'}), width=1080)

    elif opcao_selecionada == "Diário de Bordo":
        diario()

    elif opcao_selecionada == "Métricas Individuais":
        st.header("Métricas Individuais")
        # Adiciona filtros de datas 
        st.subheader("Filtro por Data")
        min_date = df_total['DATA DE INÍCIO DA TAREFA'].min().date() if not df_total.empty else datetime.today().date()
        max_date = df_total['DATA DE INÍCIO DA TAREFA'].max().date() if not df_total.empty else datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            data_inicial = st.date_input("Data Inicial", min_date)
        with col2:
            data_final = st.date_input("Data Final", max_date)

        if data_inicial > data_final:
            st.error("A data inicial não pode ser posterior à data final!")

        df_total = df_total[(df_total['DATA DE INÍCIO DA TAREFA'].dt.date >= data_inicial) & (df_total['DATA DE INÍCIO DA TAREFA'].dt.date <= data_final)]
        analista_selecionado = st.selectbox('Selecione o analista', df_total['USUÁRIO QUE CONCLUIU A TAREFA'].unique())
        df_analista = df_total[df_total['USUÁRIO QUE CONCLUIU A TAREFA'] == analista_selecionado].copy()

        total_geral_analista = len(df_analista[(df_analista['SITUAÇÃO DA TAREFA'] == 'Finalizada') | (df_analista['SITUAÇÃO DA TAREFA'] == 'Cancelada')])
        total_finalizados_analista = len(df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Finalizada'])
        total_reclass_analista = len(df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Cancelada'])
        # Calcula o TMO, quantidade de finalizados e reclassificações apenas para o analista especifico
        total_finalizados = len(df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Finalizada'])
        total_reclass = len(df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Cancelada'])
        # Verifique se o denominador não é zero
        if (total_finalizados + total_reclass) > 0:
            # Se houver cadastros finalizados ou reclassificados, calcula o tempo médio
            tempo_medio_analista = (df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Finalizada']['TEMPO MÉDIO OPERACIONAL'].sum() + 
                        df_analista[df_analista['SITUAÇÃO DA TAREFA'] == 'Cancelada']['TEMPO MÉDIO OPERACIONAL'].sum()) / (total_finalizados + total_reclass)
        else:
            # Se não houver cadastros finalizados ou reclassificados, define o tempo médio como zero ou outro valor padrão
            tempo_medio_analista = pd.Timedelta(0)  # ou "0 min"

        tmo_equipe = df_total[df_total['SITUAÇÃO DA TAREFA'] == 'Finalizada']['TEMPO MÉDIO OPERACIONAL'].mean()
        
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            with st.container(border=True):
                st.metric("Total Geral", total_geral_analista)

        with col2:
            with st.container(border=True):
                st.metric("Tarefas Finalizadas", total_finalizados_analista)

        with col3:
            with st.container(border=True):
                st.metric("Tarefas Canceladas", total_reclass_analista)

        with col4:
            with st.container(border=True):
                if tempo_medio_analista is not None and tmo_equipe is not None:
                    if tempo_medio_analista <= tmo_equipe:
                        st.metric(f"Tempo Médio por Cadastro", f"{format_timedelta(tempo_medio_analista)} {''}")
                    else:
                        st.metric(f"Tempo Médio por Cadastro", f"{format_timedelta(tempo_medio_analista)} {''}")
                        st.toast("Atenção! O tempo médio por cadastro é maior do que o TMO da equipe", icon="⚠️")
                else:
                    st.metric(f"Tempo Médio por Cadastro", 'Nenhum dado encontrado')

        with st.container(border=True):
            st.subheader(f"Tarefas Realizadas por {analista_selecionado}")
            if 'TAREFA' in df_analista.columns:
                carteiras_analista = df_analista['TAREFA'].dropna().value_counts().reset_index()
                carteiras_analista.columns = ['TAREFA', 'Quantidade']
                carteiras_analista = carteiras_analista.sort_values(by='Quantidade', ascending=False).reset_index(drop=True)
                carteiras_analista = carteiras_analista.rename(columns={'TAREFA': 'Tarefa', 'Quantidade': 'Quantidade'})
                # Ajuste aqui para aplicar hide_index na função st.dataframe
                st.dataframe(carteiras_analista.style.format({'Quantidade': '{:.0f}'}), hide_index=True, width=1080)
            else:
                st.write("A coluna 'TAREFA' não foi encontrada no dataframe.")
                carteiras_analista = pd.DataFrame({'Tarefa': [], 'Quantidade': []})
                st.dataframe(carteiras_analista.style.format({'Quantidade': '{:.0f}'}), hide_index=True, width=1080)

        # Gráficos de pizza lado a lado
        col1, col2 = st.columns(2)
        
        # Gráfico de pizza para o status do analista selecionado
        with col1:
            with st.container(border=True):
                st.subheader(f"Distribuição de Status de {analista_selecionado}")
                fig_status_analista = px.pie(
                    names=['Finalizado', 'Reclassificado'],
                    values=[total_finalizados_analista, total_reclass_analista],
                    title=f'Distribuição de Status - {analista_selecionado}',
                    color_discrete_sequence=custom_colors
                )
                
                fig_status_analista.update_traces(
                    hovertemplate='Tarefas %{label} = %{value}<extra></extra>',
                )

                fig_status_analista.update_layout(
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.1,
                        xanchor="center",
                        x=0.5
                    )
                )

                st.plotly_chart(fig_status_analista)

        # Gráfico de pizza para as tarefas feitas pelo analista
        with col2:
            with st.container(border=True):
                st.subheader(f"Tarefas Realizadas por {analista_selecionado}")
                
                if 'TAREFA' in df_analista.columns:
                    tarefas_feitas_analista = df_analista['TAREFA'].dropna().value_counts().reset_index()
                    tarefas_feitas_analista.columns = ['Tarefa', 'Quantidade']

                    fig_tarefas_feitas_analista = px.pie(
                        names=tarefas_feitas_analista['Tarefa'],
                        values=tarefas_feitas_analista['Quantidade'],
                        title=f'Tarefas Feitas - {analista_selecionado}',
                        color_discrete_sequence=custom_colors
                    )

                    fig_tarefas_feitas_analista.update_traces(
                        hovertemplate='Tarefas %{label} = %{value}<extra></extra>',
                    )

                    fig_tarefas_feitas_analista.update_layout(
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.1,
                            xanchor="center",
                            x=0.5
                        )
                    )

                    st.plotly_chart(fig_tarefas_feitas_analista)
                else:
                    st.write("A coluna 'TAREFA' não foi encontrada no dataframe.")

        # Gráfico de barras para o tempo médio do analista por dia
        with st.container(border=True):
            st.subheader(f"Tempo Médio por Dia - {analista_selecionado}")
            df_tmo_analista = calcular_tmo_por_dia(df_analista)

            # Converte a coluna "TMO" para minutos e segundos
            df_tmo_analista['TMO_segundos'] = df_tmo_analista['TMO'].apply(lambda x: int(x.split(' min')[0]) * 60 + int(x.split('s')[0].split(' min')[1]))
            df_tmo_analista['TMO_minutos'] = df_tmo_analista['TMO_segundos'] / 60

            # Cria o gráfico de barras
            fig_tmo_analista = px.bar(
                df_tmo_analista, x='Dia', 
                y='TMO_minutos', 
                title=f'Tempo Médio por Dia - {analista_selecionado}',
                labels={'y': 'TMO (min)', 'Dia': 'Dia'},
                text=df_tmo_analista['TMO'],  # Exibe o tempo formatado fora das barras
                color_discrete_sequence=custom_colors
            )
            fig_tmo_analista.update_traces(
                hovertemplate='Data = %{x|%d/%m/%Y}<br>TMO = %{text}',
                text=df_tmo_analista['TMO']  # Exibe o tempo formatado fora das barras
            )
            st.plotly_chart(fig_tmo_analista)

        # st.write(df_tmo_analista)

        # # Tabela de pontos de atenção
        # st.subheader("Pontos de Atenção")
        # pontos_de_atencao_analista = get_points_of_attention(df_analista)
        # if not pontos_de_atencao_analista.empty:
        #     st.write(pontos_de_atencao_analista[['Protocolo', 'Tempo de Análise', 'Próximo']].assign(
        #         **{'Tempo de Análise': pontos_de_atencao_analista['Tempo de Análise'].apply(format_timedelta)}
        #     ).to_html(index=False, justify='left'), unsafe_allow_html=True)
        # else:
        #     st.write("Nenhum ponto de atenção identificado para este analista.")    

    # # Botão para salvar a planilha atualizada
    # if st.sidebar.button("Salvar Dados"):
    #     save_data(df_total, usuario_logado)  # Salva dados específicos do usuário
    #     st.sidebar.success("Dados salvos com sucesso!")

    if st.sidebar.button("Logout"):
        st.session_state.logado = False
        st.session_state.usuario_logado = None
        st.sidebar.success("Desconectado com sucesso!")
        st.rerun()  # Volta para a tela de login

# Para que a função dashboard seja chamada no arquivo principal
if __name__ == "__main__":
    dashboard()