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
    page = st.sidebar.selectbox("Выберите страницу", ["Записать клиента", "Калькулятор"])

    if page == "Калькулятор":
        calculator_page(db)
    elif page == "Записать клиента":
        data_management_page(db)

# app.py

def calculator_page(db: Session):
    st.subheader('Калькулятор')

    # --- Выбор клиента ---
    st.subheader('Связь с клиентом')
    clients = db.query(Client).all()
        # Создаем словарь, где ключ - это "Имя (Адрес)", а значение - ID клиента
    client_options = {f"{c.name} ({c.address})": c.id for c in clients}
        # Используем этот новый словарь для отображения в selectbox
    selected_client_name_with_address = st.selectbox("Выберите клиента", [""] + list(client_options.keys()))

    selected_client_id = None
    if selected_client_name_with_address:
        # Получаем ID клиента из выбранной опции
        selected_client_id = client_options[selected_client_name_with_address]

    # Эта секция с выбором статуса будет отображаться только после выбора клиента
    if selected_client_id:
        existing_order = db.query(Order).filter_by(client_id=selected_client_id).first()

        if existing_order:
            st.subheader("Управление заказом")
            statuses = db.query(OrderStatus).all()
            status_names = [s.name for s in statuses]
            
            # Находим текущий статус заказа
            current_status_name = existing_order.status.name if existing_order.status else status_names[0]
            
            selected_status_name = st.selectbox(
                "Изменить статус:",
                status_names,
                index=status_names.index(current_status_name)
            )

            if st.button("Обновить статус заказа"):
                new_status = db.query(OrderStatus).filter_by(name=selected_status_name).first()
                existing_order.status_id = new_status.id
                db.commit()
                st.success(f"Статус заказа обновлен на '{selected_status_name}'!")
                st.rerun()

    # --- Получение видов пленок из БД ---
    film_types = db.query(FilmType).all()
    film_type_names = {ft.name: ft for ft in film_types}
    film_type_options = list(film_type_names.keys())
    
    # Инициализируем abin как пустой список и другие переменные
    abin = [] 
    price_per_linear_meter = 0
    total_linear_meters = 0
    cost_of_work = 1000.0 
    total_area_m2 = 0 
    # Инициализируем новые переменные
    abin_width = 0
    abin_used_length_cm = 0

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
        parts_df.index = parts_df.index + 1
        parts_df.index.name = '№'
        
        # Используем st.data_editor для редактирования DataFrame
        edited_df = st.data_editor(
            parts_df,
            column_config={
                "width": st.column_config.NumberColumn("Ширина (см)", format="%.0f"),
                "height": st.column_config.NumberColumn("Высота (см)", format="%.0f"),
                "quantity": st.column_config.NumberColumn("Количество", format="%.0f", min_value=1),
                "film_type": st.column_config.TextColumn("Вид пленки"),
            },
            hide_index=False,
            num_rows="dynamic", # Позволяет добавлять/удалять строки
        )
        
        # Обновляем список створок после редактирования
        st.session_state.parts_list = edited_df.to_dict('records')

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
        elif not selected_client_name_with_address:
            st.warning('Пожалуйста, выберите клиента для сохранения расчета.')
        else:
            all_parts = []
            for part in st.session_state.parts_list:
                for _ in range(part['quantity']):
                    all_parts.append({
                        'width': part['width'],
                        'height': part['height'],
                        'film_type': part['film_type']
                    })

            # --- НОВЫЙ АЛГОРИТМ РАСКРОЯ: Ручное заполнение строк ---
            # Сортируем детали по ширине в убывающем порядке для оптимальной укладки
            sorted_parts = sorted(all_parts, key=lambda p: p['width'], reverse=True)

            current_row_width = 0
            current_row_height = 0
            abin_used_length_cm = 0
            
            for part in sorted_parts:
                part_width = part['width']
                part_height = part['height']
                
                if current_row_width + part_width <= roll_width:
                    # Деталь помещается в текущую строку
                    current_row_width += part_width
                    current_row_height = max(current_row_height, part_height)
                else:
                    # Строка заполнена, добавляем её высоту к общей длине
                    abin_used_length_cm += current_row_height
                    # Начинаем новую строку с текущей детали
                    current_row_width = part_width
                    current_row_height = part_height
            
            # Добавляем высоту последней строки
            if current_row_height > 0:
                abin_used_length_cm += current_row_height

            total_linear_meters = abin_used_length_cm / 100

            # Расчет общей площади створок
            total_area_parts_cm2 = sum(part['width'] * part['height'] * part['quantity'] for part in st.session_state.parts_list)
            total_area_parts_m2 = total_area_parts_cm2 / 10000
            
            # Расчет использованной площади пленки для эффективности
            abin_width = roll_width
            total_area_used_cm2 = abin_width * abin_used_length_cm
            total_area_used_m2 = total_area_used_cm2 / 10000

            if total_area_used_m2 > 0:
                efficiency_percentage = (total_area_parts_m2 / total_area_used_m2) * 100
            else:
                efficiency_percentage = 0
            
            selected_film_type_name = st.session_state.parts_list[0]['film_type']
            selected_film_type = film_type_names[selected_film_type_name]
            price_per_linear_meter = selected_film_type.price_per_linear_meter_cut
            cost_of_work = 1000.0

            total_price_film = total_linear_meters * price_per_linear_meter
            total_price = (price_per_linear_meter + cost_of_work) * total_linear_meters


            # --- Отображение общих результатов ---
            st.subheader("Общие результаты")
            st.write(f"Использовано погонных метров: **{total_linear_meters:.2f} м**")
            st.write(f"Общая площадь створок: **{total_area_parts_m2:.2f} м²**")
            st.write(f"Эффективность раскроя: **{efficiency_percentage:.2f}%**")
            st.write(f"Сумма за пленку: **{total_price_film:.2f} руб.**")
            st.write(f"**Общая стоимость заказа: {total_price:.2f} руб.**")

                       # --- Визуализация раскроя ---
            # Для этого простого алгоритма невозможно построить сложную визуализацию
            st.subheader("Визуализация раскроя")
            st.warning("Визуализация недоступна для этого метода расчета. Этот алгоритм гарантирует правильный расчет погонных метров, но не создает схему раскроя.")           # --- Визуализация раскроя ---
            # Для этого простого алгоритма невозможно построить сложную визуализацию
            st.subheader("Визуализация раскроя")
            st.warning("Визуализация недоступна для этого метода расчета. Этот алгоритм гарантирует правильный расчет погонных метров, но не создает схему раскроя.")

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

        # Получаем все статусы из базы данных
        statuses = db.query(OrderStatus).all()
        status_names = [s.name for s in statuses]
        
        client_name = st.text_input("Имя")
        client_phone = st.text_input("Телефон")
        client_city = st.text_input("Город")
        client_address = st.text_input("Адрес")
        client_comments = st.text_area("Комментарии")
        
        # Selectbox для выбора источника и статуса
        selected_source_name = st.selectbox("Источник", source_names)
        selected_status_name = st.selectbox("Статус заказа", status_names)

        submitted = st.form_submit_button("Добавить")
        
        if submitted:
            # Находим ID выбранного источника
            selected_source = db.query(Source).filter_by(name=selected_source_name).first()
            selected_status = db.query(OrderStatus).filter_by(name=selected_status_name).first()
             # 1. Создаем нового клиента
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
            # 2. Создаем новый заказ с выбранным статусом и связываем его с клиентом
            new_order = Order(
                name=f"Заказ клиента {client_name}",
                address=client_address,
                client_id=new_client.id,
                status_id=selected_status.id if selected_status else None
            )
            db.add(new_order)
            db.commit()

            st.success("Клиент добавлен!")
            st.rerun()

# --- Главная точка входа в приложение ---
if __name__ == '__main__':
    # Используем with для правильной работы с сессией
    for db_session in get_db():
        app_main(db_session)