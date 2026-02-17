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
    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state['nome']}**")
        st.caption(f"Cargo: {st.session_state['tipo_acesso']}")
        
        with st.expander("🔐 Alterar Minha Senha"):
            with st.form("form_minha_senha"):
                s1 = st.text_input("Nova Senha", type="password")
                s2 = st.text_input("Confirmar", type="password")
                if st.form_submit_button("Trocar"):
                    if s1 and s1==s2: 
                        ok, m = backend.alterar_senha_usuario(st.session_state['id_usuario'], s1)
                        if ok: st.success(m)
                        else: st.error(m)
                    else: st.error("Senhas inválidas")
        
        st.divider()
        if st.button("Sair"): st.session_state['logado']=False; st.rerun()

    st.title("💰 Sistema de Gestão de Comissões")
    
    # Carrega DF e garante segurança
    df = backend.carregar_dados()
    if df.empty:
        cols = ['ID_Lancamento','ID_Vendedor','ID_Gerente','Data_Previsao','Status_Recebimento','Receber_Administradora','Liquido_Caixa','Status_Pgto_Cliente','Cliente','Vendedor','Gerente','Pagar_Vendedor','Pagar_Gerente','Administradora','Status_Pgto_Vendedor','Status_Pgto_Gerente']
        df = pd.DataFrame(columns=cols)

    # =========================================================================
    # CONFIGURAÇÃO DE ACESSO ÀS ABAS (DINÂMICO)
    # =========================================================================
    
    # Definição: Quem pode ver o quê?
    PERMISSOES = {
        "📊 Dashboard":        ['Master', 'Administrativo', 'Financeiro', 'Gerente', 'Vendedor'],
        "📥 Entuba":           ['Master', 'Administrativo'],
        "🏦 Conciliação":      ['Master', 'Administrativo'], # <--- Admin adicionado
        "❌ Cancelamentos":    ['Master', 'Administrativo'], # <--- Admin adicionado
        "👥 Usuários":         ['Master', 'Administrativo'],
        "⚙️ Regras":           ['Master', 'Administrativo'],
        "📇 Clientes":         ['Master', 'Administrativo', 'Financeiro', 'Gerente', 'Vendedor'],
        "🛠️ Ajustes":          ['Master', 'Administrativo'],
        "💰 Recebimentos":     ['Master', 'Administrativo', 'Financeiro'],
        "💸 Comissões":        ['Master', 'Administrativo', 'Financeiro']
    }

    cargo_atual = st.session_state['tipo_acesso']
    
    # Filtra apenas as abas que o usuário pode ver
    abas_visiveis = [nome for nome, cargos in PERMISSOES.items() if cargo_atual in cargos]
    
    # Cria as abas visualmente
    if not abas_visiveis:
        st.error("Seu perfil não tem acesso a nenhuma funcionalidade. Contate o suporte.")
        return

    # O Streamlit cria os objetos das abas
    objetos_abas = st.tabs(abas_visiveis)
    
    # Cria um dicionário para acessar as abas pelo nome: {'📊 Dashboard': tab_object, ...}
    mapa_abas = dict(zip(abas_visiveis, objetos_abas))

    # =========================================================================
    # RENDERIZAÇÃO DAS ABAS (Só entra no IF se a aba existir no mapa)
    # =========================================================================

    # --- ABA: DASHBOARD ---
    if "📊 Dashboard" in mapa_abas:
        with mapa_abas["📊 Dashboard"]:
            # Prepara filtros
            df['Vendedor'] = df['Vendedor'].fillna('').astype(str)
            df['Cliente'] = df['Cliente'].fillna('').astype(str)
            df['Administradora'] = df['Administradora'].fillna('').astype(str)
            df['ID_Vendedor'] = df['ID_Vendedor'].fillna('0').astype(str).str.replace('.0','', regex=False)
            df['ID_Gerente'] = df['ID_Gerente'].fillna('0').astype(str).str.replace('.0','', regex=False)
            df['Data_Previsao'] = pd.to_datetime(df['Data_Previsao'], errors='coerce')
            df['Mes_Referencia'] = df['Data_Previsao'].dt.strftime('%Y-%m')

            meu_id = st.session_state['id_usuario']
            dfv = df.copy()
            
            # Row Level Security
            if cargo_atual not in ['Master', 'Administrativo']:
                dfv = dfv[(dfv['ID_Vendedor']==meu_id) | (dfv['ID_Gerente']==meu_id)]
                
            dfv['Minha_Comissao'] = 0.0
            if cargo_atual in ['Master', 'Administrativo']:
                dfv['Minha_Comissao'] = dfv['Liquido_Caixa']
            else:
                m_v = dfv['ID_Vendedor'] == meu_id; m_g = dfv['ID_Gerente'] == meu_id
                if 'Pagar_Vendedor' in dfv: dfv.loc[m_v, 'Minha_Comissao'] += dfv.loc[m_v, 'Pagar_Vendedor']
                if 'Pagar_Gerente' in dfv: dfv.loc[m_g, 'Minha_Comissao'] += dfv.loc[m_g, 'Pagar_Gerente']

            with st.expander("🔍 Filtros Avançados", expanded=False):
                c1,c2,c3 = st.columns(3)
                f_mes = c1.multiselect("Mês", sorted(dfv['Mes_Referencia'].dropna().unique()))
                f_adm = c2.multiselect("Administradora", sorted(dfv['Administradora'].unique()))
                f_cli = c3.multiselect("Cliente", sorted(dfv['Cliente'].unique()))
                c4,c5 = st.columns(2)
                f_vend = c4.multiselect("Vendedor", sorted(dfv['Vendedor'].unique()))
                
            if f_mes: dfv = dfv[dfv['Mes_Referencia'].isin(f_mes)]
            if f_adm: dfv = dfv[dfv['Administradora'].isin(f_adm)]
            if f_cli: dfv = dfv[dfv['Cliente'].isin(f_cli)]
            if f_vend: dfv = dfv[dfv['Vendedor'].isin(f_vend)]
            
            k1,k2,k3 = st.columns(3)
            if cargo_atual in ['Master', 'Administrativo']:
                pend = dfv[dfv['Status_Recebimento']!='Pago']['Receber_Administradora'].sum()
                pago = dfv[dfv['Status_Recebimento']=='Pago']['Receber_Administradora'].sum()
                liq = dfv['Liquido_Caixa'].sum()
                k1.metric("A Receber", f"R$ {pend:,.2f}"); k2.metric("Recebido", f"R$ {pago:,.2f}"); k3.metric("Líquido", f"R$ {liq:,.2f}")
            else:
                pend = dfv[dfv['Status_Recebimento']!='Pago']['Minha_Comissao'].sum()
                pago = dfv[dfv['Status_Recebimento']=='Pago']['Minha_Comissao'].sum()
                k1.metric("Futuro", f"R$ {pend:,.2f}"); k2.metric("Liberado", f"R$ {pago:,.2f}")

            st.divider()
            if not dfv.empty:
                g1, g2 = st.columns(2)
                g1.bar_chart(dfv.groupby('Mes_Referencia')['Minha_Comissao'].sum())
                if 'Administradora' in dfv.columns: g2.bar_chart(dfv.groupby('Administradora')['Minha_Comissao'].sum())
            
            dft = dfv.copy()
            if cargo_atual not in ['Master', 'Administrativo']:
                dft = dft.drop(columns=['Receber_Administradora','Liquido_Caixa'], errors='ignore')
                dft.loc[dft['ID_Vendedor']!=meu_id, 'Pagar_Vendedor'] = None
                dft.loc[dft['ID_Gerente']!=meu_id, 'Pagar_Gerente'] = None
            st.dataframe(dft, use_container_width=True)

    # --- ABA: ENTUBA ---
    if "📥 Entuba" in mapa_abas:
        with mapa_abas["📥 Entuba"]:
            st.header("Upload Vendas")
            up = st.file_uploader("Excel", type=['xlsx'], key='up_entuba')
            if up and st.button("Processar Arquivo"):
                ok, ig, logs = backend.processar_vendas_upload(pd.read_excel(up))
                c1,c2=st.columns(2)
                if ok>0: c1.success(f"✅ {ok} gerados")
                else: c1.warning("Nada gerado")
                if ig>0: c2.info(f"⚠️ {ig} ignorados")
                
                if not logs.empty:
                    st.divider(); st.subheader("Relatório")
                    def color(v): return f'color: {"green" if "Sucesso" in v else "red" if "Erro" in v else "orange"}'
                    st.dataframe(logs.style.applymap(color, subset=['Status']), use_container_width=True)

    # --- ABA: CONCILIAÇÃO ---
    if "🏦 Conciliação" in mapa_abas:
        with mapa_abas["🏦 Conciliação"]:
            st.header("Conciliação")
            c_inf, c_up = st.columns([1,2])
            with c_inf: st.info("Obrigatório: Grupo, Cota, Valor_Pago")
            with c_up: up = st.file_uploader("Extrato", type=['xlsx'], key='conc')
            if up and st.button("Baixar"):
                b, logs = backend.processar_conciliacao_upload(pd.read_excel(up))
                st.success(f"{b} Baixados")
                if not logs.empty:
                    def color(v): return f'color: {"green" if "Sucesso" in v else "red"}'
                    st.dataframe(logs.style.applymap(color, subset=['Status']), use_container_width=True)

    # --- ABA: CANCELAMENTOS ---
    if "❌ Cancelamentos" in mapa_abas:
        with mapa_abas["❌ Cancelamentos"]:
            st.header("Cancelamentos")
            up = st.file_uploader("Planilha (ID_Venda, Parcela_Cancelamento)", type=['xlsx'], key='canc')
            if up and st.button("Processar"):
                c, logs = backend.processar_cancelamento_inteligente(pd.read_excel(up))
                st.success(f"{c} Processados")
                if not logs.empty: st.dataframe(logs, use_container_width=True)

    # --- ABA: USUÁRIOS ---
    if "👥 Usuários" in mapa_abas:
        with mapa_abas["👥 Usuários"]:
            st.header("Usuários")
            cl, cf = st.columns([2,1])
            dfu = backend.carregar_usuarios_df()
            with cl: st.dataframe(dfu[['id_usuario','nome_completo','username','tipo_acesso','taxa_vendedor','taxa_gerencia']], use_container_width=True)
            with cf:
                tab_n, tab_s, tab_e = st.tabs(["Novo", "Senha", "Excluir"])
                with tab_n:
                    with st.form("new_u"):
                        uid=st.text_input("ID"); nm=st.text_input("Nome"); lg=st.text_input("Login"); pw=st.text_input("Senha",type="password")
                        tp=st.selectbox("Perfil", ["Vendedor","Gerente","Administrativo","Master"]); tv=st.number_input("Tx Vend",0.2); tg=st.number_input("Tx Ger",0.1)
                        if st.form_submit_button("Criar"): backend.adicionar_novo_usuario(uid,nm,lg,pw,tp,tv,tg); st.rerun()
                with tab_s:
                    if not dfu.empty:
                        us = st.selectbox("Usuário", dfu.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}",1), key='s_res')
                        np = st.text_input("Nova Senha", type="password", key='np_res')
                        if st.button("Alterar"): backend.alterar_senha_usuario(us.split(' - ')[0], np); st.success("OK")
                with tab_e:
                    if not dfu.empty:
                        ud = st.selectbox("Excluir", dfu.apply(lambda x: f"{x['id_usuario']} - {x['nome_completo']}",1), key='s_del')
                        if st.button("🔥 Confirmar"):
                            ok, msg = backend.excluir_usuario(ud.split(' - ')[0])
                            if ok: st.success(msg); time.sleep(1); st.rerun()
                            else: st.error(msg)

    # --- ABA: REGRAS ---
    if "⚙️ Regras" in mapa_abas:
        with mapa_abas["⚙️ Regras"]:
            st.header("Catálogo")
            dfr = backend.carregar_regras_df()
            acao = st.radio("Ação", ["Novo", "Editar"], horizontal=True)
            dd = {}
            if acao=="Editar":
                s = st.selectbox("Produto", dfr['tipo_cota'].unique() if not dfr.empty else [])
                if s: dd = dfr[dfr['tipo_cota']==s].iloc[0].to_dict()
            
            with st.form("reg"):
                c1,c2,c3 = st.columns(3)
                adm=c1.text_input("Admin", value=dd.get('administradora','Embracon'))
                tpc=c2.text_input("Nome", value=dd.get('tipo_cota',''), disabled=acao=="Editar")
                idt=c3.text_input("ID Tabela", value=dd.get('id_tabela',''))
                
                c4,c5,c6,c7 = st.columns(4)
                mnc=c4.number_input("Min Cred", value=float(dd.get('min_credito',0)))
                mxc=c5.number_input("Max Cred", value=float(dd.get('max_credito',0)))
                mnp=c6.number_input("Min Prz", value=int(dd.get('min_prazo',0)))
                mxp=c7.number_input("Max Prz", value=int(dd.get('max_prazo',0)))
                
                c8,c9,c10,c11 = st.columns(4)
                txa=c8.number_input("Tx Ant", value=float(dd.get('taxa_antecipada',0)))
                
                opts_ref = ["1a Parcela", "Crédito", "Parcelado 12x", "2 primeiras parcelas"]
                v_ref = str(dd.get('ref_taxa_antecipada', '1a Parcela'))
                idx_ref = opts_ref.index(v_ref) if v_ref in opts_ref else 0
                rta=c9.selectbox("Ref Ant", opts_ref, index=idx_ref)
                
                mnt=c10.number_input("Min Tx", value=float(dd.get('min_taxa_adm',0)))
                mxt=c11.number_input("Max Tx", value=float(dd.get('max_taxa_adm',0)))
                
                c12,c13,c14 = st.columns(3)
                fr=c12.number_input("F. Res", value=float(dd.get('fundo_reserva',0)))
                emb=c13.number_input("L. Emb", value=float(dd.get('pct_lance_embutido',0)))
                
                l_idx = ["INCC", "IGPM", "IPCA"]
                v_idx = dd.get('indice_reajuste', 'INCC')
                idx_sel = l_idx.index(v_idx) if v_idx in l_idx else 0
                idx=c14.selectbox("Indice", l_idx, index=idx_sel)
                
                op_mods = ["Sorteio", "Lance Livre", "Lance Fixo", "Lance Embutido"]
                v_mod_str = str(dd.get('modalidades_contemplacao',''))
                v_mod_def = [x.strip() for x in v_mod_str.split(',') if x.strip() in op_mods]
                mods = st.multiselect("Modalidades", op_mods, default=v_mod_def)
                
                pct=st.text_area("Percentuais (1.5, 1.0)", value=dd.get('lista_percentuais',''))
                ce1,ce2=st.columns(2)
                pest=ce1.number_input("% Estorno", value=float(dd.get('pct_estorno',0)))
                lim=ce2.number_input("Lim Estorno", value=int(dd.get('limite_parcela_estorno',3)))
                
                if st.form_submit_button("Salvar"):
                    save_d = {
                        'administradora':adm, 'tipo_cota':tpc, 'id_tabela':idt, 'lista_percentuais':pct,
                        'min_credito':mnc, 'max_credito':mxc, 'min_prazo':mnp, 'max_prazo':mxp,
                        'taxa_antecipada':txa, 'ref_taxa_antecipada':rta, 'min_taxa_adm':mnt, 'max_taxa_adm':mxt,
                        'fundo_reserva':fr, 'pct_lance_embutido':emb, 'indice_reajuste':idx, 
                        'modalidades_contemplacao': ", ".join(sorted(mods)),
                        'pct_estorno':pest, 'limite_parcela_estorno':lim
                    }
                    backend.salvar_regra_completa(save_d); st.rerun()
            st.dataframe(dfr)

    # --- ABA: CLIENTES ---
    if "📇 Clientes" in mapa_abas:
        with mapa_abas["📇 Clientes"]:
            st.header("Clientes")
            
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
            
            # LAYOUT
            c1, c2 = st.columns([1, 3])
            
            # --- COLUNA ESQUERDA: SELEÇÃO E CADASTRO ---
            with c1:
                lista_clientes = [""] + sorted(dfc['nome_completo'].unique().tolist()) if not dfc.empty else []
                sel = st.selectbox("Cliente", lista_clientes)
                
                if sel:
                    # Pega dados cadastrais
                    d = dfc[dfc['nome_completo'] == sel].iloc[0]
                    with st.form("crm"):
                        st.text_input("ID", d['id_cliente'], disabled=True)
                        e = st.text_input("Email", str(d['email']))
                        t = st.text_input("Tel", str(d['telefone']))
                        o = st.text_area("Obs", str(d['obs']))
                        if st.form_submit_button("Salvar"): 
                            backend.salvar_cliente_manual(d['id_cliente'], d['nome_completo'], e, t, o)
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
                        
                        st.subheader(f"Extrato: {sel}")
                        
                        st.dataframe(dff[[
                            'ID_Lancamento', 'Grupo', 'Cota', 'Parcela', 
                            'Data_Previsao', 'Receber_Administradora', 
                            'Status_Pgto_Cliente', 'Status_Recebimento'
                        ]], use_container_width=True, hide_index=True, column_config={
                            "Data_Previsao": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                            "Receber_Administradora": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                        })
                        
                        # Métricas (Baseadas no DFF já filtrado, ou seja, só o que eu posso ver)
                        c_a, c_b = st.columns(2)
                        pago = dff[dff['Status_Pgto_Cliente'] == 'Pago']['Receber_Administradora'].sum()
                        pend = dff[dff['Status_Pgto_Cliente'] != 'Pago']['Receber_Administradora'].sum()
                        c_a.metric("Total Pago (Minha Visão)", f"R$ {pago:,.2f}")
                        c_b.metric("Total Pendente (Minha Visão)", f"R$ {pend:,.2f}")
                    else:
                        st.info("Nenhum registro financeiro vinculado ao seu usuário para este cliente.")

    # --- ABA: AJUSTES ---
    if "🛠️ Ajustes" in mapa_abas:
        with mapa_abas["🛠️ Ajustes"]:
            t1, t2 = st.tabs(["Edição", "Exclusão"])
            with t1:
                up = st.file_uploader("Upload Edição", type=['xlsx'], key='adj')
                if up and st.button("Processar"):
                    q, log = backend.processar_edicao_lote(pd.read_excel(up))
                    st.success(f"{q} Alterados")
                    def c(v): return f'color: {"green" if "Sucesso" in v else "red" if "Bloqueado" in v else "orange"}'
                    if not log.empty: st.dataframe(log.style.applymap(c, subset=['Status']), use_container_width=True)
            with t2:
                upd = st.file_uploader("Upload Exclusão (ID_Lancamento)", type=['xlsx'], key='del')
                if upd and st.button("🔥 Excluir"):
                    q, log = backend.processar_exclusao_lote(pd.read_excel(upd))
                    st.success(f"{q} Excluídos")
                    if not log.empty: st.dataframe(log, use_container_width=True)

    # --- ABA: RECEBIMENTOS ---
    if "💰 Recebimentos" in mapa_abas:
        with mapa_abas["💰 Recebimentos"]:
            st.header("Recebimentos")
            m = st.radio("Visão", ["Pendente", "Pago"], horizontal=True)
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

    # --- ABA: COMISSÕES ---
    if "💸 Comissões" in mapa_abas:
        with mapa_abas["💸 Comissões"]:
            st.header("Comissões")
            m = st.radio("Visão", ["Pendente", "Pago"], horizontal=True, key='r10')
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