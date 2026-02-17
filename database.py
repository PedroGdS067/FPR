# database.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

# Pega a URL do segredo ou variável de ambiente
# No secrets.toml será: DATABASE_URL = "mysql+mysqlconnector://usuario:senha@host:porta/nome_banco"
DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))

if not DATABASE_URL:
    # Fallback para SQLite local apenas para testes se não houver config
    DATABASE_URL = "sqlite:///./sistema_local.db"

# O SQLAlchemy precisa saber que é mysqlconnector
# Se a URL vier apenas como "mysql://", forçamos o driver correto
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+mysqlconnector://")

# Configuração específica para MySQL (pool_recycle evita queda de conexão por inatividade)
engine = create_engine(DATABASE_URL, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)