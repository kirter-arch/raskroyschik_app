"""
Модуль Streamlit-приложения Vitrium: замеры, CRM и раскрой пленки.

Содержит:
- app_main: точка входа UI, навигация между страницами
- calculator_page: калькулятор раскроя рулона и сохранение расчета
- data_management_page: управление клиентами и заказами
"""

import streamlit as st
import matplotlib.pyplot as plt
from rectpack import newPacker
import pandas as pd
from sqlalchemy.orm import Session
from database import get_db
from models import Client, FilmType, Source, OrderStatus, Calculation, Order
import re
import io

# === Функция: Главная точка входа приложения ===
def app_main(db: Session) -> None:
    """
    Отрисовывает общий каркас приложения и навигацию.
    Переключает страницы: 'Калькулятор' и 'Записать клиента'.
    """
    st.title('Vitrium-замеры и CRM')

    # --- Блок: Навигация по страницам ---
    st.sidebar.title("Навигация")
    page = st.sidebar.selectbox("Выберите страницу", ["Записать клиента", "Калькулятор"])

    if page == "Калькулятор":
        calculator_page(db)
    elif page == "Записать клиента":
        data_management_page(db)


# === Функция: Калькулятор раскроя и сохранения расчета ===
def calculator_page(db: Session) -> None:
    """
    Калькулятор раскроя пленки:
    - выбор клиента и управление статусом заказа
    - ввод параметров рулона
    - ввод/редактирование створок
    - упаковка через rectpack, расчет метража, площадей, стоимости
    - визуализация и сохранение результата в БД
    """
    st.subheader('Калькулятор')

    # --- Блок: Связь с клиентом и управление заказом ---
    st.subheader('Связь с клиентом')
    clients = db.query(Client).all()
    client_options = {f"{c.name} ({c.address})": c.id for c in clients}
    selected_client_name_with_address = st.selectbox("Выберите клиента", [""] + list(client_options.keys()))
    selected_client_id = client_options.get(selected_client_name_with_address) if selected_client_name_with_address else None

    if selected_client_id:
        existing_order = db.query(Order).filter_by(client_id=selected_client_id).first()
        if existing_order:
            st.subheader("Управление заказом")
            statuses = db.query(OrderStatus).all()
            status_names = [s.name for s in statuses]
            current_status_name = existing_order.status.name if existing_order.status else (status_names[0] if status_names else "")

            selected_status_name = st.selectbox(
                "Изменить статус:",
                status_names,
                index=status_names.index(current_status_name) if current_status_name in status_names else 0
            )

            if st.button("Обновить статус заказа"):
                new_status = db.query(OrderStatus).filter_by(name=selected_status_name).first()
                if new_status:
                    existing_order.status_id = new_status.id
                    db.commit()
                    st.success(f"Статус заказа обновлен на '{selected_status_name}'!")
                    st.rerun()

    # --- Блок: Виды пленок ---
    film_types = db.query(FilmType).order_by(FilmType.id).all()
    film_type_by_name = {ft.name: ft for ft in film_types}
    film_type_options = list(film_type_by_name.keys())

    # --- Блок: Параметры рулона ---
    roll_width = st.number_input('Ширина рулона (см)', min_value=1, value=152, step=1)
    roll_length = st.number_input('Длина рулона (см)', min_value=1, value=3000, step=10)

    # --- Блок: Ввод створок для раскроя ---
    st.subheader('Створки для раскроя')
    if 'parts_list' not in st.session_state:
        st.session_state.parts_list = []

    with st.form("add_part_form", clear_on_submit=True):
        part_width = st.text_input('Ширина створки (см)',  value="")
        part_height = st.text_input('Высота створки (см)',  value="")
        part_quantity = st.number_input('Количество', min_value=1, value=1, step=1)
        selected_film_type_name = st.selectbox("Вид пленки", film_type_options)

        if st.form_submit_button('Добавить створку'):
            st.session_state.parts_list.append({
                'width': int(part_width) if part_width else 0,
                'height': int(part_height) if part_height else 0,
                'quantity': int(part_quantity),
                'film_type': selected_film_type_name
            })
            st.rerun()

    # --- Блок: Таблица/редактор створок ---
    st.subheader('Список створок')
    if st.session_state.parts_list:
        parts_df = pd.DataFrame(st.session_state.parts_list)
        parts_df.index = parts_df.index + 1
        parts_df.index.name = '№'

        edited_df = st.data_editor(
            parts_df,
            column_config={
                "width": st.column_config.NumberColumn("Ширина (см)", format="%.0f", step=1),
                "height": st.column_config.NumberColumn("Высота (см)", format="%.0f", step=1),
                "quantity": st.column_config.NumberColumn("Количество", format="%.0f", min_value=1, step=1),
                "film_type": st.column_config.TextColumn("Вид пленки"),
            },
            hide_index=False,
            num_rows="dynamic",
        )
        st.session_state.parts_list = edited_df.to_dict('records')
    else:
        st.info('Список створок для раскроя пуст.')

    if st.button('Очистить список'):
        st.session_state.parts_list = []
        st.rerun()

    # --- Блок: Расчет и сохранение ---
    st.header('Результат раскроя:')
    if st.button('Рассчитать и сохранить'):
        # Подблок: Базовые проверки
        if not st.session_state.parts_list:
            st.warning('Список створок для раскроя пуст.')
            return
        if not selected_client_name_with_address:
            st.warning('Пожалуйста, выберите клиента для сохранения расчета.')
            return

        # Подблок: Единый вид пленки для корректного ценообразования
        film_types_in_list = {p['film_type'] for p in st.session_state.parts_list}
        if len(film_types_in_list) != 1:
            st.error("Для корректного расчета цены используйте один вид пленки во всех створках.")
            return
        single_film_type_name = next(iter(film_types_in_list))
        selected_film_type = film_type_by_name[single_film_type_name]
        price_per_linear_meter = float(selected_film_type.price_per_linear_meter_cut)
        cost_of_work = 1200.0  # фиксированная стоимость работ

        # Подблок: Разворачиваем позиции по количеству и валидируем размеры
        parts_for_packing = []
        for part in st.session_state.parts_list:
            w = int(part.get('width', 0))
            h = int(part.get('height', 0))
            q = int(part.get('quantity', 0))
            for _ in range(q):
                parts_for_packing.append({'width': w, 'height': h, 'rid': single_film_type_name})

        if any(p['width'] <= 0 or p['height'] <= 0 for p in parts_for_packing):
            st.error("Все размеры створок должны быть положительными.")
            return

        # Подблок: Валидация габаритов с учетом запрета поворота (rotation=False)
        too_wide = [p for p in parts_for_packing if p['width'] > roll_width]
        too_tall = [p for p in parts_for_packing if p['height'] > roll_length]
        if too_wide:
            st.error("Есть створки шире рулона. Уменьшите ширину створок.")
            return
        if too_tall:
            st.error("Есть створки выше длины рулона. Увеличьте длину рулона или уменьшите высоту створок.")
            return

        # Подблок: Упаковка через rectpack (сортировка по площади, без поворотов)
        parts_for_packing.sort(key=lambda p: p['width'] * p['height'], reverse=True)
        packer = newPacker(rotation=False)

        for p in parts_for_packing:
            packer.add_rect(p['width'], p['height'], rid=p['rid'])

        # Добавляем до 10 рулонов (бинов), чтобы вместить все детали
        max_rolls = 100
        for _ in range(max_rolls):
            packer.add_bin(roll_width, roll_length)

        packer.pack()

        if len(packer) == 0:
            st.error("Не удалось создать бин для раскроя.")
            return

        # Подблок: Проверка упакованных элементов
        placed_count = len(packer.rect_list())
        total_requested = len(parts_for_packing)
        if placed_count < total_requested:
            st.error(f"Не удалось разместить все детали даже в {max_rolls} рулонах. Проверьте размеры створок и рулона.")
            return

      # Подблок: Общая использованная длина по всем рулонам
        total_used_length_cm = 0
        for abin in packer:
            if abin:  # пропускаем пустые бины
                roll_used = max((rect.y + rect.height for rect in abin), default=0)
                total_used_length_cm += roll_used

        used_length_cm = total_used_length_cm  # для совместимости с оставшимся кодом
        total_linear_meters = total_used_length_cm / 100.0

        # Подблок: Расчет площадей и эффективности
        total_area_requested_cm2 = sum(p['width'] * p['height'] for p in parts_for_packing)
        total_area_requested_m2 = total_area_requested_cm2 / 10000.0

        placed_area_cm2 = sum(rect.width * rect.height for rect in abin)
        placed_area_m2 = placed_area_cm2 / 10000.0

        total_area_used_m2 = (roll_width * used_length_cm) / 10000.0
        efficiency_percentage = (placed_area_m2 / total_area_used_m2 * 100.0) if total_area_used_m2 > 0 else 0.0

        # Подблок: Расчет стоимости
        total_price_film = total_linear_meters * price_per_linear_meter
        total_price = (price_per_linear_meter + cost_of_work) * total_area_requested_m2

       # Подблок: Визуализация раскроя — для всех рулонов
        st.subheader("Визуализация раскроя")

        for roll_index, abin in enumerate(packer):
            if not abin:  # пропускаем пустые рулоны
                continue

            used_length_this_roll = max((rect.y + rect.height for rect in abin), default=0)
            fig_height = max(6.0, 0.02 * used_length_this_roll)
            fig, ax = plt.subplots(figsize=(8, fig_height))
            ax.set_title(f"Рулон {roll_index + 1}: {roll_width} x {used_length_this_roll:.2f} см")
            ax.add_patch(plt.Rectangle((0, 0), roll_width, used_length_this_roll, fc='#d3d3d3', ec='black'))

            for rect in abin:
                color = plt.cm.tab10(hash(str(rect.rid)) % 10)
                ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, fc=color, ec='white', hatch='///'))

            ax.set_xlim(0, roll_width)
            ax.set_ylim(0, used_length_this_roll)
            ax.set_xlabel('Ширина (см)')
            ax.set_ylabel('Длина (см)')
            
            # Выводим график
            st.pyplot(fig)
            plt.close(fig)  # освобождаем память

        st.pyplot(fig)

        # Подблок: Отображение итогов
        st.subheader("Общие результаты")
        st.write(f"Использованная длина рулона: {used_length_cm:.2f} см")
        st.write(f"Использовано погонных метров: {total_linear_meters:.2f} м")
        st.write(f"Площадь упакованных створок: {placed_area_m2:.2f} м²")
        st.write(f"Эффективность раскроя: {efficiency_percentage:.2f}%")
        st.write(f"Сумма за пленку: {total_price_film:.2f} руб.")
        st.write(f"Общая стоимость заказа: {total_price:.2f} руб.")

        # Подблок: Сохранение в БД
        selected_client_id = client_options[selected_client_name_with_address]
        existing_order = db.query(Order).filter_by(client_id=selected_client_id).first()
        if not existing_order:
            st.error("Ошибка: Не найден заказ для этого клиента.")
            return

        new_calculation = Calculation(
            client_id=selected_client_id,
            film_type_id=selected_film_type.id,
            total_length_meters=total_linear_meters,
            total_area_m2=placed_area_m2,
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


# === Функция: Управление клиентами и заказами ===
def data_management_page(db: Session) -> None:
    """
    Управление данными CRM:
    - просмотр списка клиентов
    - добавление нового клиента
    - создание заказа с выбранным статусом
    """
    st.subheader('Управление замерами')

    # --- Блок: Список клиентов ---
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

    # --- Блок: Форма добавления нового клиента ---
    with st.form("new_client_form", clear_on_submit=True):
        st.write("Добавить нового клиента")

        sources = db.query(Source).all()
        source_names = [s.name for s in sources]

        statuses = db.query(OrderStatus).all()
        status_names = [s.name for s in statuses]

        client_name = st.text_input("Имя")
        client_phone = st.text_input("Телефон")
        client_city = st.text_input("Город")
        client_address = st.text_input("Адрес")
        client_comments = st.text_area("Комментарии")

        selected_source_name = st.selectbox("Источник", source_names)
        selected_status_name = st.selectbox("Статус заказа", status_names)

        submitted = st.form_submit_button("Добавить")

        if submitted:
            # Очистка номера телефона от всех символов, кроме цифр
            client_phone_clean = re.sub(r'\D', '', client_phone)

            selected_source = db.query(Source).filter_by(name=selected_source_name).first()
            selected_status = db.query(OrderStatus).filter_by(name=selected_status_name).first()

            # Создание клиента
            new_client = Client(
                name=client_name,
                phone_number=client_phone_clean,
                city=client_city,
                address=client_address,
                comments=client_comments,
                source_id=selected_source.id if selected_source else None
            )
            db.add(new_client)
            db.commit()

            # Создание заказа с выбранным статусом
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


# === Точка входа ===
if __name__ == '__main__':
    # Поддержка жизненного цикла сессии SQLAlchemy через генератор get_db()
    for db_session in get_db():
        app_main(db_session)