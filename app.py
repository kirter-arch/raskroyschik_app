import streamlit as st
import matplotlib.pyplot as plt
from rectpack import newPacker
import pandas as pd
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import Client, Supplier, FilmType, Source, OrderStatus, Calculation, Order
import json

# Создаем все таблицы, если их еще нет (на всякий случай)
# Base.metadata.create_all(bind=engine)

def app_main(db: Session):
    st.title('Vitrium-замеры и CRM')

    # --- Навигация по страницам (в боковой панели) ---
    st.sidebar.title("Навигация")
    page = st.sidebar.selectbox("Выберите страницу", ["Калькулятор", "Данные"])

    if page == "Калькулятор":
        calculator_page(db)
    elif page == "Данные":
        data_management_page(db)

def calculator_page(db: Session):
    st.subheader('Калькулятор')

    # Инициализируем abin как пустой список
    abin = [] 
    price_per_linear_meter = 0
    total_linear_meters = 0
    
    # Значение по умолчанию для стоимости работы
    cost_of_work = 1000.0 

    # --- Кнопка для расчета ---
    st.header('Результат раскроя:')
    if st.button('Рассчитать и сохранить'):

    # --- Выбор клиента ---
    st.subheader('Связь с клиентом')
    clients = db.query(Client).all()
    client_names = {c.name: c.id for c in clients}
    selected_client_name = st.selectbox("Выберите клиента", [""] + list(client_names.keys()))

    # --- Получение видов пленок из БД ---
    film_types = db.query(FilmType).all()
    film_type_names = {ft.name: ft for ft in film_types}
    film_type_options = list(film_type_names.keys())

    # --- Значения по умолчанию ---
    roll_width = st.number_input('Ширина рулона (см)', min_value=1, value=152)
    roll_length = st.number_input('Длина рулона (см)', min_value=1, value=3000)

    # --- Секция для ввода створок ---
    st.subheader('Створки для раскроя')
    if 'parts_list' not in st.session_state:
        st.session_state.parts_list = []

    with st.form("add_part_form", clear_on_submit=True):
        part_width = st.number_input('Ширина створки (см)', min_value=1, value=100)
        part_height = st.number_input('Высота створки (см)', min_value=1, value=100)
        part_quantity = st.number_input('Количество', min_value=1, value=1)
        selected_film_type_name = st.selectbox("Вид пленки", film_type_options)
        
        if st.form_submit_button('Добавить створку'):
            st.session_state.parts_list.append({
                'width': part_width,
                'height': part_height,
                'quantity': part_quantity,
                'film_type': selected_film_type_name
            })
            st.rerun()

    # --- Таблица створок ---
    st.subheader('Список створок')
    if st.session_state.parts_list:
        parts_df = pd.DataFrame(st.session_state.parts_list)
        st.dataframe(parts_df)
    else:
        st.info('Список створок для раскроя пуст.')

    if st.button('Очистить список'):
        st.session_state.parts_list = []
        st.rerun()


    # --- Кнопка для расчета ---
    st.header('Результат раскроя:')
    if st.button('Рассчитать и сохранить'):
        if not st.session_state.parts_list:
            st.warning('Список створок для раскроя пуст.')
        elif not selected_client_name:
            st.warning('Пожалуйста, выберите клиента для сохранения расчета.')
        else:
            # ... (код для расчета раскроя без изменений) ...

            total_linear_meters = 0
            total_price_film = 0 # Переименовано

            for rect in abin:
                # ... (код без изменений) ...
                
                price_per_linear_meter = selected_film_type.price_per_linear_meter_cut
                
                total_linear_meters += rect.height / 100
                total_price_film += (rect.height / 100) * price_per_linear_meter # Используем новое имя

            # ... (код без изменений) ...

            # Новая логика для расчета общей стоимости заказа
            
            total_price = (price_per_linear_meter + cost_of_work) * total_linear_meters
            
            # --- Сохранение в базу данных ---
            if selected_client_name:
                selected_client_id = client_names[selected_client_name]

                new_calculation = Calculation(
                    client_id=selected_client_id,
                    film_type_id=film_type_id,
                    total_length_meters=total_linear_meters,
                    total_area_m2=total_area_m2,
                    price_per_linear_meter_cut=price_per_linear_meter,
                    cost_of_work=cost_of_work,
                    total_price_film=total_price_film, # Обновлено
                    total_price=total_price # Добавлено
                )
                db.add(new_calculation)
                db.commit()
                st.success(f"Расчет для клиента '{selected_client_name}' сохранен в базе данных!")

            # --- Отображение результатов ---
            st.subheader("Общие результаты")
            st.write(f"Использовано погонных метров: **{total_linear_meters:.2f} м**")
            st.write(f"Использовано квадратных метров: **{total_area_m2:.2f} м²**")
            st.write(f"Сумма за пленку: **{total_price_film:.2f} руб.**") # Обновлено
            st.write(f"**Общая стоимость заказа: {total_price:.2f} руб.**") # Добавлена новая строка

def data_management_page(db: Session):
    st.subheader('Управление замерами')

    # Отображение данных клиентов
    st.subheader("Клиенты")
    clients = db.query(Client).all()
    if clients:
        clients_df = pd.DataFrame([{
            'Имя': c.name,
            'Телефон': c.phone_number,
            'Город': c.city,
            'Адрес': c.address,
            'Комментарии': c.comments,
            'Источник': c.source.name if c.source else 'Не указан'
        } for c in clients])
        st.dataframe(clients_df)
    else:
        st.info("Клиентов пока нет.")

    # Форма для добавления нового клиента
    with st.form("new_client_form", clear_on_submit=True):
        st.write("Добавить нового клиента")
        
        # Получаем все источники из базы данных
        sources = db.query(Source).all()
        source_names = [s.name for s in sources]
        
        client_name = st.text_input("Имя")
        client_phone = st.text_input("Телефон")
        client_city = st.text_input("Город")
        client_address = st.text_input("Адрес")
        client_comments = st.text_area("Комментарии")
        
        # Selectbox для выбора источника
        selected_source_name = st.selectbox("Источник", source_names)
        
        submitted = st.form_submit_button("Добавить")
        
        if submitted:
            # Находим ID выбранного источника
            selected_source = db.query(Source).filter_by(name=selected_source_name).first()
            
            new_client = Client(
                name=client_name,
                phone_number=client_phone,
                city=client_city,
                address=client_address,
                comments=client_comments,
                source_id=selected_source.id if selected_source else None
            )
            db.add(new_client)
            db.commit()
            st.success("Клиент добавлен!")
            st.rerun()

# --- Главная точка входа в приложение ---
if __name__ == '__main__':
    # Используем with для правильной работы с сессией
    for db_session in get_db():
        app_main(db_session)