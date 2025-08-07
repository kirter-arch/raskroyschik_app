import streamlit as st
import matplotlib.pyplot as plt
from rectpack import newPacker
import pandas as pd
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import Client, Supplier, FilmType, Source, OrderStatus, Calculation, Order

# Создаем все таблицы, если их еще нет (на всякий случай)
#Base.metadata.create_all(bind=engine)

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

    # --- Старая логика калькулятора (пока без использования БД) ---
    roll_width = st.number_input('Ширина рулона (см)', min_value=1, value=126)
    roll_length = st.number_input('Длина рулона (см)', min_value=1, value=5000)

    # --- Секция для ввода створок ---
    st.subheader('Створки для раскроя')
    if 'parts_list' not in st.session_state:
        st.session_state.parts_list = []

    part_width = st.number_input('Ширина створки (см)', min_value=1, value=100)
    part_height = st.number_input('Высота створки (см)', min_value=1, value=100)
    part_quantity = st.number_input('Количество', min_value=1, value=1)

    if st.button('Добавить створку'):
        st.session_state.parts_list.append((part_width, part_height, part_quantity))

    # --- Таблица створок ---
    st.subheader('Список створок')
    if st.session_state.parts_list:
        parts_df = pd.DataFrame(st.session_state.parts_list, columns=['Ширина (см)', 'Высота (см)', 'Количество (шт)'])
        st.dataframe(parts_df)
    else:
        st.info('Список створок для раскроя пуст.')

    if st.button('Очистить список'):
        st.session_state.parts_list = []
        st.experimental_rerun()

    # --- Кнопка для расчета ---
    st.header('Результат раскроя:')
    if st.button('Рассчитать'):
        if not st.session_state.parts_list:
            st.warning('Список створок для раскроя пуст.')
        else:
            all_parts = []
            for part in st.session_state.parts_list:
                width, height, quantity = part
                for _ in range(quantity):
                    all_parts.append((width, height))

            packer = newPacker()
            for part in all_parts:
                packer.add_rect(part[0], part[1])
            packer.add_bin(roll_width, roll_length)
            packer.pack()

            abin = packer[0]
            abin_used_length = 0
            abin_used_area = 0
            
            part_counts = {}
            for rect in abin:
                abin_used_length = max(abin_used_length, rect.y + rect.height)
                abin_used_area += rect.width * rect.height
                
                part_key = (int(rect.width), int(rect.height))
                if part_key in part_counts:
                    part_counts[part_key]['Количество (шт)'] += 1
                else:
                    part_counts[part_key] = {
                        'Длина (см)': int(rect.height),
                        'Ширина (см)': int(rect.width),
                        'Количество (шт)': 1,
                        'Погонные метры (м)': rect.height / 100,
                        'Площадь (м²)': (rect.width * rect.height) / 10000
                    }

            if abin.width > 0 and abin_used_length > 0:
                aspect_ratio = abin_used_length / abin.width
            else:
                aspect_ratio = 1
                
            fig_width = 8
            fig_height = fig_width * aspect_ratio
            
            if fig_height > 15:
                fig_height = 15
            
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            ax.set_aspect('equal', adjustable='box')
            
            margin = abin.width * 0.02
            ax.set_xlim(-margin, abin.width + margin)
            ax.set_ylim(-margin, abin_used_length + margin)
            
            ax.set_title("Схема раскроя")
            ax.set_xlabel("Ширина (см)")
            ax.set_ylabel("Длина (см)")
            
            for rect in abin:
                ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, edgecolor='black', facecolor='skyblue'))
                center_x = rect.x + rect.width / 2
                center_y = rect.y + rect.height / 2
                ax.text(center_x, center_y, f'{int(rect.width)}x{int(rect.height)}', ha='center', va='center', fontsize=8)
                
            st.pyplot(fig)
            plt.close(fig)

            st.subheader("Общие результаты")
            abin_used_area_m2 = abin_used_area / 10000
            roll_area_m2 = (roll_width * roll_length) / 10000
            abin_efficiency = (abin_used_area_m2 / roll_area_m2) * 100
            
            remaining_length = roll_length - abin_used_length
            
            st.write(f"Использовано погонных метров: **{abin_used_length / 100:.2f} м**")
            st.write(f"Остаток погонных метров: **{remaining_length / 100:.2f} м**")
            st.write(f"Использовано квадратных метров: **{abin_used_area_m2:.2f} м²**")
            st.write(f"Эффективность раскроя: **{abin_efficiency:.2f}%**")
            
            last_calculation_results = []
            for part in part_counts.values():
                part_row = part.copy()
                part_row['Погонные метры (м)'] *= part_row['Количество (шт)']
                part_row['Площадь (м²)'] *= part_row['Количество (шт)']
                last_calculation_results.append(part_row)
            
            results_df = pd.DataFrame(last_calculation_results)
            
            csv_string = results_df.to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(
                label="Скачать CSV файл",
                data=csv_string,
                file_name="результаты_раскроя.csv",
                mime="text/csv"
            )

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
    db = get_db()
    try:
        app_main(db)
    finally:
        db.close()