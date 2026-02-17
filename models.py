# models.py
from sqlalchemy import Column, String, Integer, Float, Date, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id_usuario = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True)
    password_hash = Column(String(200))
    nome_completo = Column(String(150))
    tipo_acesso = Column(String(50))
    taxa_vendedor = Column(Float)
    taxa_gerencia = Column(Float)

class Cliente(Base):
    __tablename__ = 'clientes'
    id_cliente = Column(String(50), primary_key=True)
    nome_completo = Column(String(150))
    email = Column(String(150))
    telefone = Column(String(50))
    obs = Column(Text)

class RegraComissao(Base):
    __tablename__ = 'regras_comissao'
    # Identificação
    tipo_cota = Column(String(100), primary_key=True)
    administradora = Column(String(50))
    id_tabela = Column(String(50))
    
    # Comissões
    lista_percentuais = Column(String(200))
    
    # Regras de Negócio (Todos os campos recuperados)
    min_credito = Column(Float, default=0.0)
    max_credito = Column(Float, default=0.0)
    min_prazo = Column(Integer, default=0)
    max_prazo = Column(Integer, default=0)
    
    taxa_antecipada = Column(Float, default=0.0)
    ref_taxa_antecipada = Column(String(50))
    
    min_taxa_adm = Column(Float, default=0.0)
    max_taxa_adm = Column(Float, default=0.0)
    fundo_reserva = Column(Float, default=0.0)
    
    pct_lance_embutido = Column(Float, default=0.0)
    indice_reajuste = Column(String(50))
    modalidades_contemplacao = Column(String(300))
    
    # Churn / Estorno
    pct_estorno = Column(Float, default=0.0)
    limite_parcela_estorno = Column(Integer, default=3)

class Lancamento(Base):
    __tablename__ = 'financeiro_mestre'
    
    id_lancamento = Column(String(100), primary_key=True)
    id_venda = Column(String(100), index=True)
    
    administradora = Column(String(50))
    grupo = Column(String(50))
    cota = Column(String(50))
    tipo_cota = Column(String(100))
    parcela = Column(String(50))
    
    data_previsao = Column(Date)
    data_real_recebimento = Column(Date, nullable=True)
    valor_recebido_real = Column(Float, nullable=True)
    
    id_cliente = Column(String(50))
    cliente = Column(String(150))
    id_vendedor = Column(String(50))
    vendedor = Column(String(150))
    id_gerente = Column(String(50))
    gerente = Column(String(150))
    
    receber_administradora = Column(Float, default=0.0)
    pagar_vendedor = Column(Float, default=0.0)
    pagar_gerente = Column(Float, default=0.0)
    liquido_caixa = Column(Float, default=0.0)
    
    status_recebimento = Column(String(50), default='Pendente')
    status_pgto_cliente = Column(String(50), default='Pendente')
    status_pgto_vendedor = Column(String(50), default='Pendente')
    status_pgto_gerente = Column(String(50), default='Pendente')
    
    obs = Column(Text)