from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# Клиенты
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String)
    city = Column(String)
    address = Column(String)
    comments = Column(String)
    
    source_id = Column(Integer, ForeignKey("sources.id"))
    source = relationship("Source", back_populates="clients")
    
    calculations = relationship("Calculation", order_by="Calculation.id", back_populates="client")
    orders = relationship("Order", order_by="Order.id", back_populates="client")

# Поставщики
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    contact_info = Column(String)
    
    films = relationship("FilmType", order_by="FilmType.id", back_populates="supplier")

# Виды пленок
class FilmType(Base):
    __tablename__ = "film_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    width = Column(Integer, nullable=False)
    length = Column(Integer, nullable=False)

    price_per_linear_meter_cut = Column(Float, nullable=False)
    price_per_roll = Column(Float, nullable=False)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="films")
    
    calculations = relationship("Calculation", order_by="Calculation.id", back_populates="film_type")

    @property
    def price_per_linear_meter_in_roll(self):
        if self.length > 0:
            return self.price_per_roll / (self.length / 100.0)
        return 0.0

# Источники клиентов
class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    clients = relationship("Client", order_by="Client.id", back_populates="source")

# Справочник для статусов заказа
class OrderStatus(Base):
    __tablename__ = "order_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    orders = relationship("Order", order_by="Order.id", back_populates="status")

# Таблица для хранения результатов каждого расчета
class Calculation(Base):
    __tablename__ = "calculations"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", back_populates="calculations")

    film_type_id = Column(Integer, ForeignKey("film_types.id"))
    film_type = relationship("FilmType", back_populates="calculations")
    
    total_length_meters = Column(Float)
    total_area_m2 = Column(Float)
    
    price_per_linear_meter_cut = Column(Float) 
    
    cost_of_work = Column(Float, default=1000.0)#здесь меняем цену за работу
    total_price = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", order_by="Order.id", back_populates="calculation")

# Таблица для заказов
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    
    date_created = Column(DateTime, default=datetime.utcnow)
    date_completed = Column(DateTime)
    cost = Column(Float)

    client_id = Column(Integer, ForeignKey("clients.id"))
    calculation_id = Column(Integer, ForeignKey("calculations.id"))
    status_id = Column(Integer, ForeignKey("order_statuses.id"))

    client = relationship("Client", back_populates="orders")
    calculation = relationship("Calculation", back_populates="orders")
    status = relationship("OrderStatus", back_populates="orders")