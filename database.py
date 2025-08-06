from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- ИЗМЕНИ ЭТИ ПАРАМЕТРЫ НА СВОИ ---
DATABASE_URL = "postgresql://postgres:x500oo@localhost:5432/vitrium_db"

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    return db