import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    # Пытаемся получить URL из секретов Streamlit Cloud
    DATABASE_URL = st.secrets["DATABASE_URL"]
except FileNotFoundError:
    # Если запущен локально, используем локальный URL
    DATABASE_URL = "postgresql://postgres:x500oo@localhost:5432/vitrium_db"

engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()