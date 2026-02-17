# backend.py
import pandas as pd
import streamlit as st
from sqlalchemy import text
from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib
from database import engine, SessionLocal
from models import Lancamento, Usuario, Cliente, RegraComissao

# --- MAPEAMENTO DE COLUNAS (SQL -> APP) ---
MAPA_SQL_APP = {
    'id_lancamento': 'ID_Lancamento', 'id_venda': 'ID_Venda',
    'administradora': 'Administradora', 'grupo': 'Grupo', 'cota': 'Cota', 'tipo_cota': 'Tipo_Cota',
    'parcela': 'Parcela', 'data_previsao': 'Data_Previsao',
    'data_real_recebimento': 'Data_Real_Recebimento', 'valor_recebido_real': 'Valor_Recebido_Real',
    'id_cliente': 'ID_Cliente', 'cliente': 'Cliente',
    'id_vendedor': 'ID_Vendedor', 'vendedor': 'Vendedor',
    'id_gerente': 'ID_Gerente', 'gerente': 'Gerente',
    'receber_administradora': 'Receber_Administradora',
    'pagar_vendedor': 'Pagar_Vendedor', 'pagar_gerente': 'Pagar_Gerente',
    'liquido_caixa': 'Liquido_Caixa',
    'status_recebimento': 'Status_Recebimento', 'status_pgto_cliente': 'Status_Pgto_Cliente',
    'status_pgto_vendedor': 'Status_Pgto_Vendedor', 'status_pgto_gerente': 'Status_Pgto_Gerente',
    'obs': 'Obs'
}

def limpar_id(val):
    if pd.isna(val) or str(val).strip() == '': return None
    return str(val).strip().replace('.0', '')

def gerar_hash(senha):
    return hashlib.sha256(str(senha).encode()).hexdigest()

def realizar_backup():
    pass 

# --- LEITURA COM LIMPEZA PARA OS FILTROS ---
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

def carregar_usuarios_df():
    try: 
        df = pd.read_sql("SELECT * FROM usuarios", engine)
        # Limpa espaços que podem ter vindo da migração
        df['username'] = df['username'].str.strip()
        return df
    except: return pd.DataFrame()

def carregar_clientes():
    try: return pd.read_sql("SELECT * FROM clientes", engine)
    except: return pd.DataFrame()

def carregar_regras_df():
    try: return pd.read_sql("SELECT * FROM regras_comissao", engine)
    except: return pd.DataFrame()

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

# --- ESCRITA ---
def adicionar_novo_usuario(id_u, nome, user, senha, tipo, tv, tg):
    session = SessionLocal()
    try:
        # Verifica user limpo
        user_clean = str(user).strip()
        existe = session.query(Usuario).filter((Usuario.id_usuario == str(id_u)) | (Usuario.username == user_clean)).first()
        if existe: return False, "ID ou Usuário já existe."
        
        novo = Usuario(
            id_usuario=str(id_u), 
            username=user_clean, 
            password_hash=gerar_hash(senha),
            nome_completo=str(nome).strip(), 
            tipo_acesso=str(tipo), 
            taxa_vendedor=float(tv), 
            taxa_gerencia=float(tg)
        )
        session.add(novo); session.commit()
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
        session.commit(); return True, msg
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
        session.commit(); return True, "Salvo"
    except Exception as e: session.rollback(); return False, str(e)
    finally: session.close()

# --- PROCESSAMENTO ENTUBA ---
def processar_vendas_upload(df):
    REGRAS = carregar_regras_dict()
    if not REGRAS: return 0,0,["Sem regras. Cadastre na Aba 6."]
    
    # Padroniza Excel de entrada
    df.columns = df.columns.str.strip().str.lower()
    
    mapa_tab = {limpar_id(v['id_tabela']): k for k,v in REGRAS.items() if v.get('id_tabela')}
    
    df_u = carregar_usuarios_df()
    map_u = dict(zip(df_u['id_usuario'], df_u['nome_completo']))
    map_tv = dict(zip(df_u['id_usuario'], pd.to_numeric(df_u['taxa_vendedor']).fillna(0.2)))
    map_tg = dict(zip(df_u['id_usuario'], pd.to_numeric(df_u['taxa_gerencia']).fillna(0.1)))
    
    df_c = carregar_clientes()
    map_cid = dict(zip(df_c['id_cliente'], df_c['nome_completo']))
    map_cnm = dict(zip(df_c['nome_completo'].str.lower().str.strip(), df_c['id_cliente']))
    try: pcid = int(pd.to_numeric(df_c['id_cliente']).max()) + 1
    except: pcid = 1
    
    session = SessionLocal()
    exist = {x[0] for x in session.query(Lancamento.id_lancamento).all()}
    
    novos = []; err = []; ncli_obj = []; ign=0; ok=0
    
    for idx, row in df.iterrows():
        # Busca Tipo
        tipo = row.get('tipo_cota')
        if not tipo and 'id_tabela' in row: tipo = mapa_tab.get(limpar_id(row['id_tabela']))
        if not tipo or tipo not in REGRAS: err.append(f"L{idx+2}: Produto não identificado"); continue
        
        reg = REGRAS[tipo]
        
        # Busca Pessoas
        iv = limpar_id(row.get('id_vendedor'))
        ig = limpar_id(row.get('id_gerente'))
        if iv not in map_u: err.append(f"L{idx+2}: Vendedor ID {iv} não existe"); continue
        
        # Busca Cliente
        cnm = str(row.get('cliente')).strip()
        cid_xls = limpar_id(row.get('id_cliente'))
        cid_final = None
        
        if cid_xls and cid_xls in map_cid: cid_final=cid_xls; cnm=map_cid[cid_xls]
        elif cnm.lower() in map_cnm: cid_final=map_cnm[cnm.lower()]
        else:
            cid_final = str(pcid)
            ncli_obj.append(Cliente(id_cliente=cid_final, nome_completo=cnm, obs='Auto'))
            map_cnm[cnm.lower()] = cid_final; pcid+=1
            
        grp = str(row.get('grupo')).replace('.0',''); cta = str(row.get('cota')).replace('.0','')
        idv = f"{reg['admin']}_{grp}_{cta}"
        dtv = pd.to_datetime(row['data_venda'])
        dc = int(row.get('dia_vencimento', 15))
        sh = 1 if dtv.day >= dc else 0
        vcred = float(row.get('valor_credito', 0))
        
        pcts = reg['pcts']
        for i, pct in enumerate(pcts):
            idl = f"{idv}_P{i+1}"
            if idl in exist: ign+=1; continue
            
            dp = dtv if i==0 else dtv+relativedelta(months=i+sh)
            vb = vcred * (pct/100)
            pv = vb * map_tv.get(iv, 0.2); pg = vb * map_tg.get(ig, 0.1)
            
            novos.append(Lancamento(
                id_lancamento=idl, id_venda=idv, administradora=reg['admin'],
                grupo=grp, cota=cta, tipo_cota=tipo, parcela=f"{i+1}/{len(pcts)}",
                data_previsao=dp.date(), id_cliente=cid_final, cliente=cnm,
                id_vendedor=iv, vendedor=map_u[iv], id_gerente=ig, gerente=map_u.get(ig,''),
                receber_administradora=round(vb,2), pagar_vendedor=round(pv,2), pagar_gerente=round(pg,2),
                liquido_caixa=round(vb-pv-pg,2), status_recebimento='Pendente', status_pgto_cliente='Pendente'
            ))
            exist.add(idl); ok+=1
            
    try:
        if ncli_obj: session.add_all(ncli_obj)
        if novos: session.add_all(novos)
        session.commit()
    except Exception as e: session.rollback(); err.append(str(e))
    finally: session.close()
    return ok, ign, err

def processar_conciliacao_upload(df):
    session = SessionLocal()
    df.columns = df.columns.str.lower().str.strip()
    c=0; logs=[]
    try:
        for _, row in df.iterrows():
            g=str(row.get('grupo')).replace('.0',''); ct=str(row.get('cota')).replace('.0','')
            v=float(row.get('valor_pago',0))
            try: pn=int(str(row.get('num_parcela')).split('/')[0].replace('Parcela ',''))
            except: pn=0
            
            l = session.query(Lancamento).filter(Lancamento.grupo==g, Lancamento.cota==ct, Lancamento.parcela.like(f"{pn}/%")).first()
            log = {'Grupo':g, 'Cota':ct}
            if not l: log['Status']='Falha: Não encontrado'
            elif l.status_recebimento=='Pago': log['Status']='Alerta: Já pago'
            elif abs(l.receber_administradora - v) > 0.5: log['Status']='Falha: Valor divergente'
            else:
                l.status_recebimento='Pago'; l.valor_recebido_real=v; c+=1; log['Status']='Sucesso'
            logs.append(log)
        if c: session.commit()
        return c, pd.DataFrame(logs)
    except Exception as e: session.rollback(); return 0, pd.DataFrame([{'Erro':str(e)}])
    finally: session.close()

def processar_cancelamento_inteligente(df):
    REGRAS = carregar_regras_dict()
    session = SessionLocal()
    df.columns = df.columns.str.lower().str.strip()
    c=0; logs=[]
    try:
        for _, row in df.iterrows():
            idv = str(row['id_venda']).strip(); pc = int(row['parcela_cancelamento'])
            lancs = session.query(Lancamento).filter_by(id_venda=idv).all()
            if not lancs: logs.append(f"{idv}: Não encontrada"); continue
            
            reg = REGRAS.get(lancs[0].tipo_cota, {})
            lim = reg.get('limite_parcela_estorno', 3); pest = reg.get('pct_estorno', 0)
            
            z=0
            for l in lancs:
                try: pn = int(l.parcela.split('/')[0])
                except: continue
                if pn > pc:
                    l.status_recebimento='Cancelado'; l.receber_administradora=0; l.pagar_vendedor=0; l.pagar_gerente=0; l.liquido_caixa=0; z+=1
            if z: logs.append(f"{idv}: {z} futuras canceladas")
            
            if pc <= lim and pest > 0:
                cred = 0
                for l in lancs:
                    if l.receber_administradora > 0:
                        try:
                            idx = int(l.parcela.split('/')[0])-1
                            if idx < len(reg['pcts']): cred = l.receber_administradora/(reg['pcts'][idx]/100); break
                        except: pass
                if cred > 0:
                    m = -1*(cred*(pest/100))
                    session.merge(Lancamento(
                        id_lancamento=f"{idv}_EST", id_venda=idv, administradora=lancs[0].administradora, grupo=lancs[0].grupo, cota=lancs[0].cota, tipo_cota=lancs[0].tipo_cota, parcela="Estorno",
                        data_previsao=datetime.now().date(), id_cliente=lancs[0].id_cliente, cliente=lancs[0].cliente, id_vendedor=lancs[0].id_vendedor, vendedor=lancs[0].vendedor, id_gerente=lancs[0].id_gerente, gerente=lancs[0].gerente,
                        receber_administradora=m, pagar_vendedor=0, pagar_gerente=0, liquido_caixa=m, status_recebimento='Estorno', status_pgto_cliente='Estorno', status_pgto_vendedor='Isento', status_pgto_gerente='Isento'
                    ))
                    logs.append(f"{idv}: Estorno de {m:.2f} gerado")
            c+=1
        if c: session.commit()
        return c, logs
    except Exception as e: session.rollback(); return 0, [str(e)]
    finally: session.close()

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
            tv = users[l.id_vendedor].taxa_vendedor if l.id_vendedor in users else 0.20
            tg = users[l.id_gerente].taxa_gerencia if l.id_gerente in users else 0.10
            
            try: r = float(l.receber_administradora)
            except: r = 0.0
            
            l.pagar_vendedor = r * tv
            l.pagar_gerente = r * tg
            l.liquido_caixa = r - l.pagar_vendedor - l.pagar_gerente
            # Não precisa logar o recálculo para não poluir, pois já logou a mudança que causou isso

    if count_alterados > 0:
        try:
            session.commit()
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
        except Exception as e:
            session.rollback()
            return 0, pd.DataFrame([{'ID': 'Erro', 'Status': 'Crítico', 'Detalhe': str(e)}])
            
    session.close()
    return count, pd.DataFrame(logs)

def alterar_status_cliente_lote(ids, stt):
    session = SessionLocal()
    try:
        session.query(Lancamento).filter(Lancamento.id_lancamento.in_(ids)).update({Lancamento.status_pgto_cliente: stt}, synchronize_session=False)
        session.commit(); return len(ids), "OK"
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
        session.commit(); return c, "OK"
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
        return True, f"Senha de {usuario.nome_completo} alterada com sucesso!"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

