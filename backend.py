# backend.py
import pandas as pd
import streamlit as st
from sqlalchemy import text
from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib
from database import engine, SessionLocal
from models import Lancamento, Usuario, Cliente, RegraComissao
import bcrypt


# --- MAPEAMENTO DE COLUNAS (SQL -> APP) ---
MAPA_SQL_APP = {
    'id_lancamento': 'ID_Lancamento', 'id_venda': 'ID_Venda', 'valor_cliente': 'Valor_Cliente',
    'administradora': 'Administradora', 'grupo': 'Grupo', 'cota': 'Cota', 'tipo_cota': 'Tipo_Cota',
    'parcela': 'Parcela', 'data_previsao': 'Data_Previsao',
    'data_real_recebimento': 'Data_Real_Recebimento', 'valor_recebido_real': 'Valor_Recebido_Real',
    'id_cliente': 'ID_Cliente', 'cliente': 'Cliente',
    'id_vendedor': 'ID_Vendedor', 'vendedor': 'Vendedor',
    'id_supervisor': 'ID_Supervisor', 'supervisor': 'Supervisor',
    'id_gerente': 'ID_Gerente', 'gerente': 'Gerente',
    'receber_administradora': 'Receber_Administradora',
    'pagar_vendedor': 'Pagar_Vendedor', 'pagar_supervisor': 'Pagar_Supervisor', 'pagar_gerente': 'Pagar_Gerente',
    'liquido_caixa': 'Liquido_Caixa',
    'status_recebimento': 'Status_Recebimento', 'status_pgto_cliente': 'Status_Pgto_Cliente',
    'status_pgto_vendedor': 'Status_Pgto_Vendedor', 'status_pgto_supervisor': 'Status_Pgto_Supervisor', 'status_pgto_gerente': 'Status_Pgto_Gerente',
    'obs': 'Obs'
}

def limpar_id(val):
    if pd.isna(val) or str(val).strip() == '': return None
    return str(val).strip().replace('.0', '')

def gerar_hash(senha):
    # Converte a senha para bytes (necessário para o bcrypt nativo)
    senha_bytes = str(senha).encode('utf-8')
    # Corta em 72 bytes para blindar contra o erro da nuvem
    senha_segura = senha_bytes[:72]
    # Gera o hash e devolve como string para gravar no MySQL
    return bcrypt.hashpw(senha_segura, bcrypt.gensalt()).decode('utf-8')

def verificar_hash(senha_digitada, hash_armazenado):
    try:
        # Prepara a senha digitada
        senha_bytes = str(senha_digitada).encode('utf-8')
        senha_segura = senha_bytes[:72]
        # Prepara o hash que veio do banco de dados
        hash_bytes = str(hash_armazenado).encode('utf-8')
        # Faz a comparação segura nativa
        return bcrypt.checkpw(senha_segura, hash_bytes)
    except Exception as e:
        return False

# --- LEITURA COM LIMPEZA PARA OS FILTROS ---
@st.cache_data(ttl=300, show_spinner=False) # Mantém na memória por 5 minutos (300 segundos)
def carregar_dados():
    try:
        # Lê do SQL
        df = pd.read_sql("SELECT * FROM financeiro_mestre", engine)
        
        # Traduz nomes
        df = df.rename(columns=MAPA_SQL_APP)
        
        # --- LIMPEZA CRÍTICA PARA FILTROS ---
        # Se isso não for feito, os filtros ficam vazios ou com duplicatas sujas
        cols_texto = ['Vendedor', 'Gerente', 'Cliente', 'Status_Recebimento', 'Status_Pgto_Cliente']
        for col in cols_texto:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                # Converte "nan" string para vazio real
                df.loc[df[col].str.lower() == 'nan', col] = ''

        # Garante datas
        if 'Data_Previsao' in df.columns:
            df['Data_Previsao'] = pd.to_datetime(df['Data_Previsao'], errors='coerce')
            
        return df
    except Exception as e:
        print(f"Erro leitura SQL: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def carregar_usuarios_df():
    try: 
        df = pd.read_sql("SELECT * FROM usuarios", engine)
        # Limpa espaços que podem ter vindo da migração
        df['username'] = df['username'].str.strip()
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def carregar_clientes():
    try: return pd.read_sql("SELECT * FROM clientes", engine)
    except: return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def carregar_regras_df():
    try: return pd.read_sql("SELECT * FROM regras_comissao", engine)
    except: return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def carregar_regras_dict():
    df = carregar_regras_df()
    regras = {}
    for _, row in df.iterrows():
        try:
            raw_str = str(row['lista_percentuais']).replace(',', ' ')
            lista = [float(x) for x in raw_str.split() if x.strip()]
            regras[row['tipo_cota']] = {
                'admin': str(row.get('administradora', 'Embracon')).strip(),
                'pcts': lista,
                'id_tabela': str(row.get('id_tabela', '')),
                'min_credito': float(row.get('min_credito', 0)),
                'max_credito': float(row.get('max_credito', 0)),
                'min_prazo': int(row.get('min_prazo', 0)),
                'max_prazo': int(row.get('max_prazo', 0)),
                'taxa_antecipada': float(row.get('taxa_antecipada', 0)),
                'ref_taxa_antecipada': str(row.get('ref_taxa_antecipada', '')),
                'min_taxa_adm': float(row.get('min_taxa_adm', 0)),
                'max_taxa_adm': float(row.get('max_taxa_adm', 0)),
                'fundo_reserva': float(row.get('fundo_reserva', 0)),
                'indice_reajuste': str(row.get('indice_reajuste', '')),
                'modalidades_contemplacao': str(row.get('modalidades_contemplacao', '')),
                'pct_estorno': float(row.get('pct_estorno', 0)),
                'limite_parcela_estorno': int(row.get('limite_parcela_estorno', 3))
            }
        except: continue
    return regras

@st.cache_data(ttl=60, show_spinner=False)
def carregar_aprovacoes_pendentes():
    session = SessionLocal()
    try:
        engine = session.get_bind()
        # Lê apenas as que não foram aprovadas ou rejeitadas ainda
        df_pendentes = pd.read_sql("SELECT * FROM vendas_pendentes WHERE status_aprovacao = 'Pendente'", con=engine)
        return df_pendentes
    except:
        # Se for o primeiro dia de uso e a tabela ainda não existir no SQL, retorna vazio sem dar erro
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=60, show_spinner=False)
def carregar_meus_rascunhos(id_vendedor):
    session = SessionLocal()
    try:
        engine = session.get_bind()
        # Uso de query parametrizada para evitar injeção de SQL (Hacker)
        query = text("SELECT * FROM vendas_pendentes WHERE status_aprovacao = 'Rascunho' AND id_vendedor = :id")
        return pd.read_sql(query, con=engine, params={"id": id_vendedor})
    except:
        return pd.DataFrame()
    finally:
        session.close()

# --- ESCRITA ---
def adicionar_novo_usuario(id_u, nome, user, senha, tipo, tv, ts, tg, id_sup, id_ger):
    session = SessionLocal()
    try:
        user_clean = str(user).strip()
        existe = session.query(Usuario).filter((Usuario.id_usuario == str(id_u)) | (Usuario.username == user_clean)).first()
        if existe: return False, "ID ou Usuário já existe."
        
        # Garante que IDs de hierarquia fiquem limpos
        id_sup = limpar_id(id_sup)
        id_ger = limpar_id(id_ger)
        
        # --- LÓGICA DE AUTO-VINCULAÇÃO (CASCATA) ---
        # Se você selecionou um supervisor, o sistema ignora o gerente da tela e puxa o gerente do supervisor!
        if id_sup:
            supervisor_banco = session.query(Usuario).filter(Usuario.id_usuario == id_sup).first()
            if supervisor_banco and supervisor_banco.id_gerente:
                id_ger = supervisor_banco.id_gerente
        # -------------------------------------------
        
        novo = Usuario(
            id_usuario=str(id_u), 
            username=user_clean, 
            password_hash=gerar_hash(senha),
            nome_completo=str(nome).strip(), 
            tipo_acesso=str(tipo), 
            taxa_vendedor=float(tv), 
            taxa_supervisor=float(ts),
            taxa_gerencia=float(tg),
            id_supervisor=id_sup,
            id_gerente=id_ger
        )
        session.add(novo); session.commit()
        st.cache_data.clear()
        return True, "Cadastrado."
    except Exception as e: session.rollback(); return False, str(e)
    finally: session.close()

def excluir_usuario(id_u):
    session = SessionLocal()
    try:
        # 1. Proteção do Admin
        if str(id_u) == '1':
            return False, "⛔ Ação Bloqueada: Não é possível excluir o usuário Administrador Master (ID 1)."

        # 2. Verifica se o usuário existe
        usuario = session.query(Usuario).filter(Usuario.id_usuario == str(id_u)).first()
        if not usuario:
            return False, "❌ Erro: Usuário não encontrado no banco de dados."

        # 3. Proteção de Integridade (O Pulo do Gato)
        # Verifica se ele aparece como Vendedor ou Gerente em alguma venda
        vendas_vinculadas = session.query(Lancamento).filter(
            (Lancamento.id_vendedor == str(id_u)) | (Lancamento.id_gerente == str(id_u))
        ).count()

        if vendas_vinculadas > 0:
            return False, f"⚠️ Bloqueado: Este usuário possui {vendas_vinculadas} lançamentos financeiros vinculados. Você não pode excluí-lo pois isso quebraria o histórico. Sugestão: Apenas mude a senha dele para bloquear o acesso."

        # 4. Se passou por tudo, exclui
        session.delete(usuario)
        session.commit()
        st.cache_data.clear()
        return True, f"✅ Sucesso: Usuário '{usuario.nome_completo}' foi excluído permanentemente."

    except Exception as e:
        session.rollback()
        return False, f"❌ Erro Crítico no Banco: {str(e)}"
    finally:
        session.close()

def salvar_cliente_manual(id_c, nome, email, tel, obs):
    session = SessionLocal()
    try:
        cli = session.query(Cliente).get(str(id_c))
        if cli: cli.nome_completo=nome; cli.email=email; cli.telefone=tel; cli.obs=obs; msg="Atualizado"
        else: session.add(Cliente(id_cliente=str(id_c), nome_completo=nome, email=email, telefone=tel, obs=obs)); msg="Criado"
        session.commit()
        st.cache_data.clear()
        return True, msg
    except Exception as e: session.rollback(); return False, str(e)
    finally: session.close()

def auto_cadastrar_clientes_novos(lista_nomes):
    session = SessionLocal()
    c = 0
    try:
        exist = {x.nome_completo.lower() for x in session.query(Cliente.nome_completo).all()}
        res = session.execute(text("SELECT MAX(CAST(id_cliente AS UNSIGNED)) FROM clientes")).scalar()
        pid = (res or 0) + 1
        for n in lista_nomes:
            nl = str(n).strip()
            if nl.lower() not in exist and nl != '':
                session.add(Cliente(id_cliente=str(pid), nome_completo=nl, obs='Auto')); pid+=1; c+=1
                exist.add(nl.lower())
        session.commit(); return c
    except: session.rollback(); return 0
    finally: session.close()

def salvar_regra_completa(d):
    session = SessionLocal()
    try:
        session.query(RegraComissao).filter_by(tipo_cota=d['tipo_cota']).delete()
        m = d.get('modalidades_contemplacao'); 
        if isinstance(m, list): m = ", ".join(m)
        session.add(RegraComissao(
            tipo_cota=d['tipo_cota'], administradora=d['administradora'], id_tabela=d['id_tabela'],
            lista_percentuais=d['lista_percentuais'], min_credito=d['min_credito'], max_credito=d['max_credito'],
            min_prazo=d['min_prazo'], max_prazo=d['max_prazo'], taxa_antecipada=d['taxa_antecipada'],
            ref_taxa_antecipada=d['ref_taxa_antecipada'], min_taxa_adm=d['min_taxa_adm'], max_taxa_adm=d['max_taxa_adm'],
            fundo_reserva=d['fundo_reserva'], pct_lance_embutido=d['pct_lance_embutido'],
            indice_reajuste=d['indice_reajuste'], modalidades_contemplacao=m,
            pct_estorno=d['pct_estorno'], limite_parcela_estorno=d['limite_parcela_estorno']
        ))
        st.cache_data.clear()
        session.commit()
        st.cache_data.clear()
        return True, "Salvo"
    except Exception as e: session.rollback(); return False, str(e)
    finally: session.close()

# --- PROCESSAMENTO ENTUBA ---
def processar_vendas_upload(df):
    REGRAS = carregar_regras_dict()
    if not REGRAS: return 0, 0, pd.DataFrame([{'Status': 'Erro Crítico', 'Detalhe': 'Nenhuma regra de comissão cadastrada (Aba 6)'}])
    
    # Busca o DataFrame completo de regras para o cálculo do Valor do Cliente
    df_regras_full = carregar_regras_df()
    regras_completas = df_regras_full.set_index('tipo_cota').to_dict('index') if not df_regras_full.empty else {}
    
    # Padroniza Excel
    df.columns = df.columns.str.strip().str.lower()
    
    mapa_tab = {limpar_id(v['id_tabela']): k for k,v in REGRAS.items() if v.get('id_tabela')}
    
    df_u = carregar_usuarios_df()
    map_u = dict(zip(df_u['id_usuario'], df_u['nome_completo']))
    map_tv = dict(zip(df_u['id_usuario'], pd.to_numeric(df_u.get('taxa_vendedor', 0.2)).fillna(0.2)))
    map_ts = dict(zip(df_u['id_usuario'], pd.to_numeric(df_u.get('taxa_supervisor', 0.1)).fillna(0.1))) # <-- NOVO
    map_tg = dict(zip(df_u['id_usuario'], pd.to_numeric(df_u.get('taxa_gerencia', 0.1)).fillna(0.1)))
    
    # Mapas de Inteligência (Puxa quem é o chefe do Vendedor)
    map_sup_link = dict(zip(df_u['id_usuario'], df_u.get('id_supervisor', pd.Series([''] * len(df_u))).fillna('')))
    map_ger_link = dict(zip(df_u['id_usuario'], df_u.get('id_gerente', pd.Series([''] * len(df_u))).fillna('')))
    
    df_c = carregar_clientes()
    map_cid = dict(zip(df_c['id_cliente'], df_c['nome_completo']))
    map_cnm = dict(zip(df_c['nome_completo'].str.lower().str.strip(), df_c['id_cliente']))
    try: pcid = int(pd.to_numeric(df_c['id_cliente']).max()) + 1
    except: pcid = 1
    
    session = SessionLocal()
    exist = {x[0] for x in session.query(Lancamento.id_lancamento).all()}
    
    novos = []; ncli_obj = []; logs = []; ign = 0; ok = 0
    
    for idx, row in df.iterrows():
        linha_excel = idx + 2
        cliente_nome = str(row.get('cliente', 'Desc.')).strip()
        
        tipo = row.get('tipo_cota')
        if not tipo and 'id_tabela' in row: tipo = mapa_tab.get(limpar_id(row['id_tabela']))
        
        if not tipo or tipo not in REGRAS: 
            logs.append({'Linha': linha_excel, 'Cliente': cliente_nome, 'Status': '❌ Erro', 'Detalhe': 'Produto/Regra não encontrado'})
            continue
        
        reg = REGRAS[tipo]
        reg_c = regras_completas.get(tipo, {}) 
        
        iv = limpar_id(row.get('id_vendedor'))
        if iv not in map_u: 
            logs.append({'Linha': linha_excel, 'Cliente': cliente_nome, 'Status': '❌ Erro', 'Detalhe': f'Vendedor ID {iv} inexistente'})
            continue
            
        # --- PREENCHIMENTO AUTOMÁTICO DA HIERARQUIA ---
        isup = map_sup_link.get(iv)
        ig = map_ger_link.get(iv)
        
        # Caso a planilha venha com um gerente forçado, ele acata. Se não, usa o automático do banco.
        if not isup and 'id_supervisor' in row: isup = limpar_id(row.get('id_supervisor'))
        if not ig and 'id_gerente' in row: ig = limpar_id(row.get('id_gerente'))
        
        cnm = cliente_nome
        cid_xls = limpar_id(row.get('id_cliente'))
        cid_final = None
        
        if cid_xls and cid_xls in map_cid: 
            cid_final=cid_xls; cnm=map_cid[cid_xls]
        elif cnm.lower() in map_cnm: 
            cid_final=map_cnm[cnm.lower()]
        else:
            cid_final = str(pcid)
            ncli_obj.append(Cliente(id_cliente=cid_final, nome_completo=cnm, obs='Auto Entuba'))
            map_cnm[cnm.lower()] = cid_final; pcid+=1
            logs.append({'Linha': linha_excel, 'Cliente': cnm, 'Status': 'Info', 'Detalhe': 'Novo cliente cadastrado'})

        grp = str(row.get('grupo')).replace('.0',''); cta = str(row.get('cota')).replace('.0','')
        idv = f"{reg.get('admin', reg_c.get('administradora', ''))}_{grp}_{cta}"
        
        try: dtv = pd.to_datetime(row['data_venda'], dayfirst=True)
        except: logs.append({'Linha': linha_excel, 'Cliente': cnm, 'Status': '❌ Erro', 'Detalhe': 'Data inválida'}); continue

        dc = int(row.get('dia_vencimento', 15))
        sh = 1 if dtv.day >= dc else 0
        vcred = float(row.get('valor_credito', 0))
        
        # --- MATEMÁTICA PADRÃO DO VALOR DO CLIENTE ---
        prazo_venda = pd.to_numeric(row.get('prazo'), errors='coerce')
        if pd.isna(prazo_venda) or prazo_venda <= 0: prazo_venda = float(reg_c.get('max_prazo', 1))

        taxa_adm_venda = pd.to_numeric(row.get('taxa_adm'), errors='coerce')
        if pd.isna(taxa_adm_venda): taxa_adm_venda = float(reg_c.get('max_taxa_adm', 0))

        fundo_res = float(reg_c.get('fundo_reserva', 0))
        taxa_antecipada = float(reg_c.get('taxa_antecipada', 0))

        valor_taxa_adm = vcred * (taxa_adm_venda / 100.0)
        valor_fundo_res = vcred * (fundo_res / 100.0)
        valor_antecipacao = vcred * (taxa_antecipada / 100.0)

        total_divida = vcred + valor_taxa_adm + valor_fundo_res
        saldo_restante = total_divida - valor_antecipacao
        parcela_normal = saldo_restante / prazo_venda if prazo_venda > 0 else 0
        primeira_parcela = parcela_normal + valor_antecipacao

        # --- NOVO: OVERRIDE MANUAL SE PREENCHIDO NA PLANILHA ---
        val_pri_manual = pd.to_numeric(row.get('valor_primeira_parcela'), errors='coerce')
        val_dem_manual = pd.to_numeric(row.get('valor_demais_parcelas'), errors='coerce')

        if pd.notna(val_pri_manual) and val_pri_manual > 0:
            primeira_parcela = val_pri_manual
            
        if pd.notna(val_dem_manual) and val_dem_manual > 0:
            parcela_normal = val_dem_manual

        # --- GERAÇÃO DAS PARCELAS ---
        pcts = reg['pcts']
        parcelas_criadas_na_linha = 0
        total_parcelas_fixo = 12
        
        for i in range(total_parcelas_fixo):
            idl = f"{idv}_P{i+1}"
            if idl in exist: 
                ign += 1; continue
            
            dp = dtv if i==0 else dtv+relativedelta(months=i+sh)
            pct = pcts[i] if i < len(pcts) else 0.0
            
            valor_cliente_atual = primeira_parcela if i == 0 else parcela_normal
            status_pg_cli = 'Pago' if i == 0 else 'Pendente'
            
            # --- NOVO: STATUS INTELIGENTE ---
            status_pg_sup = 'Pendente' if isup else 'Isento'
            status_pg_ger = 'Pendente' if ig else 'Isento'
            
            vb = vcred * (pct/100)
            pv = vb * map_tv.get(iv, 0.2)
            ps = vb * map_ts.get(isup, 0.1) if isup else 0.0
            pg = vb * map_tg.get(ig, 0.1) if ig else 0.0
            
            novos.append(Lancamento(
                id_lancamento=idl, id_venda=idv, administradora=reg.get('admin', reg_c.get('administradora')),
                grupo=grp, cota=cta, tipo_cota=tipo, 
                parcela=f"{i+1}/{total_parcelas_fixo}",
                data_previsao=dp.date(), id_cliente=cid_final, cliente=cnm,
                id_vendedor=iv, vendedor=map_u.get(iv,''), 
                id_supervisor=isup, supervisor=map_u.get(isup,''),
                id_gerente=ig, gerente=map_u.get(ig,''), 
                valor_cliente=round(valor_cliente_atual, 2), 
                receber_administradora=round(vb,2), 
                pagar_vendedor=round(pv,2), pagar_supervisor=round(ps,2), pagar_gerente=round(pg,2),
                liquido_caixa=round(vb-pv-ps-pg, 2), 
                status_recebimento='Pendente', status_pgto_cliente=status_pg_cli,
                status_pgto_vendedor='Pendente', 
                status_pgto_supervisor=status_pg_sup, # Recebe 'Isento' se vazio
                status_pgto_gerente=status_pg_ger     # Recebe 'Isento' se vazio
            ))
            exist.add(idl); parcelas_criadas_na_linha += 1; ok += 1
        
        if parcelas_criadas_na_linha > 0:
            logs.append({'Linha': linha_excel, 'Cliente': cnm, 'Status': '✅ Sucesso', 'Detalhe': f'{parcelas_criadas_na_linha} parcelas geradas'})
        else:
             logs.append({'Linha': linha_excel, 'Cliente': cnm, 'Status': '⚠️ Ignorado', 'Detalhe': 'Todas as parcelas já existiam'})

    try:
        if ncli_obj: session.add_all(ncli_obj)
        if novos: session.add_all(novos)
        session.commit()
        st.cache_data.clear()
    except Exception as e: 
        session.rollback()
        logs.append({'Linha': '-', 'Cliente': '-', 'Status': '❌ Erro Fatal', 'Detalhe': str(e)})
        return 0, 0, pd.DataFrame(logs)
    finally: 
        session.close()
    
    return ok, ign, pd.DataFrame(logs)

def processar_conciliacao_upload(df):
    session = SessionLocal()
    df.columns = df.columns.str.lower().str.strip()
    
    logs = []
    sucesso_count = 0
    
    # 1. Validação de Colunas Obrigatórias
    cols_obrigatorias = ['grupo', 'cota', 'valor_pago']
    faltantes = [c for c in cols_obrigatorias if c not in df.columns]
    if faltantes:
        return 0, pd.DataFrame([{'Status': 'Erro Crítico', 'Detalhe': f'Colunas faltando no Excel: {faltantes}'}])

    try:
        for idx, row in df.iterrows():
            linha = idx + 2
            
            # Normaliza Grupo e Cota
            g = str(row.get('grupo', '')).replace('.0', '').strip()
            c = str(row.get('cota', '')).replace('.0', '').strip()
            
            # Tenta ler o Valor
            try:
                val_pago = float(row.get('valor_pago', 0))
            except:
                logs.append({'Linha': linha, 'Grupo/Cota': f"{g}/{c}", 'Status': '❌ Erro', 'Detalhe': 'Valor Pago inválido (não numérico)'})
                continue

            # Tenta ler o Número da Parcela (Se houver)
            num_parcela = None
            if 'num_parcela' in df.columns:
                raw_p = str(row.get('num_parcela', ''))
                # Tenta extrair "1" de "1/60" ou "Parcela 1"
                try: 
                    num_parcela = int(raw_p.split('/')[0].lower().replace('parcela', '').strip())
                except: 
                    pass
            
            # --- BUSCA NO BANCO ---
            query = session.query(Lancamento).filter(Lancamento.grupo == g, Lancamento.cota == c)
            
            # Se tiver número da parcela, filtra por ela
            if num_parcela:
                # Busca parcela que começa com o número (ex: "1/100")
                query = query.filter(Lancamento.parcela.like(f"{num_parcela}/%"))
            else:
                # Se não tem parcela no Excel, tenta achar a mais antiga PENDENTE com valor próximo
                query = query.filter(Lancamento.status_recebimento != 'Pago')
            
            lancs_encontrados = query.all()
            
            if not lancs_encontrados:
                logs.append({
                    'Linha': linha, 
                    'Grupo/Cota': f"{g}/{c}", 
                    'Status': '⚠️ Não Encontrado', 
                    'Detalhe': f'Venda não existe ou parcela {num_parcela} incorreta'
                })
                continue
            
            # Pega o primeiro candidato (ou o único)
            l = lancs_encontrados[0]
            
            # --- VALIDAÇÕES DE REGRA DE NEGÓCIO ---
            
            # 1. Já está pago?
            if l.status_recebimento == 'Pago':
                logs.append({
                    'Linha': linha, 
                    'Grupo/Cota': f"{g}/{c}", 
                    'Parcela': l.parcela,
                    'Status': '⚠️ Já Baixado', 
                    'Detalhe': f'Esta parcela já consta como paga em {l.data_real_recebimento or "Data N/A"}'
                })
                continue
                
            # 2. Valor bate? (Aceita diferença de centavos até 1.00)
            diferenca = abs(l.receber_administradora - val_pago)
            if diferenca > 1.00:
                logs.append({
                    'Linha': linha, 
                    'Grupo/Cota': f"{g}/{c}", 
                    'Parcela': l.parcela,
                    'Status': '⛔ Divergência', 
                    'Detalhe': f'Esperado: R$ {l.receber_administradora:.2f} | Veio: R$ {val_pago:.2f}'
                })
                continue
            
            # --- EXECUTA A BAIXA ---
            l.status_recebimento = 'Pago'
            l.valor_recebido_real = val_pago
            l.data_real_recebimento = datetime.now().date()
            
            # Atualiza status do cliente também (opcional, depende da sua regra)
            # l.status_pgto_cliente = 'Pago' 
            
            sucesso_count += 1
            logs.append({
                'Linha': linha, 
                'Grupo/Cota': f"{g}/{c}", 
                'Parcela': l.parcela,
                'Status': '✅ Sucesso', 
                'Detalhe': f'Baixado R$ {val_pago:.2f}'
            })

        if sucesso_count > 0:
            session.commit()
            st.cache_data.clear()
            
    except Exception as e:
        session.rollback()
        logs.append({'Linha': '-', 'Status': '❌ Erro Fatal', 'Detalhe': str(e)})
        return 0, pd.DataFrame(logs)
    finally:
        session.close()

    return sucesso_count, pd.DataFrame(logs)

def processar_cancelamento_inteligente(df):
    REGRAS = carregar_regras_dict()
    session = SessionLocal()
    
    # Normaliza Excel
    df.columns = df.columns.str.lower().str.strip()
    
    count_alterados = 0
    logs = []
    
    try:
        for idx, row in df.iterrows():
            linha_excel = idx + 2
            id_venda = str(row.get('id_venda', '')).strip()
            
            # Validação básica
            if not id_venda:
                logs.append({'Linha': linha_excel, 'Venda': '-', 'Status': '❌ Erro', 'Detalhe': 'ID Venda vazio'})
                continue
                
            try:
                parcela_corte = int(row.get('parcela_cancelamento'))
            except:
                logs.append({'Linha': linha_excel, 'Venda': id_venda, 'Status': '❌ Erro', 'Detalhe': 'Parcela inválida (deve ser número)'})
                continue
            
            # Busca todos os lançamentos dessa venda
            lancs = session.query(Lancamento).filter_by(id_venda=id_venda).all()
            
            if not lancs:
                logs.append({'Linha': linha_excel, 'Venda': id_venda, 'Status': '❌ Erro', 'Detalhe': 'Venda não encontrada no banco'})
                continue
            
            # Identifica Regra para cálculo de estorno
            tipo_cota = lancs[0].tipo_cota
            regra = REGRAS.get(tipo_cota, {})
            limite_estorno = regra.get('limite_parcela_estorno', 3)
            pct_multa = regra.get('pct_estorno', 0.0)
            
            # --- LÓGICA DE VERIFICAÇÃO (JÁ ESTÁ CANCELADO?) ---
            qtd_futuras = 0
            qtd_ja_canceladas = 0
            
            # Identifica quais parcelas deveriam ser canceladas
            lancs_futuros = []
            for l in lancs:
                # Ignora linha de estorno se já existir
                if 'EST' in l.id_lancamento: continue
                
                try: num_parcela = int(l.parcela.split('/')[0])
                except: continue
                
                if num_parcela > parcela_corte:
                    lancs_futuros.append(l)
                    qtd_futuras += 1
                    if l.status_recebimento == 'Cancelado':
                        qtd_ja_canceladas += 1
            
            # SE TODAS AS FUTURAS JÁ ESTÃO CANCELADAS, IGNORA
            if qtd_futuras > 0 and qtd_futuras == qtd_ja_canceladas:
                logs.append({
                    'Linha': linha_excel, 
                    'Venda': id_venda, 
                    'Status': '⚠️ Ignorado', 
                    'Detalhe': f'Venda já cancelada a partir da parc {parcela_corte}'
                })
                continue
            
            if qtd_futuras == 0:
                logs.append({
                    'Linha': linha_excel, 
                    'Venda': id_venda, 
                    'Status': '⚠️ Aviso', 
                    'Detalhe': 'Nenhuma parcela futura encontrada para cancelar'
                })
                continue

            # --- EXECUTA O CANCELAMENTO ---
            for l in lancs_futuros:
                l.status_recebimento = 'Cancelado'
                l.status_pgto_cliente = 'Cancelado'
                l.receber_administradora = 0.0
                l.pagar_vendedor = 0.0
                l.pagar_supervisor = 0.0
                l.pagar_gerente = 0.0
                l.liquido_caixa = 0.0
                if hasattr(l, 'valor_cliente'):
                    l.valor_cliente = 0.0
            
            msg_sucesso = f"{len(lancs_futuros)} parcelas canceladas."
            
            # --- CÁLCULO DE ESTORNO (MULTA) ---
            # Só gera estorno se o cancelamento for precoce (ex: antes da parcela 3)
            if parcela_corte <= limite_estorno and pct_multa > 0:
                id_estorno = f"{id_venda}_EST"
                
                # Verifica se estorno já existe
                estorno_existente = session.query(Lancamento).get(id_estorno)
                
                if not estorno_existente:
                    # Calcula crédito base (Engenharia reversa da comissão recebida)
                    credito_estimado = 0.0
                    for l in lancs:
                        if l.receber_administradora > 0 and 'EST' not in l.id_lancamento:
                            try:
                                idx = int(l.parcela.split('/')[0]) - 1
                                if idx < len(regra['pcts']):
                                    # Valor / % = Crédito
                                    credito_estimado = l.receber_administradora / (regra['pcts'][idx] / 100)
                                    break
                            except: pass
                    
                    if credito_estimado > 0:
                        valor_multa = -1 * (credito_estimado * (pct_multa / 100))
                        
                        estorno_obj = Lancamento(
                            id_lancamento=id_estorno,
                            id_venda=id_venda,
                            administradora=lancs[0].administradora,
                            grupo=lancs[0].grupo,
                            cota=lancs[0].cota,
                            tipo_cota=tipo_cota,
                            parcela="Estorno",
                            data_previsao=datetime.now().date(),
                            id_cliente=lancs[0].id_cliente,
                            cliente=lancs[0].cliente,
                            id_vendedor=lancs[0].id_vendedor,
                            vendedor=lancs[0].vendedor,
                            id_gerente=lancs[0].id_gerente,
                            gerente=lancs[0].gerente,
                            valor_cliente=0.0,
                            receber_administradora=valor_multa,
                            pagar_vendedor=0,
                            pagar_gerente=0,
                            pagar_supervisor=0,
                            liquido_caixa=valor_multa,
                            status_recebimento='Estorno',
                            status_pgto_cliente='Estorno',
                            status_pgto_vendedor='Isento',
                            status_pgto_supervisor='Isento',
                            status_pgto_gerente='Isento'
                        )
                        session.add(estorno_obj)
                        msg_sucesso += f" Multa de {valor_multa:.2f} gerada."
            
            logs.append({
                'Linha': linha_excel, 
                'Venda': id_venda, 
                'Status': '✅ Sucesso', 
                'Detalhe': msg_sucesso
            })
            count_alterados += 1

        if count_alterados > 0:
            session.commit()
            st.cache_data.clear()
            
    except Exception as e:
        session.rollback()
        logs.append({'Linha': '-', 'Venda': '-', 'Status': '❌ Erro Fatal', 'Detalhe': str(e)})
        return 0, pd.DataFrame(logs)
    finally:
        session.close()

    return count_alterados, pd.DataFrame(logs)

def processar_edicao_lote(df):
    session = SessionLocal()
    count_alterados = 0
    logs = [] 
    
    # Normaliza colunas
    df.columns = df.columns.str.lower().str.strip()
    
    # Carrega lookups
    users = {u.id_usuario: u for u in session.query(Usuario).all()}
    
    # Lista Negra (Campos que não podem mudar nunca)
    COLUNAS_PROIBIDAS = ['administradora', 'parcela', 'tipo_cota', 'id_venda', 'grupo', 'cota', 'id_lancamento']

    for _, row in df.iterrows():
        # Identifica ID
        id_lanc = str(row.get('id_lancamento', '')).strip()
        if not id_lanc: continue
        
        l = session.query(Lancamento).get(id_lanc)
        
        if not l:
            logs.append({'ID': id_lanc, 'Status': '❌ Erro', 'Detalhe': 'ID não encontrado no banco'})
            continue
            
        recalc_financeiro = False
        
        for col in df.columns:
            # Pula coluna de ID e colunas que não existem no modelo
            if col == 'id_lancamento' or not hasattr(l, col): 
                continue 
            
            val_novo = row[col]
            if pd.isna(val_novo): continue # Pula vazios
            
            s_val_novo = str(val_novo).replace('.0', '').strip()
            val_atual = str(getattr(l, col) or '').strip()
            
            # CENÁRIO 1: VALOR IDÊNTICO (IGNORA)
            if val_atual == s_val_novo:
                logs.append({
                    'ID': id_lanc,
                    'Status': '⚠️ Ignorado',
                    'Detalhe': f"Campo '{col}' já é '{val_atual}'"
                })
                continue

            # CENÁRIO 2: VALOR DIFERENTE (TENTA ALTERAR)
            
            # Trava Estrutural
            if col in COLUNAS_PROIBIDAS:
                logs.append({
                    'ID': id_lanc, 
                    'Status': '⛔ Bloqueado', 
                    'Detalhe': f"Campo '{col}' é estrutural (blindado)"
                })
                continue

            # Travas Financeiras
            if col == 'id_vendedor' and l.status_pgto_vendedor == 'Pago':
                logs.append({'ID': id_lanc, 'Status': '⛔ Bloqueado', 'Detalhe': 'Comissão Vendedor já paga'})
                continue
                
            if col == 'id_gerente' and l.status_pgto_gerente == 'Pago':
                logs.append({'ID': id_lanc, 'Status': '⛔ Bloqueado', 'Detalhe': 'Comissão Gerente já paga'})
                continue

            if col == 'receber_administradora' and l.status_recebimento == 'Pago':
                 logs.append({'ID': id_lanc, 'Status': '⛔ Bloqueado', 'Detalhe': 'Recebimento já baixado'})
                 continue

            # APLICA ALTERAÇÃO
            setattr(l, col, s_val_novo)
            count_alterados += 1
            
            logs.append({
                'ID': id_lanc, 
                'Status': '✅ Sucesso', 
                'Detalhe': f"{col}: {val_atual} -> {s_val_novo}"
            })
            
            # Flags de Recálculo
            if col in ['id_vendedor', 'id_gerente', 'receber_administradora']:
                recalc_financeiro = True

        # Recálculo de comissão
        if recalc_financeiro:
            tv = users[l.id_vendedor].taxa_vendedor if l.id_vendedor and l.id_vendedor in users else 0.20
            ts = users[l.id_supervisor].taxa_supervisor if l.id_supervisor and l.id_supervisor in users else 0.10
            tg = users[l.id_gerente].taxa_gerencia if l.id_gerente and l.id_gerente in users else 0.10
            
            try: r = float(l.receber_administradora)
            except: r = 0.0
            
            l.pagar_vendedor = r * tv
            l.pagar_supervisor = r * ts if l.id_supervisor else 0.0
            l.pagar_gerente = r * tg if l.id_gerente else 0.0
            l.liquido_caixa = r - l.pagar_vendedor - l.pagar_supervisor - l.pagar_gerente

            # --- NOVO: REAJUSTE DE STATUS AUTOMÁTICO ---
            if not l.id_supervisor: l.status_pgto_supervisor = 'Isento'
            elif l.status_pgto_supervisor == 'Isento': l.status_pgto_supervisor = 'Pendente'
            
            if not l.id_gerente: l.status_pgto_gerente = 'Isento'
            elif l.status_pgto_gerente == 'Isento': l.status_pgto_gerente = 'Pendente'

    if count_alterados > 0:
        try:
            session.commit()
            st.cache_data.clear()
        except Exception as e:
            session.rollback()
            logs.append({'ID': 'Geral', 'Status': '❌ Erro Crítico', 'Detalhe': str(e)})
            return 0, pd.DataFrame(logs)
            
    session.close()
    return count_alterados, pd.DataFrame(logs)

def processar_exclusao_lote(df):
    session = SessionLocal()
    count = 0
    logs = []
    
    # Normaliza
    df.columns = df.columns.str.lower().str.strip()
    
    # Assume que o ID está na primeira coluna ou numa coluna chamada 'id_lancamento'
    col_id = 'id_lancamento' if 'id_lancamento' in df.columns else df.columns[0]
    
    for _, row in df.iterrows():
        id_alvo = str(row[col_id]).strip()
        
        # Tenta achar para excluir
        l = session.query(Lancamento).get(id_alvo)
        
        if l:
            # Verifica se já está pago (Trava de Segurança opcional, mas recomendada)
            if l.status_recebimento == 'Pago' or l.status_pgto_vendedor == 'Pago':
                logs.append({'ID': id_alvo, 'Status': '⛔ Bloqueado', 'Detalhe': 'Registro possui valores pagos/recebidos'})
            else:
                session.delete(l)
                logs.append({'ID': id_alvo, 'Status': '🗑️ Excluído', 'Detalhe': 'Removido com sucesso'})
                count += 1
        else:
            logs.append({'ID': id_alvo, 'Status': '⚠️ Ignorado', 'Detalhe': 'ID não encontrado'})

    if count > 0:
        try:
            session.commit()
            st.cache_data.clear()
        except Exception as e:
            session.rollback()
            return 0, pd.DataFrame([{'ID': 'Erro', 'Status': 'Crítico', 'Detalhe': str(e)}])
            
    session.close()
    return count, pd.DataFrame(logs)

def alterar_status_cliente_lote(ids, stt):
    session = SessionLocal()
    try:
        session.query(Lancamento).filter(Lancamento.id_lancamento.in_(ids)).update({Lancamento.status_pgto_cliente: stt}, synchronize_session=False)
        session.commit()
        st.cache_data.clear()
        return len(ids), "OK"
    except Exception as e: session.rollback(); return 0, str(e)
    finally: session.close()

def processar_baixa_comissoes_lote(lista):
    session = SessionLocal()
    c=0
    try:
        for a in lista:
            l = session.query(Lancamento).get(str(a['id']))
            if l:
                if a['tipo']=='Vendedor': l.status_pgto_vendedor = a['status']
                else: l.status_pgto_gerente = a['status']
                c+=1
        session.commit()
        st.cache_data.clear()
        return c, "OK"
    except Exception as e: session.rollback(); return 0, str(e)
    finally: session.close()

def alterar_senha_usuario(id_user, nova_senha):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.id_usuario == str(id_user)).first()
        if not usuario:
            return False, "Usuário não encontrado."
        
        # Gera o novo hash
        novo_hash = gerar_hash(nova_senha)
        usuario.password_hash = novo_hash
        
        session.commit()
        st.cache_data.clear()
        return True, f"Senha de {usuario.nome_completo} alterada com sucesso!"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def atualizar_vinculo_usuario(id_u, id_sup, id_ger, tv, ts, tg):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.id_usuario == str(id_u)).first()
        if not usuario: return False, "Usuário não encontrado."
        
        # Limpa os IDs recebidos
        id_sup = limpar_id(id_sup)
        id_ger = limpar_id(id_ger)
        
        # --- LÓGICA DE AUTO-VINCULAÇÃO (CASCATA PARA CIMA) ---
        if id_sup:
            supervisor_banco = session.query(Usuario).filter(Usuario.id_usuario == id_sup).first()
            if supervisor_banco and supervisor_banco.id_gerente:
                id_ger = supervisor_banco.id_gerente
                
        # Atualiza os Vínculos
        usuario.id_supervisor = id_sup
        usuario.id_gerente = id_ger
        
        # --- ATUALIZA AS TAXAS DE COMISSÃO ---
        usuario.taxa_vendedor = float(tv)
        usuario.taxa_supervisor = float(ts)
        usuario.taxa_gerencia = float(tg)
        
        # --- LÓGICA DE AUTO-VINCULAÇÃO (CASCATA PARA BAIXO) ---
        if usuario.tipo_acesso == 'Supervisor':
            vendedores_abaixo = session.query(Usuario).filter(Usuario.id_supervisor == str(id_u)).all()
            for vend in vendedores_abaixo:
                vend.id_gerente = id_ger 
                
        session.commit()
        st.cache_data.clear()
        return True, f"✅ Cadastro de {usuario.nome_completo} atualizado com sucesso!"
    except Exception as e: 
        session.rollback()
        return False, f"Erro ao atualizar: {e}"
    finally: 
        session.close()

# --- FILA DE APROVAÇÕES DE VENDAS ---
def enviar_venda_aprovacao(id_vendedor, id_gerente, cliente, adm, produto, credito):
    # Cria o DataFrame com a venda
    nova_venda = pd.DataFrame([{
        "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_vendedor": id_vendedor,
        "id_gerente": id_gerente,
        "cliente": cliente,
        "administradora": adm,
        "tipo_cota": produto,
        "valor_credito": credito,
        "status_aprovacao": "Pendente"
    }])
    
    session = SessionLocal() # Abre a sua sessão configurada no secrets.toml
    try:
        engine = session.get_bind() # Pega o motor do banco de dados
        # O Pandas usa o seu motor para criar a tabela sozinho e inserir os dados!
        nova_venda.to_sql('vendas_pendentes', con=engine, if_exists='append', index=False)
        
        # Limpa o cache para a aba da Diretoria atualizar na hora
        st.cache_data.clear()
        return True, "Venda enviada para análise da diretoria!"
    except Exception as e:
        return False, f"Erro ao enviar: {e}"
    finally:
        session.close()

    session = SessionLocal()
    try:
        nova_venda = pd.DataFrame([{
            "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_vendedor": id_vendedor,
            "id_gerente": id_gerente,
            "cliente": cliente,
            "administradora": adm,
            "tipo_cota": produto,
            "valor_credito": credito,
            "grupo": 0,  # <-- BLINDAGEM 1: Força o MySQL a criar a coluna como INT
            "cota": 0,   # <-- BLINDAGEM 1: Força o MySQL a criar a coluna como INT
            "data_primeira_parcela": "", 
            "status_aprovacao": "Rascunho" 
        }])
        
        engine = session.get_bind()
        nova_venda.to_sql('vendas_pendentes', con=engine, if_exists='append', index=False)
        st.cache_data.clear()
        return True, "Proposta salva na sua gaveta de rascunhos!"
    except Exception as e:
        return False, f"Erro ao salvar rascunho: {e}"
    finally:
        session.close()

def completar_e_enviar_aprovacao(data_solicitacao, cliente, grupo, cota, data_primeira_parcela, dia_vencimento):
    session = SessionLocal()
    try:
        query = text("""
            UPDATE vendas_pendentes 
            SET grupo = :grupo, cota = :cota, data_primeira_parcela = :data_parcela, dia_vencimento = :dia_vencimento, status_aprovacao = 'Pendente' 
            WHERE Data_Solicitacao = :data AND cliente = :cliente
        """)
        session.execute(query, {
            "grupo": int(grupo), "cota": int(cota), 
            "data_parcela": data_primeira_parcela, 
            "dia_vencimento": int(dia_vencimento),  # <--- ATUALIZANDO O BANCO
            "data": data_solicitacao, "cliente": cliente
        })
        session.commit(); st.cache_data.clear()
        return True, "Venda enviada para aprovação do Backoffice!"
    except ValueError: return False, "⚠️ Erro: O Número do Grupo, Cota e Vencimento devem conter apenas números!"
    except Exception as e: session.rollback(); return False, f"Erro ao enviar venda: {e}"
    finally: session.close()

# --- FILA DE APROVAÇÕES E RASCUNHOS DE VENDAS ---
def salvar_proposta_rascunho(id_vendedor, id_supervisor, id_gerente, cliente, adm, produto, credito, prazo, taxa_adm):
    session = SessionLocal()
    try:
        nova_venda = pd.DataFrame([{
            "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_vendedor": id_vendedor,
            "id_supervisor": id_supervisor,
            "id_gerente": id_gerente,
            "cliente": cliente,
            "administradora": adm,
            "tipo_cota": produto,
            "valor_credito": credito,
            "prazo": prazo,        
            "taxa_adm": taxa_adm,  
            "grupo": 0,  
            "cota": 0,   
            "data_primeira_parcela": "", 
            "dia_vencimento": 15,
            "status_aprovacao": "Rascunho" 
        }])
        
        engine = session.get_bind()
        nova_venda.to_sql('vendas_pendentes', con=engine, if_exists='append', index=False)
        st.cache_data.clear()
        return True, "Proposta salva na sua gaveta de rascunhos!"
    except Exception as e:
        return False, f"Erro ao salvar rascunho: {e}"
    finally:
        session.close()

def processar_decisao_venda(data_solicitacao, cliente, decisao):
    session = SessionLocal()
    try:
        engine = session.get_bind()
        q_ok = 0; q_ig = 0; log_entuba = None

        if decisao == 'Aprovado':
            df_venda = pd.read_sql(
                f"SELECT * FROM vendas_pendentes WHERE Data_Solicitacao = '{data_solicitacao}' AND cliente = '{cliente}'", 
                con=engine
            ).head(1)
            
            df_entuba = df_venda.rename(columns={
                'cliente': 'Cliente',
                'id_vendedor': 'ID_Vendedor',
                'id_supervisor': 'ID_Supervisor', 
                'id_gerente': 'ID_Gerente',       
                'tipo_cota': 'Tipo_Cota',
                'valor_credito': 'Valor_Credito',
                'prazo': 'Prazo',         
                'taxa_adm': 'Taxa_Adm',   
                'grupo': 'Grupo', 
                'cota': 'Cota',
                'dia_vencimento': 'dia_vencimento'
            })
            
            df_entuba['Data_Venda'] = pd.to_datetime(df_entuba['data_primeira_parcela']).dt.strftime('%d/%m/%Y')
            df_entuba['Grupo'] = pd.to_numeric(df_entuba['Grupo'], errors='coerce').fillna(0).astype(int)
            df_entuba['Cota'] = pd.to_numeric(df_entuba['Cota'], errors='coerce').fillna(0).astype(int)
            
            # Inclui o dia_vencimento no pacote que vai para o Entuba
            df_final = df_entuba[['Cliente', 'ID_Vendedor', 'ID_Supervisor', 'ID_Gerente', 'Tipo_Cota', 'Valor_Credito', 'Prazo', 'Taxa_Adm', 'Data_Venda', 'Grupo', 'Cota', 'dia_vencimento']]
            
            q_ok, q_ig, log_entuba = processar_vendas_upload(df_final)
            if q_ok == 0:
                return False, "O Entuba rejeitou o lançamento. Verifique o log de erros.", q_ok, q_ig, log_entuba

        query_update = text("UPDATE vendas_pendentes SET status_aprovacao = :decisao WHERE Data_Solicitacao = :data AND cliente = :cliente")
        session.execute(query_update, {"decisao": decisao, "data": data_solicitacao, "cliente": cliente})
        session.commit()
            
        st.cache_data.clear()
        return True, f"Venda {decisao.lower()} com sucesso!", q_ok, q_ig, log_entuba
        
    except Exception as e:
        session.rollback()
        return False, f"Erro ao processar: {e}", 0, 0, None
    finally:
        session.close()


