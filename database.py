import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Приложение будет пытаться получить URL только из секретов Streamlit
# Если secrets.toml нет, то возникнет ошибка, и это правильно, 
# потому что приложение не должно работать без подключения к Supabase
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