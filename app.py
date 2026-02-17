import streamlit as st
import pandas as pd
import time
import backend
import io

st.set_page_config(page_title="FPR Consórcios", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center;}
    .stTabs [data-baseweb="tab-list"] {gap: 2px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: #f9f9f9; border-radius: 5px 5px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;}
    .stTabs [aria-selected="true"] {background-color: #ffffff; border-top: 3px solid #ff4b4b;}
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
def verificar_login(u, s):
    df = backend.carregar_usuarios_df()
    # Limpa espaços em branco para evitar erro de login
    m = df[df['username'] == u.strip()]
    if not m.empty:
        if m.iloc[0]['password_hash'] == backend.gerar_hash(s): return True, m.iloc[0]
    return False, None

def tela_login():
    st.markdown("<br><br><h1 style='text-align: center;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("l"):
            u = st.text_input("Usuário"); s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                ok, d = verificar_login(u, s)
                if ok:
                    st.session_state.update({'logado':True, 'usuario':u, 'tipo_acesso':d['tipo_acesso'], 'nome':d['nome_completo'], 'id_usuario':str(d['id_usuario']).replace('.0','')})
                    st.success("Entrando..."); time.sleep(0.5); st.rerun()
                else: st.error("Login inválido")

def main():
    with st.sidebar:
        st.write(f"👤 **{st.session_state['nome']}**")
        st.caption(f"Cargo: {st.session_state['tipo_acesso']}")
        st.divider()
    
    with st.sidebar:
        st.write(f"👤 **{st.session_state['nome']}**")
        st.caption(f"Cargo: {st.session_state['tipo_acesso']}")
        
        # --- ALTERAR PRÓPRIA SENHA (NOVO) ---
        with st.expander("🔐 Alterar Minha Senha"):
            with st.form("form_minha_senha"):
                senha_nova_1 = st.text_input("Nova Senha", type="password")
                senha_nova_2 = st.text_input("Confirmar Senha", type="password")
                
                if st.form_submit_button("Atualizar"):
                    if senha_nova_1 == "" or senha_nova_2 == "":
                        st.warning("Digite a senha.")
                    elif senha_nova_1 != senha_nova_2:
                        st.error("As senhas não coincidem.")
                    else:
                        # O usuário altera a senha do SEU PRÓPRIO ID
                        ok, msg = backend.alterar_senha_usuario(st.session_state['id_usuario'], senha_nova_1)
                        if ok:
                            st.success("Senha alterada!")
                            time.sleep(1)
                            # Opcional: Deslogar para forçar novo login
                            # st.session_state['logado'] = False
                            st.rerun()
                        else:
                            st.error(msg)
        
        st.divider()
        if st.button("Sair"): st.session_state['logado']=False; st.rerun()

    st.title("💰 Sistema de Gestão de Comissões")
    
    # Carrega DF e garante que não vem vazio
    df = backend.carregar_dados()
    if df.empty:
        st.warning("Banco de dados vazio. Faça upload na aba Entuba.")
        cols = ['ID_Lancamento','ID_Vendedor','ID_Gerente','Data_Previsao','Status_Recebimento','Receber_Administradora','Liquido_Caixa','Status_Pgto_Cliente','Cliente','Vendedor','Gerente','Pagar_Vendedor','Pagar_Gerente','Administradora','Status_Pgto_Vendedor','Status_Pgto_Gerente']
        df = pd.DataFrame(columns=cols)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 Dashboard", "📥 Entuba", "🏦 Conciliação", "❌ Cancelamentos", 
        "👥 Usuários", "⚙️ Regras", "📇 Clientes", "🛠️ Ajustes", 
        "💰 Recebimentos", "💸 Comissões"
    ])

    # --- ABA 1: DASHBOARD ---
    with tab1:
        # 1. Limpeza de Dados para Filtros
        df['Vendedor'] = df['Vendedor'].fillna('').astype(str)
        df['Cliente'] = df['Cliente'].fillna('').astype(str)
        df['Administradora'] = df['Administradora'].fillna('').astype(str)
        df['Status_Recebimento'] = df['Status_Recebimento'].fillna('Pendente')
        df['Status_Pgto_Cliente'] = df['Status_Pgto_Cliente'].fillna('Pendente')
        df['Status_Pgto_Vendedor'] = df['Status_Pgto_Vendedor'].fillna('Pendente')
        df['Status_Pgto_Gerente'] = df['Status_Pgto_Gerente'].fillna('Pendente')
        
        df['ID_Vendedor'] = df['ID_Vendedor'].fillna('0').astype(str).str.replace('.0','', regex=False)
        df['ID_Gerente'] = df['ID_Gerente'].fillna('0').astype(str).str.replace('.0','', regex=False)
        df['Data_Previsao'] = pd.to_datetime(df['Data_Previsao'], errors='coerce')
        df['Mes_Referencia'] = df['Data_Previsao'].dt.strftime('%Y-%m')

        meu_id = st.session_state['id_usuario']; cargo = st.session_state['tipo_acesso']
        dfv = df.copy()
        
        # 2. Segurança (Row Level Security)
        if cargo not in ['Master', 'Administrativo']:
            dfv = dfv[(dfv['ID_Vendedor']==meu_id) | (dfv['ID_Gerente']==meu_id)]
            
        # 3. Cálculo de Comissão Pessoal vs Empresa
        dfv['Minha_Comissao'] = 0.0
        if cargo in ['Master', 'Administrativo']:
            dfv['Minha_Comissao'] = dfv['Liquido_Caixa']
        else:
            m_v = dfv['ID_Vendedor'] == meu_id
            m_g = dfv['ID_Gerente'] == meu_id
            if 'Pagar_Vendedor' in dfv: dfv.loc[m_v, 'Minha_Comissao'] += dfv.loc[m_v, 'Pagar_Vendedor']
            if 'Pagar_Gerente' in dfv: dfv.loc[m_g, 'Minha_Comissao'] += dfv.loc[m_g, 'Pagar_Gerente']

        # 4. FILTROS AVANÇADOS (ATUALIZADO)
        with st.expander("🔍 Filtros Avançados", expanded=False):
            # Linha 1: Dados Gerais
            c1,c2,c3 = st.columns(3)
            f_mes = c1.multiselect("Mês", sorted(dfv['Mes_Referencia'].dropna().unique()))
            f_adm = c2.multiselect("Administradora", sorted(dfv['Administradora'].unique()))
            f_cli = c3.multiselect("Cliente", sorted(dfv['Cliente'].unique()))
            
            # Linha 2: Pessoas
            c4,c5 = st.columns(2)
            f_vend = c4.multiselect("Vendedor", sorted(dfv['Vendedor'].unique()))
            # Se quiser filtro de gerente também, pode adicionar aqui
            
            # Linha 3: Status Financeiros
            c6,c7,c8,c9 = st.columns(4)
            st_adm = c6.multiselect("Status Admin", sorted(dfv['Status_Recebimento'].unique()))
            st_cli = c7.multiselect("Status Cliente", sorted(dfv['Status_Pgto_Cliente'].unique()))
            st_pgv = c8.multiselect("Pgto Vendedor", sorted(dfv['Status_Pgto_Vendedor'].unique()))
            st_pgg = c9.multiselect("Pgto Gerente", sorted(dfv['Status_Pgto_Gerente'].unique()))

        # Aplicação dos Filtros
        if f_mes: dfv = dfv[dfv['Mes_Referencia'].isin(f_mes)]
        if f_adm: dfv = dfv[dfv['Administradora'].isin(f_adm)]
        if f_cli: dfv = dfv[dfv['Cliente'].isin(f_cli)]
        if f_vend: dfv = dfv[dfv['Vendedor'].isin(f_vend)]
        
        if st_adm: dfv = dfv[dfv['Status_Recebimento'].isin(st_adm)]
        if st_cli: dfv = dfv[dfv['Status_Pgto_Cliente'].isin(st_cli)]
        if st_pgv: dfv = dfv[dfv['Status_Pgto_Vendedor'].isin(st_pgv)]
        if st_pgg: dfv = dfv[dfv['Status_Pgto_Gerente'].isin(st_pgg)]
        
        # 5. KPIs
        k1,k2,k3 = st.columns(3)
        if cargo in ['Master', 'Administrativo']:
            pend = dfv[dfv['Status_Recebimento']!='Pago']['Receber_Administradora'].sum()
            pago = dfv[dfv['Status_Recebimento']=='Pago']['Receber_Administradora'].sum()
            liq = dfv['Liquido_Caixa'].sum()
            k1.metric("A Receber (Admin)", f"R$ {pend:,.2f}")
            k2.metric("Recebido (Admin)", f"R$ {pago:,.2f}")
            k3.metric("Líquido Caixa", f"R$ {liq:,.2f}")
        else:
            pend = dfv[dfv['Status_Recebimento']!='Pago']['Minha_Comissao'].sum()
            pago = dfv[dfv['Status_Recebimento']=='Pago']['Minha_Comissao'].sum()
            k1.metric("Comissão Futura", f"R$ {pend:,.2f}")
            k2.metric("Comissão Liberada", f"R$ {pago:,.2f}")

        st.divider()
        if not dfv.empty:
            g1, g2 = st.columns(2)
            g1.bar_chart(dfv.groupby('Mes_Referencia')['Minha_Comissao'].sum())
            # Gráfico por Administradora se houver dados
            if 'Administradora' in dfv.columns:
                g2.bar_chart(dfv.groupby('Administradora')['Minha_Comissao'].sum())
        
        # Tabela Detalhada
        dft = dfv.copy()
        if cargo not in ['Master', 'Administrativo']:
            # Esconde colunas sensíveis da empresa
            dft = dft.drop(columns=['Receber_Administradora','Liquido_Caixa'], errors='ignore')
            # Mascara comissão alheia
            dft.loc[dft['ID_Vendedor']!=meu_id, 'Pagar_Vendedor'] = None
            dft.loc[dft['ID_Gerente']!=meu_id, 'Pagar_Gerente'] = None
            
        st.dataframe(dft, use_container_width=True)

    # --- ABA 2: ENTUBA ---
    with tab2:
        if cargo in ['Master', 'Administrativo']:
            st.header("Upload Vendas")
            up = st.file_uploader("Excel", type=['xlsx'])
            if up and st.button("Processar lançamentos"):
                ok, ig, er = backend.processar_vendas_upload(pd.read_excel(up))
                if er: st.error(f"Erros: {er}")
                else: st.success(f"{ok} processados, {ig} ignorados."); time.sleep(2); st.rerun()

    # --- ABA 3: CONCILIAÇÃO ---
    with tab3:
        if cargo == 'Master':
            st.header("Conciliação")
            up = st.file_uploader("Extrato", type=['xlsx'], key='conc')
            if up and st.button("Baixar"):
                b, log = backend.processar_conciliacao_upload(pd.read_excel(up))
                st.success(f"{b} baixados"); st.dataframe(log)

    # --- ABA 4: CANCELAMENTOS ---
    with tab4:
        if cargo == 'Master':
            st.header("Cancelamentos")
            up = st.file_uploader("Planilha", type=['xlsx'], key='canc')
            if up and st.button("Processar cancelamentos"):
                c, log = backend.processar_cancelamento_inteligente(pd.read_excel(up))
                st.success(f"{c} processados"); st.write(log)

    # --- ABA 5: GESTÃO DE USUÁRIOS ---
    with tab5:
        if cargo in ['Master', 'Administrativo']:
            st.header("👥 Gestão de Usuários")
            
            # Divide a tela em duas colunas: Lista e Ações
            col_lista, col_form = st.columns([2, 1])
            
            df_users = backend.carregar_usuarios_df()
            
            with col_lista:
                st.subheader("Usuários Cadastrados")
                st.dataframe(
                    df_users[['id_usuario', 'nome_completo', 'username', 'tipo_acesso', 'taxa_vendedor', 'taxa_gerencia']],
                    use_container_width=True,
                    hide_index=True
                )

            with col_form:
                st.subheader("Ações")
                # AGORA SÃO 3 ABAS: NOVO, SENHA, EXCLUIR
                aba_novo, aba_senha, aba_excluir = st.tabs(["➕ Novo", "🔑 Senha", "🗑️ Excluir"])
                
                # --- ABA 1: NOVO USUÁRIO ---
                with aba_novo:
                    with st.form("form_add_user"):
                        uid = st.text_input("ID (Ex: 10)")
                        nm = st.text_input("Nome Completo")
                        lg = st.text_input("Login")
                        pw = st.text_input("Senha Inicial", type="password")
                        tp = st.selectbox("Perfil", ["Vendedor", "Gerente", "Administrativo", "Master"])
                        c1, c2 = st.columns(2)
                        tv = c1.number_input("Taxa Vend", 0.0, 1.0, 0.20)
                        tg = c2.number_input("Taxa Ger", 0.0, 1.0, 0.10)
                        
                        if st.form_submit_button("Cadastrar Usuário"):
                            if not uid or not nm or not lg or not pw:
                                st.warning("Preencha todos os campos.")
                            else:
                                ok, msg = backend.adicionar_novo_usuario(uid, nm, lg, pw, tp, tv, tg)
                                if ok: st.success(msg); time.sleep(1); st.rerun()
                                else: st.error(msg)

                # --- ABA 2: ALTERAR SENHA (ADMIN) ---
                with aba_senha:
                    st.info("Redefinir senha de um usuário.")
                    if not df_users.empty:
                        # Selectbox para escolher a vítima
                        opcoes_reset = df_users.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}", axis=1)
                        user_reset_sel = st.selectbox("Selecione o Usuário", options=opcoes_reset, key='sel_reset')
                        
                        new_pass_admin = st.text_input("Nova Senha para ele(a)", type="password", key='pass_reset')
                        
                        if st.button("Confirmar Troca de Senha"):
                            if not new_pass_admin:
                                st.warning("Digite a nova senha.")
                            else:
                                id_alvo_reset = user_reset_sel.split(' - ')[0]
                                ok, msg = backend.alterar_senha_usuario(id_alvo_reset, new_pass_admin)
                                if ok: st.success(msg)
                                else: st.error(msg)

                # --- ABA 3: EXCLUIR USUÁRIO ---
                with aba_excluir:
                    st.warning("Cuidado: Ação permanente.")
                    if not df_users.empty:
                        # Recria opções para não dar conflito de key
                        opcoes_del = df_users.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}", axis=1)
                        user_del_sel = st.selectbox("Selecione para excluir", options=opcoes_del, key='sel_del')
                        
                        if st.button("🔥 Excluir Usuário"):
                            id_alvo = user_del_sel.split(' - ')[0]
                            sucesso, justificativa = backend.excluir_usuario(id_alvo)
                            if sucesso: st.success(justificativa); time.sleep(1.5); st.rerun()
                            else: st.error(justificativa)
                    else:
                        st.info("Nenhum usuário.")

        else:
            st.error("Acesso restrito. Apenas Master ou Administrativo podem gerenciar usuários.")

    # --- ABA 6: REGRAS (CATÁLOGO DE PRODUTOS) ---
    with tab6:
        if st.session_state['tipo_acesso'] in ['Master', 'Administrativo']:
            st.header("⚙️ Catálogo de Produtos e Regras")
            
            df_regras = backend.carregar_regras_df()
            
            # Seletor de Ação
            col_sel1, col_sel2 = st.columns([1, 3])
            acao_regra = col_sel1.radio("Ação:", ["Novo Produto", "Editar Existente"], label_visibility="collapsed")
            
            dados_edit = {}
            if acao_regra == "Editar Existente":
                lista_prods = sorted(df_regras['tipo_cota'].unique()) if not df_regras.empty else []
                prod_sel = col_sel2.selectbox("Selecione o Produto para Editar", lista_prods)
                if prod_sel:
                    dados_edit = df_regras[df_regras['tipo_cota'] == prod_sel].iloc[0].to_dict()
            
            st.divider()
            
            # --- FORMULÁRIO COMPLETO ---
            with st.form("form_produto_completo"):
                # 1. Identificação
                st.subheader("1. Identificação do Produto")
                c1, c2, c3 = st.columns(3)
                val_admin = dados_edit.get('administradora', 'Embracon')
                val_tipo = dados_edit.get('tipo_cota', '')
                val_id = dados_edit.get('id_tabela', '')
                
                input_admin = c1.text_input("Administradora", value=val_admin)
                input_tipo = c2.text_input("Nome do Produto (Tipo Cota)", value=val_tipo, disabled=(acao_regra=="Editar Existente"), help="Nome único. Ex: Imovel Premium")
                input_id_tab = c3.text_input("ID Tabela (Cód. Interno)", value=val_id, help="Código usado na importação. Ex: 1050")
                
                # 2. Parâmetros de Crédito e Prazo
                st.subheader("2. Parâmetros de Crédito e Prazo")
                c4, c5, c6, c7 = st.columns(4)
                v_min_cred = float(dados_edit.get('min_credito', 0.0))
                v_max_cred = float(dados_edit.get('max_credito', 0.0))
                v_min_prz = int(dados_edit.get('min_prazo', 0))
                v_max_prz = int(dados_edit.get('max_prazo', 0))
                
                input_min_cred = c4.number_input("Mín. Crédito (R$)", value=v_min_cred, step=1000.0)
                input_max_cred = c5.number_input("Máx. Crédito (R$)", value=v_max_cred, step=1000.0)
                input_min_prz = c6.number_input("Mín. Prazo (Meses)", value=v_min_prz)
                input_max_prz = c7.number_input("Máx. Prazo (Meses)", value=v_max_prz)
                
                # 3. Taxas e Contemplação
                st.subheader("3. Taxas e Contemplação")
                c8, c9, c10, c11 = st.columns(4)
                v_taxa_ant = float(dados_edit.get('taxa_antecipada', 0.0))
                
                # --- Lógica Refinada para Ref. Antecipada (Selectbox) ---
                opcoes_ref = ["1a Parcela", "Crédito", "Parcelado 12x", "2 primeiras parcelas"]
                v_ref_banco = str(dados_edit.get('ref_taxa_antecipada', '1a Parcela'))
                # Se o valor do banco não estiver na lista (legado), usa o primeiro
                idx_ref = opcoes_ref.index(v_ref_banco) if v_ref_banco in opcoes_ref else 0
                
                v_min_taxa = float(dados_edit.get('min_taxa_adm', 0.0))
                v_max_taxa = float(dados_edit.get('max_taxa_adm', 0.0))
                
                input_taxa_ant = c8.number_input("Taxa Antecipada (%)", value=v_taxa_ant)
                input_ref_ant = c9.selectbox("Ref. Antecipada", options=opcoes_ref, index=idx_ref)
                input_min_tx = c10.number_input("Mín. Taxa Adm (%)", value=v_min_taxa)
                input_max_tx = c11.number_input("Máx. Taxa Adm (%)", value=v_max_taxa)
                
                c12, c13, c14 = st.columns(3)
                v_fr = float(dados_edit.get('fundo_reserva', 0.0))
                v_emb = float(dados_edit.get('pct_lance_embutido', 0.0))
                v_idx = dados_edit.get('indice_reajuste', 'INCC')
                
                lista_indices = ["INCC", "IGPM", "IPCA"]
                idx_selecionado = lista_indices.index(v_idx) if v_idx in lista_indices else 0

                input_fr = c12.number_input("Fundo Reserva (%)", value=v_fr)
                input_emb = c13.number_input("% Lance Embutido", value=v_emb)
                input_idx = c14.selectbox("Índice Reajuste", lista_indices, index=idx_selecionado)
                
                # --- Lógica Refinada para Modalidades (Multiselect) ---
                opcoes_mods = ["Sorteio", "Lance Livre", "Lance Fixo", "Lance Embutido"]
                v_mods_str = str(dados_edit.get('modalidades_contemplacao', ''))
                # Converte string do banco ("Sorteio, Lance Fixo") para lista limpa
                v_mods_default = [x.strip() for x in v_mods_str.split(',') if x.strip() in opcoes_mods]
                
                input_mods = st.multiselect("Modalidades de Contemplação", options=opcoes_mods, default=v_mods_default)
                
                # 4. Estorno e Comissao
                st.subheader("4. Regras Financeiras (Comissão & Estorno)")
                ce1, ce2 = st.columns(2)
                v_pct_est = float(dados_edit.get('pct_estorno', 0.0))
                v_lim_est = int(dados_edit.get('limite_parcela_estorno', 3))
                
                input_pct_est = ce1.number_input("% Multa Estorno (sobre Crédito)", value=v_pct_est)
                input_lim_est = ce2.number_input("Limite Parcela Estorno", value=v_lim_est)
                
                st.info("Fluxo de Pagamento da Admin para a Empresa:")
                v_lista = dados_edit.get('lista_percentuais', '')
                input_lista = st.text_area("Percentuais por Parcela (separados por vírgula)", value=v_lista, help="Ex: 1.5, 1.0, 1.0, 0.5")

                # Botão Salvar
                if st.form_submit_button("💾 Salvar Produto Completo"):
                    if not input_tipo or not input_admin:
                        st.warning("Preencha pelo menos Administradora e Nome do Produto.")
                    else:
                        # TRATAMENTO ESPECIAL: Ordena e junta as modalidades
                        mods_final_string = ", ".join(sorted(input_mods))
                        
                        dados_salvar = {
                            'administradora': input_admin,
                            'tipo_cota': input_tipo,
                            'id_tabela': input_id_tab,
                            'lista_percentuais': input_lista,
                            
                            'min_credito': input_min_cred, 'max_credito': input_max_cred,
                            'min_prazo': input_min_prz, 'max_prazo': input_max_prz,
                            
                            'taxa_antecipada': input_taxa_ant, 'ref_taxa_antecipada': input_ref_ant,
                            'min_taxa_adm': input_min_tx, 'max_taxa_adm': input_max_tx,
                            'fundo_reserva': input_fr,
                            
                            'pct_lance_embutido': input_emb, 
                            'indice_reajuste': input_idx,    
                            'modalidades_contemplacao': mods_final_string, # String ordenada salva aqui
                            
                            'pct_estorno': input_pct_est,
                            'limite_parcela_estorno': input_lim_est
                        }
                        
                        ok, msg = backend.salvar_regra_completa(dados_salvar)
                        if ok:
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
            
            # Tabela de Visualização
            st.divider()
            with st.expander("Ver Catálogo Completo em Tabela"):
                st.dataframe(df_regras)

        else:
            st.error("Acesso restrito.")

    # --- ABA 7: CLIENTES (CRM) ---
    with tab7:
        st.header("📇 Ficha do Cliente & Histórico")
        
        dfc = backend.carregar_clientes()
        # Recarrega dados financeiros para garantir atualização
        df_vendas = backend.carregar_dados()

        # --- LÓGICA DE SEGURANÇA (CRM) ---
        # Se não for Master/Adm, só vê clientes da própria carteira
        if cargo not in ['Master', 'Administrativo']:
            meus_clientes = []
            if not df_vendas.empty:
                # Pega clientes onde sou Vendedor OU Gerente
                mask = (df_vendas['ID_Vendedor'] == meu_id) | (df_vendas['ID_Gerente'] == meu_id)
                meus_clientes = df_vendas[mask]['Cliente'].unique()
            # Filtra a base de clientes
            dfc = dfc[dfc['nome_completo'].isin(meus_clientes)]

        # --- LAYOUT DA TELA ---
        col_esq, col_dir = st.columns([1, 3])
        
        # COLUNA ESQUERDA: SELEÇÃO E CADASTRO
        with col_esq:
            st.subheader("Cadastro")
            opts = [""] + sorted(dfc['nome_completo'].unique()) if not dfc.empty else []
            sel_cliente = st.selectbox("Selecione o Cliente", opts)
            
            if sel_cliente:
                # Pega dados do cliente selecionado
                d_cli = dfc[dfc['nome_completo'] == sel_cliente].iloc[0]
                
                with st.form("form_crm"):
                    st.text_input("ID Interno", d_cli['id_cliente'], disabled=True)
                    email = st.text_input("Email", value=str(d_cli['email']))
                    tel = st.text_input("Telefone", value=str(d_cli['telefone']))
                    obs = st.text_area("Observações", value=str(d_cli['obs']), height=150)
                    
                    if st.form_submit_button("💾 Salvar Alterações"):
                        backend.salvar_cliente_manual(
                            d_cli['id_cliente'], 
                            d_cli['nome_completo'], 
                            email, 
                            tel, 
                            obs
                        )
                        st.success("Dados atualizados!")
                        time.sleep(1)
                        st.rerun()
        
        # COLUNA DIREITA: DASHBOARD FINANCEIRO DO CLIENTE
        with col_dir:
            if sel_cliente and not df_vendas.empty:
                st.subheader(f"📊 Extrato Financeiro: {sel_cliente}")
                
                # Filtra apenas as vendas deste cliente
                df_filtrado = df_vendas[df_vendas['Cliente'] == sel_cliente].copy()
                
                if df_filtrado.empty:
                    st.info("Este cliente não possui lançamentos financeiros ativos.")
                else:
                    # Ordena por data para ficar cronológico
                    if 'Data_Previsao' in df_filtrado.columns:
                        df_filtrado = df_filtrado.sort_values('Data_Previsao')

                    # Seleciona colunas ricas para exibir
                    cols_exibir = [
                        'ID_Lancamento',
                        'Grupo', 
                        'Cota', 
                        'Parcela', 
                        'Data_Previsao', 
                        'Receber_Administradora', # Valor da Parcela
                        'Status_Pgto_Cliente',    # Status do Cliente
                        'Vendedor',
                        'Gerente',
                        'Status_Recebimento'      # Status da Empresa (Repasse)
                    ]
                    
                    # Garante que as colunas existem antes de filtrar (evita erro se banco estiver velho)
                    cols_finais = [c for c in cols_exibir if c in df_filtrado.columns]
                    
                    # Exibe Tabela Formatada
                    st.dataframe(
                        df_filtrado[cols_finais],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Data_Previsao": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                            "Receber_Administradora": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                            "Status_Pgto_Cliente": st.column_config.TextColumn("Status Cliente", help="Se o cliente pagou o boleto"),
                            "Status_Recebimento": st.column_config.TextColumn("Repasse Admin", help="Se a empresa já recebeu a comissão")
                        }
                    )
                    
                    # Resumo Rápido (Cards abaixo da tabela)
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    total_pendente = df_filtrado[df_filtrado['Status_Pgto_Cliente'] != 'Pago']['Receber_Administradora'].sum()
                    total_pago = df_filtrado[df_filtrado['Status_Pgto_Cliente'] == 'Pago']['Receber_Administradora'].sum()
                    prox_venc = df_filtrado[df_filtrado['Status_Pgto_Cliente'] != 'Pago']['Data_Previsao'].min()
                    
                    c1.metric("Total Pago pelo Cliente", f"R$ {total_pago:,.2f}")
                    c2.metric("Total em Aberto", f"R$ {total_pendente:,.2f}")
                    if pd.notna(prox_venc):
                        c3.metric("Próximo Vencimento", prox_venc.strftime('%d/%m/%Y'))
            
            elif not sel_cliente:
                st.info("👈 Selecione um cliente na lista ao lado para ver o histórico.")

    # --- ABA 8: AJUSTES E EXCLUSÃO ---
    with tab8:
        if cargo in ['Master', 'Administrativo']:
            st.header("🛠️ Ajustes e Correções")
            
            tab_adj1, tab_adj2 = st.tabs(["📝 Edição em Lote", "🗑️ Exclusão em Lote"])
            
            # --- SUB-ABA 1: EDIÇÃO ---
            with tab_adj1:
                st.info("Use para corrigir dados errados (Ex: Vendedor, Datas). O sistema mostra o motivo se algo não mudar.")
                up_edit = st.file_uploader("Upload Planilha de Ajuste", type=['xlsx'], key='up_adjust')
                
                if up_edit and st.button("Processar Alterações"):
                    df_up = pd.read_excel(up_edit)
                    qtd, df_log = backend.processar_edicao_lote(df_up)
                    
                    if qtd > 0: st.success(f"✅ {qtd} registros atualizados!")
                    else: st.warning("⚠️ Nenhuma alteração realizada.")
                    
                    if not df_log.empty:
                        st.dataframe(df_log, use_container_width=True)

            # --- SUB-ABA 2: EXCLUSÃO ---
            with tab_adj2:
                st.error("⚠️ CUIDADO: Esta ação remove o registro do banco de dados permanentemente.")
                st.markdown("Suba um Excel contendo apenas a coluna **ID_Lancamento** das vendas que deseja apagar.")
                
                up_del = st.file_uploader("Upload Lista para Excluir", type=['xlsx'], key='up_del')
                
                if up_del:
                    st.warning("Tem certeza? Isso não pode ser desfeito.")
                    if st.button("🔥 CONFIRMAR EXCLUSÃO"):
                        df_del = pd.read_excel(up_del)
                        qtd_del, log_del = backend.processar_exclusao_lote(df_del)
                        
                        if qtd_del > 0: st.success(f"🗑️ {qtd_del} registros foram excluídos.")
                        else: st.info("Nenhum registro excluído.")
                        
                        if not log_del.empty:
                            st.dataframe(log_del, use_container_width=True)
        else:
            st.error("Acesso restrito.")

    # --- ABA 9: RECEBIMENTOS ---
    with tab9:
        if cargo in ['Master','Administrativo','Financeiro']:
            st.header("Recebimentos")
            m = st.radio("Modo", ["Pendente","Pago"], horizontal=True)
            dfa = backend.carregar_dados()
            t = 'Pago' if m=='Pago' else 'Pendente'
            v = dfa[dfa['Status_Pgto_Cliente']==t].copy()
            v['Sel']=False
            ed = st.data_editor(v[['Sel','ID_Lancamento','Cliente','Receber_Administradora','Data_Previsao']], key='ed9')
            sel = ed[ed['Sel']==True]
            if not sel.empty:
                st.metric("Total", sel['Receber_Administradora'].sum())
                nt = 'Pendente' if m=='Pago' else 'Pago'
                if st.button("Alterar Status"): backend.alterar_status_cliente_lote(sel['ID_Lancamento'].tolist(), nt); st.rerun()

    # --- ABA 10: COMISSÕES ---
    with tab10:
        if cargo in ['Master','Administrativo','Financeiro']:
            st.header("Comissões")
            m = st.radio("Modo", ["Pendente","Pago"], horizontal=True, key='r10')
            dfa = backend.carregar_dados()
            t = 'Pago' if m=='Pago' else 'Pendente'
            rows = []
            for _,r in dfa.iterrows():
                if str(r.get('Status_Pgto_Vendedor','Pendente'))==t and r['Pagar_Vendedor']>0:
                    rows.append({'ID':r['ID_Lancamento'], 'Tipo':'Vendedor', 'Nome':r['Vendedor'], 'Valor':r['Pagar_Vendedor'], 'Cx':r['Status_Recebimento']})
                if str(r.get('Status_Pgto_Gerente','Pendente'))==t and r['Pagar_Gerente']>0:
                    rows.append({'ID':r['ID_Lancamento'], 'Tipo':'Gerente', 'Nome':r['Gerente'], 'Valor':r['Pagar_Gerente'], 'Cx':r['Status_Recebimento']})
            
            if rows:
                dv = pd.DataFrame(rows)
                if st.checkbox("Só liberados pelo Admin", True): dv = dv[dv['Cx']=='Pago']
                dv['Sel']=False
                ed = st.data_editor(dv, key='ed10')
                s = ed[ed['Sel']==True]
                if not s.empty:
                    st.metric("Total", s['Valor'].sum())
                    nt = 'Pendente' if m=='Pago' else 'Pago'
                    if st.button("Pagar/Estornar"):
                        l = [{'id':r['ID'],'tipo':r['Tipo'],'status':nt} for _,r in s.iterrows()]
                        backend.processar_baixa_comissoes_lote(l); st.rerun()

if 'logado' not in st.session_state: st.session_state['logado']=False
if not st.session_state['logado']: tela_login()
else: main()