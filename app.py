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
        
        packer = newPacker()
        for part in all_parts:
            packer.add_rect(part['width'], part['height'], rid=part['film_type'])
        packer.add_bin(roll_width, roll_length)
        packer.pack()

        abin = packer[0]
        
        # --- Правильный расчет погонных метров и площади ---
        abin_used_length = 0
        abin_used_area = 0
        for rect in abin:
            abin_used_length = max(abin_used_length, rect.y + rect.height)
            abin_used_area += rect.width * rect.height
        
        total_linear_meters = abin_used_length / 100

        # Расчет общей площади створок для отображения
        total_area_parts_cm2 = sum(part['width'] * part['height'] * part['quantity'] for part in st.session_state.parts_list)
        total_area_parts_m2 = total_area_parts_cm2 / 10000
        
        # Расчет использованной площади пленки для эффективности
        total_area_used_cm2 = abin.width * abin_used_length
        total_area_used_m2 = total_area_used_cm2 / 10000

        # Расчет эффективности раскроя
        if total_area_used_m2 > 0:
            efficiency_percentage = (total_area_parts_m2 / total_area_used_m2) * 100
        else:
            efficiency_percentage = 0
        
        # Получение цены из БД для вашей утвержденной логики
        selected_film_type_name = st.session_state.parts_list[0]['film_type']
        selected_film_type = film_type_names[selected_film_type_name]
        price_per_linear_meter = selected_film_type.price_per_linear_meter_cut
        cost_of_work = 1000.0

        # Ваша утвержденная логика расчета стоимости
        total_price_film = total_linear_meters * price_per_linear_meter
        total_price = (tprice_per_linear_meter + cost_of_work) * total_linear_meters
        
        # --- Визуализация раскроя ---
        st.subheader("Визуализация раскроя")
        abin_width = abin.width
        fig, ax = plt.subplots(figsize=(10, 20 * abin_used_length / abin_width))
        ax.set_title(f"Рулон 1: {abin_width} x {abin_used_length:.2f} см")
        ax.add_patch(plt.Rectangle((0, 0), abin_width, abin_used_length, fc='#d3d3d3', ec='black'))
        
        for rect in abin:
            color = plt.cm.viridis(hash(rect.rid) % 256 / 256)
            ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, fc=color, ec='white', hatch='///'))
        
        ax.set_xlim(0, abin_width)
        ax.set_ylim(0, abin_used_length)
        ax.set_xlabel('Ширина (см)')
        ax.set_ylabel('Длина (см)')
        st.pyplot(fig)
        st.write(f"Использованная длина рулона: **{abin_used_length:.2f} см**")

        # --- Сохранение в базу данных ---
        if selected_client_name_with_address:
            selected_client_id = client_options[selected_client_name_with_address]
            existing_order = db.query(Order).filter_by(client_id=selected_client_id).first()
            if not existing_order:
                st.error("Ошибка: Не найден заказ для этого клиента.")
                st.stop()
            
            new_calculation = Calculation(
                client_id=selected_client_id,
                film_type_id=selected_film_type.id,
                total_length_meters=total_linear_meters,
                total_area_m2=total_area_parts_m2,
                price_per_linear_meter_cut=price_per_linear_meter,
                cost_of_work=cost_of_work,
                total_price_film=total_price_film,
                total_price=total_price
            )
            db.add(new_calculation)
            db.commit()
            
            existing_order.calculation_id = new_calculation.id
            existing_order.cost = total_price
            db.commit()
            st.success(f"Расчет для клиента '{selected_client_name_with_address}' сохранен, заказ обновлен!")

        # --- Отображение общих результатов ---
        st.subheader("Общие результаты")
        st.write(f"Использовано погонных метров: **{total_linear_meters:.2f} м**")
        st.write(f"Общая площадь створок: **{total_area_parts_m2:.2f} м²**")
        st.write(f"Эффективность раскроя: **{efficiency_percentage:.2f}%**")
        st.write(f"Сумма за пленку: **{total_price_film:.2f} руб.**")
        st.write(f"**Общая стоимость заказа: {total_price:.2f} руб.**")

            # --- Отображение общих результатов ---
            st.subheader("Общие результаты")
            st.write(f"Использовано погонных метров: **{total_linear_meters:.2f} м**")
            st.write(f"Общая площадь створок: **{total_area_parts_m2:.2f} м²**")
            st.write(f"Эффективность раскроя: **{efficiency_percentage:.2f}%**")
            st.write(f"Сумма за пленку: **{total_price_film:.2f} руб.**")
            st.write(f"**Общая стоимость заказа: {total_price:.2f} руб.**")

            # --- Отображение общих результатов ---
            st.subheader("Общие результаты")
            st.write(f"Использовано погонных метров: **{total_linear_meters:.2f} м**")
            st.write(f"Использовано квадратных метров: **{total_area_m2:.2f} м²**")
            st.write(f"Сумма за пленку: **{total_price_film:.2f} руб.**")
            st.write(f"**Общая стоимость заказа: {total_price:.2f} руб.**")

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