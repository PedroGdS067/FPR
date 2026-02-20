import streamlit as st
import pandas as pd
import time
import backend
import io

# Configuração da Página
st.set_page_config(page_title="FPR Consórcios", page_icon="💰", layout="wide")

# =========================================================================
# ESTILOS GLOBAIS (CSS PREMIUM - ADAPTÁVEL AO TEMA CLARO/ESCURO)
# =========================================================================
st.markdown("""
<style>
    /* 1. Estilização dos Cards de Métricas */
    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.1) !important; /* Fundo translúcido sutil */
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 2. Container das Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        padding-bottom: 10px;
    }
    
    /* 3. Abas (Botões inativos) */
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: rgba(128, 128, 128, 0.15) !important; /* Destaque translúcido universal */
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        border: none;
    }
    
    /* 4. Aba Selecionada (Destaque Primário) */
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b !important; /* Vermelho padrão Streamlit */
        color: white !important;
    }
    
    /* Remove a linha nativa debaixo das abas */
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    
    /* 5. Cartão de Perfil na Barra Lateral */
    .sidebar-profile {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# TELA DE LOGIN
# =========================================================================
def verificar_login(u, s):
    df = backend.carregar_usuarios_df()
    m = df[df['username'] == u.strip()]
    if not m.empty:
        if m.iloc[0]['password_hash'] == backend.gerar_hash(s): 
            return True, m.iloc[0]
    return False, None

def tela_login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1]) # Coluna central levemente mais larga
    
    with c2:
        st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>FPR Consórcios</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; margin-bottom: 30px;'>Acesso Restrito ao Sistema de Gestão</p>", unsafe_allow_html=True)
        
        with st.form("l", clear_on_submit=False):
            u = st.text_input("👤 Usuário")
            s = st.text_input("🔒 Senha", type="password")
            
            st.write("") # Espaçamento
            if st.form_submit_button("🚀 Entrar no Sistema", type="primary", use_container_width=True):
                if u and s:
                    ok, d = verificar_login(u, s)
                    if ok:
                        st.session_state.update({
                            'logado': True, 
                            'usuario': u, 
                            'tipo_acesso': d['tipo_acesso'], 
                            'nome': d['nome_completo'], 
                            'id_usuario': str(d['id_usuario']).replace('.0','')
                        })
                        st.success("Autenticado com sucesso! Carregando...")
                        time.sleep(0.8)
                        st.rerun()
                    else: 
                        st.error("❌ Usuário ou senha inválidos.")
                else:
                    st.warning("Preencha todos os campos.")


# =========================================================================
# FUNÇÃO PRINCIPAL E SIDEBAR
# =========================================================================
def main():
    # --- SIDEBAR (BARRA LATERAL) ---
    with st.sidebar:
        # Cartão de Perfil Moderno (Adaptável ao Tema)
        st.markdown(f"""
        <div class="sidebar-profile">
            <h3 style='margin-bottom: 0px;'>👤 {st.session_state['nome']}</h3>
            <p style='font-size: 14px; margin-top: 5px; margin-bottom: 0px;'>Cargo: <b>{st.session_state['tipo_acesso']}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔐 Alterar Minha Senha", expanded=False):
            with st.form("form_minha_senha", clear_on_submit=True):
                s1 = st.text_input("Nova Senha", type="password")
                s2 = st.text_input("Confirmar Senha", type="password")
                if st.form_submit_button("Atualizar", use_container_width=True):
                    if s1 and s1 == s2: 
                        ok, m = backend.alterar_senha_usuario(st.session_state['id_usuario'], s1)
                        if ok: st.success(m)
                        else: st.error(m)
                    else: 
                        st.error("Senhas não conferem.")
        
        st.divider()
        if st.button("🚪 Sair do Sistema", use_container_width=True): 
            st.session_state['logado'] = False
            st.rerun()

    # --- TÍTULO DO APP ---
    st.title("💰 Sistema de Gestão Financeira e Comissões")
    st.write("") # Espaçamento
    
    # Carrega DF e garante a estrutura mesmo se vazio
    df = backend.carregar_dados()
    if df.empty:
        cols = ['ID_Lancamento','ID_Vendedor','ID_Gerente','Data_Previsao','Status_Recebimento','Valor_Cliente','Receber_Administradora','Liquido_Caixa','Status_Pgto_Cliente','Cliente','Vendedor','Gerente','Pagar_Vendedor','Pagar_Gerente','Administradora','Status_Pgto_Vendedor','Status_Pgto_Gerente']
        df = pd.DataFrame(columns=cols)

    # =========================================================================
    # CONFIGURAÇÃO DE ACESSO ÀS ABAS (DINÂMICO)
    # =========================================================================
    
    # Lembrete: Se você implementar a "🕵️ Auditoria" que criamos no backend.py, basta adicionar:
    # "🕵️ Auditoria": ['Master'] aqui embaixo!
    
    PERMISSOES = {
        "📊 Dashboard":         ['Master', 'Administrativo', 'Financeiro', 'Gerente', 'Vendedor'],
        "📥 Entuba":            ['Master', 'Administrativo'],
        "🏦 Conciliação":       ['Master', 'Administrativo'], 
        "❌ Cancelamentos":     ['Master', 'Administrativo'], 
        "👥 Usuários":          ['Master', 'Administrativo'],
        "⚙️ Regras":            ['Master', 'Administrativo'],
        "📇 Clientes":          ['Master', 'Administrativo', 'Financeiro', 'Gerente', 'Vendedor'],
        "🛠️ Ajustes":           ['Master', 'Administrativo'],
        "📄 Parcelas Clientes": ['Master', 'Administrativo', 'Financeiro'],
        "💸 Comissões":         ['Master', 'Administrativo', 'Financeiro']
    }

    cargo_atual = st.session_state['tipo_acesso']
    
    # Filtra apenas as abas que o usuário pode ver
    abas_visiveis = [nome for nome, cargos in PERMISSOES.items() if cargo_atual in cargos]
    
    # Validação de segurança
    if not abas_visiveis:
        st.error("Seu perfil não tem acesso a nenhuma funcionalidade. Contate o suporte técnico.")
        return

    # Renderiza as abas
    objetos_abas = st.tabs(abas_visiveis)
    
    # Cria dicionário de mapeamento para o resto do código
    mapa_abas = dict(zip(abas_visiveis, objetos_abas))

    # =========================================================================
    # RENDERIZAÇÃO DAS ABAS (Só entra no IF se a aba existir no mapa)
    # =========================================================================

    # --- ABA: DASHBOARD ---
    if "📊 Dashboard" in mapa_abas:
        with mapa_abas["📊 Dashboard"]:
            # Cabeçalho dinâmico baseado no perfil
            if cargo_atual in ['Master', 'Administrativo', 'Financeiro']:
                st.header("📈 Visão Geral da Empresa")
                st.info("Acompanhe o faturamento, liquidez e copie os IDs para realizar ajustes em lote.")
            else:
                st.header("🎯 Meu Painel de Vendas")
                st.info("Acompanhe suas comissões, identifique suas vendas diretas vs. gerência e exporte seus relatórios.")

            # Prepara filtros e limpezas
            df['Vendedor'] = df['Vendedor'].fillna('').astype(str)
            df['Gerente'] = df['Gerente'].fillna('').astype(str)
            df['Cliente'] = df['Cliente'].fillna('').astype(str)
            df['Administradora'] = df['Administradora'].fillna('').astype(str)
            df['ID_Vendedor'] = df['ID_Vendedor'].fillna('0').astype(str).str.replace('.0','', regex=False)
            df['ID_Gerente'] = df['ID_Gerente'].fillna('0').astype(str).str.replace('.0','', regex=False)
            df['Data_Previsao'] = pd.to_datetime(df['Data_Previsao'], errors='coerce')
            df['Mes_Referencia'] = df['Data_Previsao'].dt.strftime('%m/%Y')

            # Previne erros de NA nos filtros de status
            for col_st in ['Status_Recebimento', 'Status_Pgto_Cliente', 'Status_Pgto_Vendedor', 'Status_Pgto_Gerente']:
                if col_st in df.columns:
                    df[col_st] = df[col_st].fillna('Pendente').astype(str)

            meu_id = st.session_state['id_usuario']
            dfv = df.copy()
            
            # Row Level Security (Segurança por Linha)
            if cargo_atual not in ['Master', 'Administrativo', 'Financeiro']:
                dfv = dfv[(dfv['ID_Vendedor'] == meu_id) | (dfv['ID_Gerente'] == meu_id)]
                
            # Calcula a métrica principal de visualização
            dfv['Minha_Comissao'] = 0.0
            if cargo_atual in ['Master', 'Administrativo', 'Financeiro']:
                dfv['Minha_Comissao'] = dfv['Liquido_Caixa']
            else:
                m_v = dfv['ID_Vendedor'] == meu_id
                m_g = dfv['ID_Gerente'] == meu_id
                if 'Pagar_Vendedor' in dfv: dfv.loc[m_v, 'Minha_Comissao'] += dfv.loc[m_v, 'Pagar_Vendedor']
                if 'Pagar_Gerente' in dfv: dfv.loc[m_g, 'Minha_Comissao'] += dfv.loc[m_g, 'Pagar_Gerente']

            # --- FILTROS AVANÇADOS ---
            with st.expander("🔍 Filtros do Painel", expanded=False):
                st.markdown("**Filtros de Perfil e Venda**")
                c1, c2, c3, c4 = st.columns(4)
                f_mes = c1.multiselect("Mês Vencimento", sorted(dfv['Mes_Referencia'].dropna().unique()))
                f_adm = c2.multiselect("Administradora", sorted(dfv['Administradora'].unique()))
                f_cli = c3.multiselect("Cliente", sorted(dfv['Cliente'].unique()))
                
                # Se for Master, mostra filtro de vendedor. Se for vendedor/gerente, também mostra para ele filtrar o próprio time.
                f_vend = c4.multiselect("Vendedor", sorted(dfv['Vendedor'].unique()))
                
                st.markdown("**Filtros de Status (Pagamentos e Recebimentos)**")
                c5, c6, c7, c8 = st.columns(4)
                f_stat_adm = c5.multiselect("Status Admin (FPR)", sorted(dfv['Status_Recebimento'].unique()))
                f_stat_cli = c6.multiselect("Status Cliente (Boleto)", sorted(dfv['Status_Pgto_Cliente'].unique()))
                
                # Campos dinâmicos dependendo das colunas existentes
                f_stat_vend = []
                f_stat_ger = []
                if 'Status_Pgto_Vendedor' in dfv.columns:
                    f_stat_vend = c7.multiselect("Status Repasse Vendedor", sorted(dfv['Status_Pgto_Vendedor'].unique()))
                if 'Status_Pgto_Gerente' in dfv.columns:
                    f_stat_ger = c8.multiselect("Status Repasse Gerente", sorted(dfv['Status_Pgto_Gerente'].unique()))
                
            # Aplica filtros
            if f_mes: dfv = dfv[dfv['Mes_Referencia'].isin(f_mes)]
            if f_adm: dfv = dfv[dfv['Administradora'].isin(f_adm)]
            if f_cli: dfv = dfv[dfv['Cliente'].isin(f_cli)]
            if f_vend: dfv = dfv[dfv['Vendedor'].isin(f_vend)]
            if f_stat_adm: dfv = dfv[dfv['Status_Recebimento'].isin(f_stat_adm)]
            if f_stat_cli: dfv = dfv[dfv['Status_Pgto_Cliente'].isin(f_stat_cli)]
            if f_stat_vend: dfv = dfv[dfv['Status_Pgto_Vendedor'].isin(f_stat_vend)]
            if f_stat_ger: dfv = dfv[dfv['Status_Pgto_Gerente'].isin(f_stat_ger)]
            
            # --- MÉTRICAS (KPIs) ---
            st.markdown("### 💰 Resumo Financeiro")
            k1, k2, k3 = st.columns(3)
            if cargo_atual in ['Master', 'Administrativo', 'Financeiro']:
                pend = dfv[dfv['Status_Recebimento'] != 'Pago']['Receber_Administradora'].sum()
                pago = dfv[dfv['Status_Recebimento'] == 'Pago']['Receber_Administradora'].sum()
                liq = dfv['Liquido_Caixa'].sum()
                
                k1.metric("Empresa a Receber (Bruto)", f"R$ {pend:,.2f}", help="Soma total pendente da administradora.")
                k2.metric("Empresa Recebido (Bruto)", f"R$ {pago:,.2f}", help="Soma total já recebida da administradora.")
                k3.metric("Líquido Projetado (Caixa)", f"R$ {liq:,.2f}", help="Lucro da empresa após deduzir comissões.")
            else:
                pend = dfv[dfv['Status_Recebimento'] != 'Pago']['Minha_Comissao'].sum()
                pago = dfv[dfv['Status_Recebimento'] == 'Pago']['Minha_Comissao'].sum()
                
                k1.metric("⏳ Comissão Futura", f"R$ {pend:,.2f}", help="Valor pendente de recebimento pela empresa.")
                k2.metric("✅ Comissão Liberada", f"R$ {pago:,.2f}", help="Valor já recebido pela empresa e pronto para repasse.")

            st.divider()

            # --- GRÁFICOS ---
            if not dfv.empty:
                st.markdown("### 📊 Análise de Desempenho")
                g1, g2 = st.columns(2)
                
                with g1:
                    st.caption("Evolução Mensal (Líquido/Comissão)")
                    st.bar_chart(dfv.groupby('Mes_Referencia')['Minha_Comissao'].sum(), color="#ff4b4b")
                
                with g2:
                    if 'Administradora' in dfv.columns:
                        st.caption("Receita por Administradora")
                        st.bar_chart(dfv.groupby('Administradora')['Minha_Comissao'].sum(), color="#4b8bff")
            
            st.divider()
            
            # --- TABELA DE DADOS RESUMIDA ---
            dft = dfv.copy()
            
            # --- VISÃO: COLUNAS TÉCNICAS E TODOS OS VALORES PARA A OPERAÇÃO ---
            if cargo_atual in ['Master', 'Administrativo', 'Financeiro']:
                cols_view = [
                    'ID_Lancamento', 'ID_Venda', 'Data_Previsao', 'Administradora', 
                    'Cliente', 'Status_Pgto_Cliente', 'Grupo', 'Cota', 'Parcela', 
                    'Valor_Cliente', 'Receber_Administradora', 'Pagar_Vendedor', 'Pagar_Gerente', 
                    'Liquido_Caixa', 'Status_Recebimento', 
                    'Vendedor', 'Status_Pgto_Vendedor', 'Gerente', 'Status_Pgto_Gerente', 
                    'ID_Vendedor', 'ID_Gerente'
                ]
            else:
                # Vendedor/Gerente mantêm a visão enxuta para focar no seu comercial
                cols_view = [
                    'Data_Previsao', 'Administradora', 'Cliente', 'Status_Pgto_Cliente',
                    'Grupo', 'Cota', 'Parcela', 'Minha_Comissao', 'Status_Recebimento',
                    'Vendedor', 'Status_Pgto_Vendedor', 'Gerente', 'Status_Pgto_Gerente'
                ]
            
            # Garante que as colunas existem
            cols_finais = [c for c in cols_view if c in dft.columns]
            
            # Ordenação Crescente: Parcela 1/12 antes de 2/12, etc. (Mais antigas no topo)
            df_ordenado = dft[cols_finais].sort_values('Data_Previsao', ascending=True)
            
            # Título e Botão de Exportação Universal
            col_tit, col_btn = st.columns([4, 1])
            with col_tit:
                st.markdown("### 📄 Detalhamento dos Lançamentos")
            with col_btn:
                buffer_dash = io.BytesIO()
                with pd.ExcelWriter(buffer_dash, engine='openpyxl') as writer:
                    df_ordenado.to_excel(writer, index=False, sheet_name='Dashboard_Export')
                
                st.download_button(
                    label="📥 Exportar Tabela (.xlsx)",
                    data=buffer_dash.getvalue(),
                    file_name="Dashboard_FPR_Consorcios.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary",
                    key="btn_exp_dash"
                )
            
            # Renderiza a Tabela
            st.dataframe(
                df_ordenado, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID_Lancamento": st.column_config.TextColumn("ID Lanc.", help="Use para editar ou excluir na aba Ajustes"),
                    "ID_Venda": st.column_config.TextColumn("ID Venda", help="Use para cancelar na aba Cancelamentos"),
                    "ID_Vendedor": st.column_config.TextColumn("ID Vend."),
                    "ID_Gerente": st.column_config.TextColumn("ID Ger."),
                    
                    "Data_Previsao": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                    
                    "Valor_Cliente": st.column_config.NumberColumn("Valor Cliente", format="R$ %.2f", help="Valor de 0.5% ref. parcela do cliente"),
                    "Receber_Administradora": st.column_config.NumberColumn("Comissão Empresa", format="R$ %.2f", help="Total da comissão que a FPR recebe"),
                    "Pagar_Vendedor": st.column_config.NumberColumn("Comissão Vendedor", format="R$ %.2f"),
                    "Pagar_Gerente": st.column_config.NumberColumn("Comissão Gerente", format="R$ %.2f"),
                    "Liquido_Caixa": st.column_config.NumberColumn("Caixa Empresa", format="R$ %.2f"),
                    "Minha_Comissao": st.column_config.NumberColumn("Minha Comissão", format="R$ %.2f"),
                    
                    "Status_Recebimento": st.column_config.TextColumn("Status Admin", help="Se a FPR já recebeu da Administradora"),
                    "Status_Pgto_Cliente": st.column_config.TextColumn("Pgto Cliente", help="Status do boleto do cliente"),
                    "Status_Pgto_Vendedor": st.column_config.TextColumn("Pgto Vendedor", help="Status do repasse ao vendedor"),
                    "Status_Pgto_Gerente": st.column_config.TextColumn("Pgto Gerente", help="Status do repasse ao gerente")
                }
            )

    # --- ABA: ENTUBA ---
    if "📥 Entuba" in mapa_abas:
        with mapa_abas["📥 Entuba"]:
            st.header("📥 Entrada de Vendas (Entuba)")
            st.info("Área para upload de novas vendas e geração automática das parcelas (financeiro e comissões).")

            c_info, c_up = st.columns([1, 2])
            
            with c_info:
                st.markdown("""
                **Instruções da Planilha:**
                O arquivo Excel precisa conter as colunas base:
                * `cliente`, `id_vendedor`, `id_gerente`
                * `tipo_cota` ou `id_cota` (Deve estar cadastrado na aba Regras)
                * `grupo`, `cota`, `valor_credito`
                * `data_venda`, `dia_vencimento`
                
                **O que o sistema fará?**
                1. Validará se o vendedor e o produto (regra) existem.
                2. Verificará duplicidades para não lançar a mesma cota duas vezes.
                3. Gerará **12 parcelas fixas** automaticamente.
                4. Calculará a parcela do cliente e o rateio da comissão da empresa e da equipe nas parcelas comissionáveis.
                """)

            with c_up:
                up = st.file_uploader("Upload Planilha de Vendas", type=['xlsx'], key='up_entuba')
                
                if up and st.button("🚀 Processar Arquivo (Entuba)", type="primary"):
                    with st.spinner("Analisando vendas, validando regras e gerando parcelas financeiras..."):
                        ok, ig, logs = backend.processar_vendas_upload(pd.read_excel(up))
                    
                    # Resumo do Processamento
                    st.divider()
                    col_res1, col_res2 = st.columns(2)
                    
                    if ok > 0:
                        col_res1.success(f"✅ Sucesso: {ok} parcelas financeiras foram geradas.")
                    else:
                        col_res1.warning("⚠️ Nenhuma parcela nova foi gerada. Verifique os erros no relatório.")
                        
                    if ig > 0:
                        col_res2.info(f"⚠️ {ig} parcelas foram ignoradas (pois já existiam no banco).")
                    
                    if not logs.empty:
                        # --- Título e Botão de Exportação lado a lado ---
                        col_tit, col_btn = st.columns([3, 1])
                        
                        with col_tit:
                            st.subheader("📋 Relatório de Processamento")
                            
                        with col_btn:
                            buffer_entuba = io.BytesIO()
                            with pd.ExcelWriter(buffer_entuba, engine='openpyxl') as writer:
                                logs.to_excel(writer, index=False, sheet_name='Log_Entuba')
                            
                            st.download_button(
                                label="📥 Exportar Relatório",
                                data=buffer_entuba.getvalue(),
                                file_name="Relatorio_Entuba.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="secondary",
                                key="btn_exp_entuba"
                            )
                        
                        def color_status_entuba(val):
                            color = 'black'
                            val_str = str(val).lower()
                            if 'sucesso' in val_str: color = 'green'
                            elif 'erro' in val_str or 'falha' in val_str: color = 'red'
                            elif 'ignorado' in val_str or 'aviso' in val_str: color = 'orange'
                            return f'color: {color}; font-weight: bold'

                        st.dataframe(
                            logs.style.applymap(color_status_entuba, subset=['Status']), 
                            use_container_width=True,
                            hide_index=True
                        )

    # --- ABA: CONCILIAÇÃO ---
    if "🏦 Conciliação" in mapa_abas:
        with mapa_abas["🏦 Conciliação"]:
            st.header("🏦 Conciliação Bancária (Baixa Automática)")
            st.info("Ferramenta para cruzar o extrato da Administradora com o sistema e realizar a baixa das parcelas pagas.")

            c_info, c_up = st.columns([1, 2])
            
            with c_info:
                st.markdown("""
                **Instruções do Extrato:**
                O arquivo Excel precisa ter as colunas abaixo:
                * **`Grupo`** e **`Cota`** (Obrigatórios).
                * **`Valor_Pago`** (Obrigatório - O sistema verificará se bate com a comissão esperada).
                * `Num_Parcela` (Opcional - Ajuda o sistema a encontrar a parcela exata).
                
                **Travas de Segurança do Sistema:**
                1. ⛔ **Divergência:** Bloqueia a baixa se o valor pago no Excel for diferente do valor esperado.
                2. ⚠️ **Duplicidade:** Ignora linhas caso a parcela já conste como 'Pago'.
                """)
                
            with c_up:
                up = st.file_uploader("Upload do Extrato da Administradora", type=['xlsx'], key='conc')
                
                if up and st.button("🚀 Processar Conciliação Automática", type="primary"):
                    with st.spinner("Cruzando dados do extrato com os lançamentos financeiros pendentes..."):
                        b, logs = backend.processar_conciliacao_upload(pd.read_excel(up))
                        
                    st.divider()
                    
                    # Resumo de Execução
                    if b > 0:
                        st.success(f"✅ Sucesso: {b} parcelas foram encontradas, conciliadas e atualizadas para 'Pago'.")
                    else:
                        st.warning("⚠️ Nenhuma parcela foi baixada. Verifique os alertas e divergências no relatório abaixo.")
                        
                    # Relatório Detalhado
                    if not logs.empty:
                        # --- NOVO: Título e Botão de Exportação lado a lado ---
                        col_tit, col_btn = st.columns([3, 1])
                        
                        with col_tit:
                            st.subheader("📋 Relatório de Processamento")
                            
                        with col_btn:
                            # Prepara o Excel em memória (Buffer) para não precisar salvar no disco do servidor
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                logs.to_excel(writer, index=False, sheet_name='Auditoria_Conciliacao')
                            
                            st.download_button(
                                label="📥 Exportar Relatório (.xlsx)",
                                data=buffer.getvalue(),
                                file_name="Auditoria_Divergencias_Conciliacao.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="secondary"
                            )
                        
                        # Função de Cor
                        def color_conciliacao(val):
                            color = 'black'
                            val_str = str(val).lower()
                            if 'sucesso' in val_str: color = 'green'
                            elif 'divergência' in val_str or 'erro' in val_str or 'não encontrado' in val_str: color = 'red'
                            elif 'já baixado' in val_str or 'aviso' in val_str: color = 'orange'
                            return f'color: {color}; font-weight: bold'

                        # Renderiza a tabela
                        col_status = 'Status_Processamento' if 'Status_Processamento' in logs.columns else 'Status'
                        st.dataframe(
                            logs.style.applymap(color_conciliacao, subset=[col_status]), 
                            use_container_width=True,
                            hide_index=True
                        )

    # --- ABA: CANCELAMENTOS ---
    if "❌ Cancelamentos" in mapa_abas:
        with mapa_abas["❌ Cancelamentos"]:
            st.header("❌ Gestão de Cancelamentos (Churn)")
            st.info("Ferramenta automatizada para interromper vendas e aplicar regras de estorno financeiro.")

            c_info, c_up = st.columns([1, 2])
            
            with c_info:
                st.markdown("""
                **Instruções da Planilha:**
                O arquivo Excel precisa ter exatamente as seguintes colunas:
                * **`ID_Venda`**: O código da venda (ex: Embracon_123_45).
                * **`Parcela_Cancelamento`**: O número da parcela de corte (ex: Se preencher `3`, o sistema cancelará a partir da parcela 4 em diante).
                
                **O que o sistema fará?**
                1. Localizará todas as parcelas **futuras** e mudará o status para `Cancelado`.
                2. Zerará os valores financeiros (Receita, Cliente e Comissões).
                3. Avaliará a regra do produto e, se for um cancelamento precoce, **gerará a multa de estorno** automaticamente.
                """)
                
            with c_up:
                up = st.file_uploader("Upload Planilha de Cancelamentos", type=['xlsx'], key='canc')
                
                if up and st.button("🚀 Processar Cancelamentos", type="primary"):
                    with st.spinner("Analisando parcelas e calculando regras de estorno..."):
                        c, logs = backend.processar_cancelamento_inteligente(pd.read_excel(up))
                        
                    if c > 0:
                        st.success(f"✅ Sucesso: {c} vendas tiveram o cancelamento processado com sucesso.")
                    else:
                        st.warning("⚠️ Nenhuma venda foi cancelada. Verifique os avisos no relatório abaixo.")
                    
                    if not logs.empty:
                        st.divider()
                        
                        # --- Título e Botão de Exportação lado a lado ---
                        col_tit, col_btn = st.columns([3, 1])
                        
                        with col_tit:
                            st.subheader("📋 Relatório de Processamento")
                            
                        with col_btn:
                            buffer_canc = io.BytesIO()
                            with pd.ExcelWriter(buffer_canc, engine='openpyxl') as writer:
                                logs.to_excel(writer, index=False, sheet_name='Log_Cancelamentos')
                            
                            st.download_button(
                                label="📥 Exportar Relatório",
                                data=buffer_canc.getvalue(),
                                file_name="Relatorio_Cancelamentos.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="secondary",
                                key="btn_exp_canc"
                            )
                        
                        def color_status(val):
                            color = 'black'
                            val_str = str(val).lower()
                            if 'sucesso' in val_str: color = 'green'
                            elif 'erro' in val_str or 'falha' in val_str: color = 'red'
                            elif 'ignorado' in val_str or 'aviso' in val_str: color = 'orange'
                            return f'color: {color}; font-weight: bold'

                        st.dataframe(
                            logs.style.applymap(color_status, subset=['Status']), 
                            use_container_width=True,
                            hide_index=True
                        )

    # --- ABA: USUÁRIOS ---
    if "👥 Usuários" in mapa_abas:
        with mapa_abas["👥 Usuários"]:
            st.header("👥 Gestão de Usuários e Acessos")
            st.info("Cadastre sua equipe, gerencie perfis de acesso e defina as taxas padrão de comissionamento.")
            
            # Divide a tela: 60% para a lista, 40% para as ações
            cl, cf = st.columns([1.5, 1])
            dfu = backend.carregar_usuarios_df()
            
            with cl:
                st.subheader("📋 Equipe Cadastrada")
                if not dfu.empty:
                    # Configuração visual da tabela
                    st.dataframe(
                        dfu[['id_usuario', 'nome_completo', 'username', 'tipo_acesso', 'taxa_vendedor', 'taxa_gerencia']], 
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "id_usuario": st.column_config.TextColumn("ID"),
                            "nome_completo": st.column_config.TextColumn("Nome Completo"),
                            "username": st.column_config.TextColumn("Login"),
                            "tipo_acesso": st.column_config.TextColumn("Perfil"),
                            # Multiplica por 100 apenas na exibição visual para ficar fácil de ler (ex: 20%)
                            "taxa_vendedor": st.column_config.NumberColumn("Tx Vendedor", format="%.2f"),
                            "taxa_gerencia": st.column_config.NumberColumn("Tx Gerente", format="%.2f")
                        }
                    )
                else:
                    st.warning("Nenhum usuário encontrado.")

            with cf:
                tab_n, tab_s, tab_e = st.tabs(["➕ Novo Usuário", "🔑 Resetar Senha", "🗑️ Excluir"])
                
                # --- SUB-ABA: NOVO USUÁRIO ---
                with tab_n:
                    with st.form("new_u", clear_on_submit=True):
                        st.markdown("**Dados Cadastrais**")
                        c1, c2 = st.columns([1, 2])
                        uid = c1.text_input("ID (Matrícula)")
                        nm = c2.text_input("Nome Completo")
                        
                        c3, c4 = st.columns(2)
                        lg = c3.text_input("Login de Acesso")
                        pw = c4.text_input("Senha Inicial", type="password")
                        
                        st.markdown("**Permissões e Comissões**")
                        tp = st.selectbox("Perfil de Acesso", ["Vendedor", "Gerente", "Administrativo", "Financeiro", "Master"])
                        
                        c5, c6 = st.columns(2)
                        tv = c5.number_input("Tx Vend (Ex: 0.20 = 20%)", value=0.20, step=0.01, help="Taxa padrão que o vendedor recebe sobre a comissão da administradora.")
                        tg = c6.number_input("Tx Ger (Ex: 0.10 = 10%)", value=0.10, step=0.01, help="Taxa padrão que o gerente recebe sobre a comissão da administradora.")
                        
                        if st.form_submit_button("Criar Usuário", type="primary", use_container_width=True):
                            if uid and nm and lg and pw:
                                ok, msg = backend.adicionar_novo_usuario(uid, nm, lg, pw, tp, tv, tg)
                                if ok:
                                    st.success(msg)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.warning("Por favor, preencha todos os campos de texto.")

                # --- SUB-ABA: RESET DE SENHA ---
                with tab_s:
                    st.markdown("**Esqueceu a senha?**")
                    if not dfu.empty:
                        us = st.selectbox("Selecione o Usuário", dfu.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}", axis=1), key='s_res')
                        np = st.text_input("Definir Nova Senha", type="password", key='np_res')
                        
                        if st.button("Atualizar Senha", use_container_width=True):
                            if np:
                                id_alvo = us.split(' - ')[0]
                                ok, msg = backend.alterar_senha_usuario(id_alvo, np)
                                if ok: 
                                    st.success("Senha atualizada com sucesso! O usuário já pode logar.")
                                    time.sleep(1)
                                    st.rerun()
                                else: 
                                    st.error(msg)
                            else:
                                st.warning("Digite a nova senha.")

                # --- SUB-ABA: EXCLUSÃO ---
                with tab_e:
                    st.markdown("**Remover Acesso**")
                    st.error("⚠️ Atenção: Se o usuário já possuir vendas registradas, o sistema bloqueará a exclusão para não quebrar o histórico financeiro.")
                    if not dfu.empty:
                        ud = st.selectbox("Selecione para Excluir", dfu.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}", axis=1), key='s_del')
                        
                        if st.button("🔥 Excluir Usuário", use_container_width=True):
                            id_alvo_del = ud.split(' - ')[0]
                            ok, msg = backend.excluir_usuario(id_alvo_del)
                            
                            if ok: 
                                st.success(msg)
                                time.sleep(1.5)
                                st.rerun()
                            else: 
                                st.error(msg)

    # --- ABA: REGRAS ---
    if "⚙️ Regras" in mapa_abas:
        with mapa_abas["⚙️ Regras"]:
            st.header("⚙️ Catálogo de Produtos e Regras")
            st.info("Cadastre e gerencie os produtos de consórcio, parâmetros técnicos e réguas de comissionamento.")
            
            dfr = backend.carregar_regras_df()
            
            # Divide a tela entre Visualização e Ação (Cadastro/Edição)
            tab_lista, tab_form = st.tabs(["📋 Produtos Cadastrados", "📝 Adicionar ou Editar Regra"])
            
            # --- SUB-ABA: LISTA DE PRODUTOS ---
            with tab_lista:
                if not dfr.empty:
                    st.dataframe(
                        dfr,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "administradora": "Administradora",
                            "tipo_cota": "Nome do Produto",
                            "lista_percentuais": "Percentuais de Comissão",
                            "id_tabela": "ID Tabela",
                            "pct_estorno": st.column_config.NumberColumn("% Multa Estorno"),
                            "limite_parcela_estorno": "Limite Parc. Estorno"
                        }
                    )
                else:
                    st.warning("Nenhuma regra ou produto cadastrado ainda.")

            # --- SUB-ABA: FORMULÁRIO DE CADASTRO/EDIÇÃO ---
            with tab_form:
                c_acao1, c_acao2 = st.columns([1, 2])
                acao = c_acao1.radio("Selecione a Ação:", ["➕ Novo Produto", "✏️ Editar Existente"], horizontal=True)
                
                dd = {}
                if acao == "✏️ Editar Existente":
                    s = c_acao2.selectbox("Selecione o Produto para Edição", sorted(dfr['tipo_cota'].unique()) if not dfr.empty else [])
                    if s: 
                        dd = dfr[dfr['tipo_cota'] == s].iloc[0].to_dict()
                else:
                    st.write("") # Espaçamento
                
                with st.form("reg", clear_on_submit=False):
                    # 1. IDENTIFICAÇÃO
                    st.markdown("### 1. Identificação do Produto")
                    c1, c2, c3 = st.columns(3)
                    adm = c1.text_input("Administradora", value=dd.get('administradora', 'Embracon'), help="Ex: Embracon, Ademicon, Porto Seguro")
                    tpc = c2.text_input("Nome do Produto (Tipo Cota)", value=dd.get('tipo_cota', ''), disabled=(acao == "✏️ Editar Existente"), help="Nome exato que virá na planilha de vendas. Ex: Imóvel Premium")
                    idt = c3.text_input("Código / ID Tabela", value=dd.get('id_tabela', ''), help="Código interno de integração")
                    
                    st.divider()
                    
                    # 2. PARÂMETROS DA COTA
                    st.markdown("### 2. Parâmetros de Crédito e Prazo")
                    c4, c5, c6, c7 = st.columns(4)
                    mnc = c4.number_input("Crédito Mínimo (R$)", value=float(dd.get('min_credito', 0)), step=1000.0)
                    mxc = c5.number_input("Crédito Máximo (R$)", value=float(dd.get('max_credito', 0)), step=1000.0)
                    mnp = c6.number_input("Prazo Mínimo (Meses)", value=int(dd.get('min_prazo', 0)), step=1)
                    mxp = c7.number_input("Prazo Máximo (Meses)", value=int(dd.get('max_prazo', 0)), step=1)
                    
                    st.divider()
                    
                    # 3. TAXAS DA ADMINISTRADORA
                    st.markdown("### 3. Taxas da Admin e Índices")
                    c10, c11, c12, c13 = st.columns(4)
                    mnt = c10.number_input("Taxa ADM Mínima (%)", value=float(dd.get('min_taxa_adm', 0)), step=0.1)
                    mxt = c11.number_input("Taxa ADM Máxima (%)", value=float(dd.get('max_taxa_adm', 0)), step=0.1)
                    fr = c12.number_input("Fundo de Reserva (%)", value=float(dd.get('fundo_reserva', 0)), step=0.1)
                    emb = c13.number_input("Limite Lance Embutido (%)", value=float(dd.get('pct_lance_embutido', 0)), step=0.1)
                    
                    c14, c15 = st.columns(2)
                    l_idx = ["INCC", "IGPM", "IPCA", "FIPE"]
                    v_idx = dd.get('indice_reajuste', 'INCC')
                    idx_sel = l_idx.index(v_idx) if v_idx in l_idx else 0
                    idx = c14.selectbox("Índice de Reajuste", l_idx, index=idx_sel)
                    
                    op_mods = ["Sorteio", "Lance Livre", "Lance Fixo", "Lance Embutido"]
                    v_mod_str = str(dd.get('modalidades_contemplacao', ''))
                    v_mod_def = [x.strip() for x in v_mod_str.split(',') if x.strip() in op_mods]
                    mods = c15.multiselect("Modalidades de Contemplação", op_mods, default=v_mod_def)
                    
                    st.divider()
                    
                    # 4. COMISSIONAMENTO E CHURN
                    st.markdown("### 4. Regras de Comissionamento e Churn (Estorno)")
                    
                    # Explicação visual para o campo mais importante
                    st.caption("⚠️ **Como preencher a esteira de comissão:** Digite os percentuais separados por vírgula. Exemplo: `1.5, 1.0, 1.0` (Significa 1.5% na parcela 1, 1.0% na parcela 2 e 1.0% na parcela 3).")
                    pct = st.text_area("Esteira de Percentuais (%)", value=dd.get('lista_percentuais', ''), height=68)
                    
                    c8, c9 = st.columns(2)
                    txa = c8.number_input("Taxa Antecipada (%)", value=float(dd.get('taxa_antecipada', 0)), step=0.1)
                    
                    opts_ref = ["1a Parcela", "Crédito", "Parcelado 12x", "2 primeiras parcelas"]
                    v_ref = str(dd.get('ref_taxa_antecipada', '1a Parcela'))
                    idx_ref = opts_ref.index(v_ref) if v_ref in opts_ref else 0
                    rta = c9.selectbox("Referência da Taxa Antecipada", opts_ref, index=idx_ref)
                    
                    ce1, ce2 = st.columns(2)
                    pest = ce1.number_input("Multa de Estorno (%)", value=float(dd.get('pct_estorno', 0)), step=0.1, help="Porcentagem de multa descontada do vendedor caso o cliente cancele antes do limite.")
                    lim = ce2.number_input("Limite de Parcela para Estorno", value=int(dd.get('limite_parcela_estorno', 3)), step=1, help="Se o cliente cancelar até esta parcela (inclusive), a multa acima é aplicada.")
                    
                    # Botão de salvar
                    if st.form_submit_button("💾 Salvar Produto e Regras", type="primary", use_container_width=True):
                        if not tpc or not pct:
                            st.error("⚠️ Os campos 'Nome do Produto' e 'Esteira de Percentuais' são obrigatórios.")
                        else:
                            save_d = {
                                'administradora': adm, 'tipo_cota': tpc, 'id_tabela': idt, 'lista_percentuais': pct,
                                'min_credito': mnc, 'max_credito': mxc, 'min_prazo': mnp, 'max_prazo': mxp,
                                'taxa_antecipada': txa, 'ref_taxa_antecipada': rta, 'min_taxa_adm': mnt, 'max_taxa_adm': mxt,
                                'fundo_reserva': fr, 'pct_lance_embutido': emb, 'indice_reajuste': idx, 
                                'modalidades_contemplacao': ", ".join(sorted(mods)),
                                'pct_estorno': pest, 'limite_parcela_estorno': lim
                            }
                            ok, msg = backend.salvar_regra_completa(save_d)
                            if ok:
                                st.success("✅ Regra salva com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Erro ao salvar: {msg}")

    # --- ABA: CLIENTES ---
    if "📇 Clientes" in mapa_abas:
        with mapa_abas["📇 Clientes"]:
            st.header("📇 Gestão de Clientes (CRM)")
            st.info("Consulte o histórico de parcelas, atualize contatos e acompanhe a inadimplência da sua carteira.")
            
            # Carrega dados
            dfc = backend.carregar_clientes()
            dfv = backend.carregar_dados()
            
            # Variáveis de sessão para facilitar
            meu_id = str(st.session_state['id_usuario']).strip()
            cargo = st.session_state['tipo_acesso']

            # 1. PREPARAÇÃO DOS DADOS FINANCEIROS (Normalização de IDs)
            if not dfv.empty:
                dfv['ID_Vendedor'] = dfv['ID_Vendedor'].fillna('0').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                dfv['ID_Gerente'] = dfv['ID_Gerente'].fillna('0').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            # 2. SEGURANÇA NA LISTA DE SELEÇÃO (ESQUERDA)
            # Se não for Master/Admin, filtra a lista de clientes para mostrar apenas os meus
            if cargo not in ['Master', 'Administrativo']:
                meus_clientes = []
                if not dfv.empty:
                    # Filtra onde sou Vendedor OU Gerente
                    mask_meus = (dfv['ID_Vendedor'] == meu_id) | (dfv['ID_Gerente'] == meu_id)
                    meus_clientes = dfv[mask_meus]['Cliente'].unique()
                
                # Aplica filtro na base de cadastro de clientes
                dfc = dfc[dfc['nome_completo'].isin(meus_clientes)]
            
            st.divider()
            
            # LAYOUT (CRM 1/4 da tela, Extrato 3/4)
            c1, c2 = st.columns([1, 3])
            
            # --- COLUNA ESQUERDA: SELEÇÃO E CADASTRO ---
            with c1:
                st.markdown("### 👤 Perfil do Cliente")
                lista_clientes = [""] + sorted(dfc['nome_completo'].unique().tolist()) if not dfc.empty else []
                sel = st.selectbox("Buscar Cliente...", lista_clientes)
                
                if sel:
                    # Pega dados cadastrais
                    d = dfc[dfc['nome_completo'] == sel].iloc[0]
                    with st.form("crm"):
                        st.text_input("🔑 ID do Cliente", d['id_cliente'], disabled=True)
                        e = st.text_input("📧 E-mail", str(d['email']))
                        t = st.text_input("📱 Telefone (WhatsApp)", str(d['telefone']))
                        o = st.text_area("📝 Observações Internas", str(d['obs']), height=100)
                        
                        if st.form_submit_button("💾 Salvar Cadastro", type="primary", use_container_width=True): 
                            backend.salvar_cliente_manual(d['id_cliente'], d['nome_completo'], e, t, o)
                            st.success("Atualizado!")
                            time.sleep(1)
                            st.rerun()
            
            # --- COLUNA DIREITA: HISTÓRICO FINANCEIRO FILTRADO ---
            with c2:
                if sel:
                    # A. Filtra pelo Cliente selecionado
                    dff = dfv[dfv['Cliente'] == sel].copy()
                    
                    # B. SEGURANÇA NA TABELA (Filtra apenas minhas parcelas)
                    if cargo not in ['Master', 'Administrativo']:
                        mask_minhas_parcelas = (dff['ID_Vendedor'] == meu_id) | (dff['ID_Gerente'] == meu_id)
                        dff = dff[mask_minhas_parcelas]

                    if not dff.empty:
                        dff = dff.sort_values('Data_Previsao')
                        
                        st.markdown(f"### 📄 Extrato Financeiro: **{sel}**")
                        
                        # --- 1. MÉTRICAS NO TOPO (Melhor UX) ---
                        c_m1, c_m2, c_m3 = st.columns(3)
                        pago = dff[dff['Status_Pgto_Cliente'] == 'Pago']['Valor_Cliente'].sum()
                        pend = dff[dff['Status_Pgto_Cliente'] != 'Pago']['Valor_Cliente'].sum()
                        total = pago + pend
                        
                        c_m1.metric("Total Pago (Pelo Cliente)", f"R$ {pago:,.2f}")
                        c_m2.metric("Total Pendente", f"R$ {pend:,.2f}")
                        c_m3.metric("Total da Cota (Visão Empresa)", f"R$ {total:,.2f}")
                        
                        st.write("") # Espaçamento
                        
                        # --- 2. TABELA RENOMEADA E FORMATADA ---
                        st.dataframe(
                            dff[[
                                'ID_Lancamento', 'Grupo', 'Cota', 'Parcela', 
                                'Data_Previsao', 'Valor_Cliente', 'Receber_Administradora', 
                                'Status_Pgto_Cliente', 'Status_Recebimento'
                            ]], 
                            use_container_width=True, 
                            hide_index=True, 
                            column_config={
                                "ID_Lancamento": "ID",
                                "Grupo": "Grp",
                                "Cota": "Cta",
                                "Parcela": "Parc",
                                "Data_Previsao": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                                "Valor_Cliente": st.column_config.NumberColumn("Valor Parcela", format="R$ %.2f"),
                                "Receber_Administradora": st.column_config.NumberColumn("Comissão Admin", format="R$ %.2f"),
                                "Status_Pgto_Cliente": st.column_config.TextColumn("Status Boleto"),
                                "Status_Recebimento": st.column_config.TextColumn("Status Admin")
                            }
                        )
                    else:
                        st.info("Nenhum registro financeiro vinculado ao seu usuário para este cliente.")
                else:
                    # Tela vazia amigável caso não tenha selecionado ninguém ainda
                    st.write("")
                    st.write("")
                    st.markdown("<h4 style='text-align: center; color: gray;'>👈 Selecione um cliente na lista ao lado para ver o histórico.</h4>", unsafe_allow_html=True)

    # --- ABA: AJUSTES ---
    if "🛠️ Ajustes" in mapa_abas:
        with mapa_abas["🛠️ Ajustes"]:
            st.header("🛠️ Ajustes e Manutenção em Lote")
            st.info("Área restrita para correção em massa da base de dados financeira.")

            t1, t2 = st.tabs(["📝 Edição em Lote", "🗑️ Exclusão em Lote"])
            
            # --- SUB-ABA: EDIÇÃO ---
            with t1:
                c_info, c_up = st.columns([1, 2])
                
                with c_info:
                    st.markdown("""
                    **Instruções para Edição:**
                    1. A planilha deve ter obrigatoriamente a coluna **`ID_Lancamento`**.
                    2. Adicione apenas as colunas que deseja alterar (ex: `data_previsao`, `id_vendedor`).
                    3. O sistema **bloqueará** a alteração de campos estruturais ou de valores/comissões já baixados.
                    """)
                
                with c_up:
                    up = st.file_uploader("Planilha de Correção", type=['xlsx'], key='adj')
                    
                    if up and st.button("Executar Edição em Lote", type="primary"):
                        with st.spinner("Processando edições..."):
                            q, log = backend.processar_edicao_lote(pd.read_excel(up))
                        
                        if q > 0:
                            st.success(f"✅ Sucesso: {q} registros foram alterados no banco de dados.")
                        else:
                            st.warning("⚠️ Nenhuma alteração foi realizada. Verifique os logs.")
                        
                        if not log.empty:
                            st.divider()
                            
                            # --- Título e Botão de Exportação lado a lado (EDIÇÃO) ---
                            col_tit, col_btn = st.columns([3, 1])
                            
                            with col_tit:
                                st.subheader("📋 Relatório de Alterações")
                                
                            with col_btn:
                                buffer_edicao = io.BytesIO()
                                with pd.ExcelWriter(buffer_edicao, engine='openpyxl') as writer:
                                    log.to_excel(writer, index=False, sheet_name='Auditoria_Edicao')
                                
                                st.download_button(
                                    label="📥 Exportar Relatório",
                                    data=buffer_edicao.getvalue(),
                                    file_name="Auditoria_Edicao_Lote.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="secondary",
                                    key="btn_exp_edicao"
                                )
                            
                            def color_edicao(val):
                                color = 'black'
                                val_str = str(val).lower()
                                if 'sucesso' in val_str: color = 'green'
                                elif 'bloqueado' in val_str or 'erro' in val_str: color = 'red'
                                elif 'ignorado' in val_str: color = 'orange'
                                return f'color: {color}; font-weight: bold'
                            
                            st.dataframe(
                                log.style.applymap(color_edicao, subset=['Status']), 
                                use_container_width=True, 
                                hide_index=True
                            )

            # --- SUB-ABA: EXCLUSÃO ---
            with t2:
                c_warn, c_up_del = st.columns([1, 2])
                
                with c_warn:
                    st.warning("""
                    ⚠️ **Atenção: Ação Irreversível!**
                    * Esta ferramenta remove permanentemente o registro do banco de dados.
                    * O sistema bloqueará automaticamente a exclusão de parcelas que já possuam qualquer tipo de pagamento atrelado.
                    * A planilha precisa apenas da coluna **`ID_Lancamento`**.
                    """)
                
                with c_up_del:
                    upd = st.file_uploader("Planilha de IDs para Exclusão", type=['xlsx'], key='del')
                    
                    if upd and st.button("🔥 Confirmar Exclusão Definitiva", type="primary"):
                        with st.spinner("Removendo registros..."):
                            q, log = backend.processar_exclusao_lote(pd.read_excel(upd))
                            
                        if q > 0:
                            st.success(f"✅ Sucesso: {q} registros foram excluídos permanentemente.")
                        else:
                            st.warning("⚠️ Nenhum registro foi excluído. Verifique os logs.")
                        
                        if not log.empty:
                            st.divider()
                            
                            # --- Título e Botão de Exportação lado a lado (EXCLUSÃO) ---
                            col_tit_del, col_btn_del = st.columns([3, 1])
                            
                            with col_tit_del:
                                st.subheader("📋 Relatório de Exclusões")
                                
                            with col_btn_del:
                                buffer_exclusao = io.BytesIO()
                                with pd.ExcelWriter(buffer_exclusao, engine='openpyxl') as writer:
                                    log.to_excel(writer, index=False, sheet_name='Auditoria_Exclusao')
                                
                                st.download_button(
                                    label="📥 Exportar Relatório",
                                    data=buffer_exclusao.getvalue(),
                                    file_name="Auditoria_Exclusao_Lote.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="secondary",
                                    key="btn_exp_exclusao"
                                )
                            
                            def color_exclusao(val):
                                color = 'black'
                                val_str = str(val).lower()
                                if 'excluído' in val_str: color = 'green'
                                elif 'bloqueado' in val_str or 'erro' in val_str: color = 'red'
                                elif 'ignorado' in val_str or 'aviso' in val_str: color = 'orange'
                                return f'color: {color}; font-weight: bold'
                            
                            st.dataframe(
                                log.style.applymap(color_exclusao, subset=['Status']), 
                                use_container_width=True, 
                                hide_index=True
                            )

    # --- ABA: PARCELAS CLIENTES ---
    if "📄 Parcelas Clientes" in mapa_abas:
        with mapa_abas["📄 Parcelas Clientes"]:
            st.header("📄 Controle de Parcelas dos Clientes")
            st.info("Filtre, selecione e atualize o status dos pagamentos realizados pelos clientes.")
            
            dfa = backend.carregar_dados()
            
            # --- 1. FILTROS ---
            c1, c2, c3, c4 = st.columns(4)
            m = c1.radio("Status da Parcela", ["Pendente", "Pago"], horizontal=True, key="rad_status_parc")
            
            # Prepara a base conforme o status
            t = 'Pago' if m == 'Pago' else 'Pendente'
            df_view = dfa[dfa['Status_Pgto_Cliente'] == t].copy()
            
            if not df_view.empty:
                # Garante formato de data e cria coluna de Mês/Ano para facilitar o filtro
                df_view['Data_Previsao'] = pd.to_datetime(df_view['Data_Previsao'], errors='coerce')
                df_view['Mes_Venc'] = df_view['Data_Previsao'].dt.strftime('%m/%Y')
                
                f_mes = c2.multiselect("Mês Vencimento", sorted(df_view['Mes_Venc'].dropna().unique()), key="sel_mes_parc")
                f_cli = c3.multiselect("Cliente", sorted(df_view['Cliente'].dropna().unique()), key="sel_cli_parc")
                f_vend = c4.multiselect("Vendedor", sorted(df_view['Vendedor'].dropna().unique()), key="sel_vend_parc")
                
                # Aplica os filtros escolhidos
                if f_mes: df_view = df_view[df_view['Mes_Venc'].isin(f_mes)]
                if f_cli: df_view = df_view[df_view['Cliente'].isin(f_cli)]
                if f_vend: df_view = df_view[df_view['Vendedor'].isin(f_vend)]
            
            st.divider()
            
            # --- 2. ÁREA DE DADOS E TABELA ---
            if df_view.empty:
                st.warning("Nenhuma parcela encontrada com os filtros e status atuais.")
            else:
                # Métrica geral da tela
                tot_filtrado = df_view['Valor_Cliente'].sum()
                st.metric(f"Total {m} (Conforme Filtros)", f"R$ {tot_filtrado:,.2f}")
                
                # Preparações para a Tabela
                df_view['Sel'] = False
                df_view = df_view.sort_values('Data_Previsao')
                
                # --- NOVO: LÓGICA DE ALERTAS DE VENCIMENTO ---
                hoje = pd.Timestamp.today().normalize()
                limite_prox = hoje + pd.Timedelta(days=7) # Define o que é "próximo" (7 dias)
                
                def gerar_alerta(data):
                    if pd.isnull(data): return ""
                    if data < hoje:
                        dias = (hoje - data).days
                        return f"🔴 Atrasado ({dias}d)"
                    elif data == hoje:
                        return "🟠 Vence Hoje!"
                    elif data <= limite_prox:
                        dias = (data - hoje).days
                        return f"🟡 Vence em {dias}d"
                    return "🟢 No Prazo"

                # Só cria a coluna de alerta se a visão for de Pendentes (não faz sentido para os Pagos)
                if m == 'Pendente':
                    df_view['Status_Prazo'] = df_view['Data_Previsao'].apply(gerar_alerta)
                    colunas_mostrar = ['Sel', 'ID_Lancamento', 'Cliente', 'Grupo', 'Cota', 'Parcela', 'Data_Previsao', 'Status_Prazo', 'Valor_Cliente']
                else:
                    colunas_mostrar = ['Sel', 'ID_Lancamento', 'Cliente', 'Grupo', 'Cota', 'Parcela', 'Data_Previsao', 'Valor_Cliente']
                
                colunas_finais = [c for c in colunas_mostrar if c in df_view.columns]
                
                # --- NOVO: PINTA AS LINHAS COM CORES ---
                def colorir_linhas(row):
                    # Usamos color (cor do texto) em vez de background para não estourar os olhos nem quebrar no Dark Mode
                    if m == 'Pendente' and pd.notnull(row['Data_Previsao']):
                        venc = row['Data_Previsao']
                        if venc < hoje:
                            return ['color: #ff4b4b; font-weight: bold'] * len(row) # Vermelho (Atrasado)
                        elif venc <= limite_prox:
                            return ['color: #ffa421; font-weight: bold'] * len(row) # Laranja (Próximo)
                    return [''] * len(row)
                
                # Aplica o estilo ao dataframe
                df_styled = df_view[colunas_finais].style.apply(colorir_linhas, axis=1)
                
                # Tabela Editável renderizando o DataFrame estilizado
                ed = st.data_editor(
                    df_styled, 
                    key='ed_parcelas_cli',
                    hide_index=True,
                    use_container_width=True,
                    disabled=['ID_Lancamento', 'Cliente', 'Grupo', 'Cota', 'Parcela', 'Data_Previsao', 'Status_Prazo', 'Valor_Cliente'], 
                    column_config={
                        "Sel": st.column_config.CheckboxColumn("☑️", help="Selecione para alterar"),
                        "Data_Previsao": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                        "Status_Prazo": st.column_config.TextColumn("Alerta"),
                        "Valor_Cliente": st.column_config.NumberColumn("Valor Parcela", format="R$ %.2f")
                    }
                )
                
                # --- 3. AÇÕES EM LOTE ---
                sel = ed[ed['Sel'] == True]
                if not sel.empty:
                    st.divider()
                    st.info(f"Você selecionou **{len(sel)}** parcelas.")
                    st.metric("Total Selecionado para Baixa/Estorno", f"R$ {sel['Valor_Cliente'].sum():,.2f}")
                    
                    nt = 'Pendente' if m == 'Pago' else 'Pago'
                    
                    txt_botao = "✅ Confirmar Pagamento das Selecionadas" if nt == 'Pago' else "↩️ Estornar para Pendentes"
                    tipo_botao = "primary" if nt == 'Pago' else "secondary"
                    
                    if st.button(txt_botao, type=tipo_botao): 
                        backend.alterar_status_cliente_lote(sel['ID_Lancamento'].tolist(), nt)
                        st.success("Status atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()

    # --- ABA: COMISSÕES ---
    if "💸 Comissões" in mapa_abas:
        with mapa_abas["💸 Comissões"]:
            st.header("💸 Controle de Comissões")
            st.info("Filtre, confira as referências das vendas e realize a baixa (pagamento) das comissões da equipe.")
            
            # --- 1. CONTROLES SUPERIORES ---
            c_rad, c_chk = st.columns([1, 2])
            m = c_rad.radio("Status da Comissão", ["Pendente", "Pago"], horizontal=True, key='rad_status_comissao')
            # Checkbox mais claro: só mostra o que a empresa já recebeu
            liberados = c_chk.checkbox("Mostrar apenas liberadas (Onde a FPR já recebeu a comissão da Admin)", value=True, key='chk_liberados')
            
            dfa = backend.carregar_dados()
            t = 'Pago' if m == 'Pago' else 'Pendente'
            
            rows = []
            for _, r in dfa.iterrows():
                # Cria uma string de contexto para o operador saber do que se trata a comissão
                contexto_venda = f"{r.get('Cliente', '')} | {r.get('Grupo', '')}/{r.get('Cota', '')} (P: {r.get('Parcela', '')})"
                
                # Coleta Vendedor
                if str(r.get('Status_Pgto_Vendedor', 'Pendente')) == t and r.get('Pagar_Vendedor', 0) > 0:
                    rows.append({
                        'ID': r['ID_Lancamento'], 
                        'Tipo': 'Vendedor', 
                        'Nome': r['Vendedor'], 
                        'Valor': r['Pagar_Vendedor'], 
                        'Cx': r['Status_Recebimento'],
                        'Referência': contexto_venda
                    })
                # Coleta Gerente
                if str(r.get('Status_Pgto_Gerente', 'Pendente')) == t and r.get('Pagar_Gerente', 0) > 0:
                    rows.append({
                        'ID': r['ID_Lancamento'], 
                        'Tipo': 'Gerente', 
                        'Nome': r['Gerente'], 
                        'Valor': r['Pagar_Gerente'], 
                        'Cx': r['Status_Recebimento'],
                        'Referência': contexto_venda
                    })
            
            if rows:
                dv = pd.DataFrame(rows)
                
                # Aplica o filtro do caixa (Admin)
                if liberados: 
                    dv = dv[dv['Cx'] == 'Pago']
                
                if not dv.empty:
                    st.divider()
                    
                    # --- 2. FILTROS DINÂMICOS ---
                    cf1, cf2 = st.columns(2)
                    f_tipo = cf1.multiselect("Filtrar Cargo", sorted(dv['Tipo'].unique()), key='sel_tipo_com')
                    f_nome = cf2.multiselect("Filtrar Colaborador", sorted(dv['Nome'].unique()), key='sel_nome_com')
                    
                    if f_tipo: dv = dv[dv['Tipo'].isin(f_tipo)]
                    if f_nome: dv = dv[dv['Nome'].isin(f_nome)]
                
                if not dv.empty:
                    # Métrica visual do que está filtrado
                    st.metric(f"Total {m} (Na tela atual)", f"R$ {dv['Valor'].sum():,.2f}")
                    
                    # --- 3. TABELA COM UX MELHORADA ---
                    dv['Sel'] = False
                    colunas_ordem = ['Sel', 'ID', 'Referência', 'Tipo', 'Nome', 'Valor', 'Cx']
                    
                    ed = st.data_editor(
                        dv[colunas_ordem], 
                        key='ed_comissoes_view',
                        hide_index=True,
                        use_container_width=True,
                        # Impede edição de texto, libera só a caixa de seleção
                        disabled=['ID', 'Referência', 'Tipo', 'Nome', 'Valor', 'Cx'],
                        column_config={
                            "Sel": st.column_config.CheckboxColumn("☑️", help="Selecione para baixar"),
                            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                            "Cx": st.column_config.TextColumn("Status Admin", help="Status do recebimento pela FPR")
                        }
                    )
                    
                    # --- 4. AÇÃO EM LOTE ---
                    s = ed[ed['Sel'] == True]
                    if not s.empty:
                        st.divider()
                        st.info(f"Você selecionou **{len(s)}** comissões.")
                        st.metric("Total Selecionado", f"R$ {s['Valor'].sum():,.2f}")
                        
                        nt = 'Pendente' if m == 'Pago' else 'Pago'
                        
                        txt_btn = "✅ Confirmar Pagamento das Comissões" if nt == 'Pago' else "↩️ Estornar para Pendentes"
                        cor_btn = "primary" if nt == 'Pago' else "secondary"
                        
                        if st.button(txt_btn, type=cor_btn):
                            l = [{'id': r['ID'], 'tipo': r['Tipo'], 'status': nt} for _, r in s.iterrows()]
                            backend.processar_baixa_comissoes_lote(l)
                            st.success("Operação concluída com sucesso!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("Nenhuma comissão encontrada para os filtros aplicados.")
            else:
                st.success("Tudo limpo! Nenhuma comissão encontrada nestes parâmetros.")

if 'logado' not in st.session_state: st.session_state['logado']=False
if not st.session_state['logado']: tela_login()
else: main()