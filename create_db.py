from database import engine, Base
from models import Order, Calculation # Импортируем только нужные модели

print("Removing old 'orders' table...")
Order.__table__.drop(bind=engine, checkfirst=True)

print("Removing old 'calculations' table...")
Calculation.__table__.drop(bind=engine, checkfirst=True)

print("Creating all tables based on models...")
Base.metadata.create_all(bind=engine)

print("Database tables synchronized successfully!")