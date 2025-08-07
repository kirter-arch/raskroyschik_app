from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

# Клиенты
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String)  # Поле для номера
    city = Column(String)          # поле для города
    address = Column(String)       # Поле для адреса
    comments = Column(String)      # Поле для комментариев
    
    source_id = Column(Integer, ForeignKey("sources.id"))
    source = relationship("Source", back_populates="clients")

# Поставщики
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    contact_info = Column(String)

# Виды пленок
class FilmType(Base):
    __tablename__ = "film_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    width = Column(Integer, nullable=False)
    length = Column(Integer, nullable=False)

    price_per_linear_meter_cut = Column(Float, nullable=False) # Цена за погонный метр в отрез
    price_per_roll = Column(Float, nullable=False) # Цена за рулон

    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="films")

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
    clients = relationship("Client", order_by=Client.id, back_populates="source")

# Справочник для статусов заказа
class OrderStatus(Base):
    __tablename__ = "order_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

# Таблица для хранения результатов каждого расчета
class Calculation(Base):
    __tablename__ = "calculations"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client")
    
    film_type_id = Column(Integer, ForeignKey("film_types.id"))
    film_type = relationship("FilmType")
    
    total_length_meters = Column(Float)
    total_area_m2 = Column(Float)
    number_of_rolls = Column(Integer)
    
    price_per_linear_meter = Column(Float)
    cost_of_film = Column(Float)
    cost_of_work = Column(Float)
    total_price = Column(Float)

# Таблица для заказов
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_completed = Column(DateTime)
    cost = Column(Float) # Итоговая стоимость заказа

    client_id = Column(Integer, ForeignKey("clients.id"))
    calculation_id = Column(Integer, ForeignKey("calculations.id"))
    status_id = Column(Integer, ForeignKey("order_statuses.id"))

    client = relationship("Client")
    calculation = relationship("Calculation")
    status = relationship("OrderStatus")

Supplier.films = relationship("FilmType", order_by=FilmType.id, back_populates="supplier")