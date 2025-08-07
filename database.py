import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Теперь приложение будет всегда пытаться получить URL только из секретов Streamlit.
# Это нужно для правильной работы в Streamlit Cloud.
DATABASE_URL = st.secrets["DATABASE_URL"]

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)

# Создаем базовый класс для наших моделей
Base = declarative_base()

# Создаем сессию
Session = sessionmaker(bind=engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()