import streamlit as st
from rectpack import newPacker
import matplotlib.pyplot as plt
import pandas as pd

# --- Глобальные переменные для хранения состояния приложения ---
if 'parts_list' not in st.session_state:
    st.session_state['parts_list'] = []
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
if 'edit_index' not in st.session_state:
    st.session_state['edit_index'] = None
if 'part_width_edit' not in st.session_state:
    st.session_state['part_width_edit'] = 1
if 'part_length_edit' not in st.session_state:
    st.session_state['part_length_edit'] = 1
if 'part_quantity_edit' not in st.session_state:
    st.session_state['part_quantity_edit'] = 1
if 'selected_part_index' not in st.session_state:
    st.session_state['selected_part_index'] = 0

def reset_input_fields():
    """Сбрасывает поля ввода к стандартным значениям."""
    st.session_state.edit_mode = False
    st.session_state.edit_index = None
    st.session_state.part_width_edit = 1
    st.session_state.part_length_edit = 1
    st.session_state.part_quantity_edit = 1

# --- Описание интерфейса ---
st.title('Раскройщик тонировочной пленки')

st.info('Приложение работает на бесплатном сервере, поэтому первая загрузка может занять до нескольких минут. Пожалуйста, подождите.')

st.header('Параметры рулона:')
roll_width = st.number_input('Ширина (см):', key='roll_width_input', value=152, min_value=1, step=1, format="%d")
roll_length = st.number_input('Длина (см):', key='roll_length_input', value=3000, min_value=1, step=1, format="%d")

# --- Описание интерфейса ---
st.title('Раскройщик тонировочной пленки')

st.header('Параметры рулона:')
roll_width = st.number_input('Ширина (см):', value=152, min_value=1, step=1, format="%d")
roll_length = st.number_input('Длина (см):', value=3000, min_value=1, step=1, format="%d")

# --- Створки для раскроя: ---
st.header('Створки для раскроя:')

# --- ИЗМЕНЕНИЕ: Функции для кнопок редактирования ---
def set_edit_mode_on():
    if st.session_state.selected_part_index is not None:
        st.session_state.edit_mode = True
        st.session_state.edit_index = st.session_state.selected_part_index
        
        part_to_edit = st.session_state.parts_list[st.session_state.selected_part_index]
        st.session_state.part_width_edit = part_to_edit[0]
        st.session_state.part_length_edit = part_to_edit[1]
        st.session_state.part_quantity_edit = part_to_edit[2]

def delete_selected_part():
    if st.session_state.selected_part_index is not None:
        st.session_state.parts_list.pop(st.session_state.selected_part_index)
        reset_input_fields()

def update_selected_part():
    if st.session_state.edit_index is not None and st.session_state.part_quantity_edit > 0:
        st.session_state.parts_list[st.session_state.edit_index] = (
            st.session_state.parts_list[st.session_state.edit_index][0],
            st.session_state.parts_list[st.session_state.edit_index][1],
            st.session_state.part_quantity_edit
        )
        reset_input_fields()

# --- Поля для ввода ---
part_width_val = st.number_input('Ширина (см):', key='part_width', value=st.session_state.part_width_edit, min_value=1, step=1, format="%d", disabled=st.session_state.edit_mode)
part_length_val = st.number_input('Длина (см):', key='part_length', value=st.session_state.part_length_edit, min_value=1, step=1, format="%d", disabled=st.session_state.edit_mode)
part_quantity_val = st.number_input('Количество:', key='part_quantity', value=st.session_state.part_quantity_edit, min_value=1, format="%d")

# --- Кнопки для добавления/обновления ---
col1, col2 = st.columns(2)
with col1:
    if st.button('Внести в раскрой', disabled=st.session_state.edit_mode):
        if part_width_val > 0 and part_length_val > 0 and part_quantity_val > 0:
            st.session_state.parts_list.append((part_width_val, part_length_val, part_quantity_val))
            st.rerun()
        else:
            st.error('Пожалуйста, введите корректные значения для ширины, длины и количества.')

with col2:
    if st.button('Обновить размеры створки', disabled=not st.session_state.edit_mode, on_click=update_selected_part):
        pass # Логика перенесена в on_click

# --- Список добавленных створок ---
st.subheader('Список добавленных створок:')
if st.session_state.parts_list:
    df = pd.DataFrame(st.session_state.parts_list, columns=['Ширина (см)', 'Длина (см)', 'Количество (шт)'])
    st.dataframe(df.set_index(df.columns[0]))
    
    st.session_state.selected_part_index = st.selectbox(
        'Выберите створку для действия:',
        options=range(len(st.session_state.parts_list)),
        index=st.session_state.selected_part_index if st.session_state.selected_part_index < len(st.session_state.parts_list) else len(st.session_state.parts_list) -1,
        format_func=lambda i: f"Створка: {int(st.session_state.parts_list[i][0])}x{int(st.session_state.parts_list[i][1])} см, Количество: {st.session_state.parts_list[i][2]} шт."
    )
    
    col3, col4 = st.columns(2)
    with col3:
        st.button('Редактировать выбранную', on_click=set_edit_mode_on)

    with col4:
        st.button('Удалить выбранную', on_click=delete_selected_part)
        
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
        
        # --- ИЗМЕНЕНИЕ: Сначала рассчитываем использованную длину и площадь ---
        # Этот блок был перемещен выше
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

        # --- Визуализация ---
        # Теперь, когда abin_used_length рассчитана, можно создавать график
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
        
        # --- Отдельный цикл для отрисовки прямоугольников ---
        for rect in abin:
            ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, edgecolor='black', facecolor='skyblue'))
            center_x = rect.x + rect.width / 2
            center_y = rect.y + rect.height / 2
            ax.text(center_x, center_y, f'{int(rect.width)}x{int(rect.height)}', ha='center', va='center', fontsize=8)
            
        st.pyplot(fig)
        plt.close(fig)

        # --- Вывод результатов ---
        st.subheader("Общие результаты")
        abin_efficiency = (abin_used_area / (abin.width * abin.height)) * 100
        st.write(f"Использовано погонных метров: **{abin_used_length / 100:.2f} м**")
        st.write(f"Использовано квадратных метров: **{abin_used_area / 10000:.2f} м²**")
        st.write(f"Эффективность раскроя: **{abin_efficiency:.2f}%**")
        
        # --- Экспорт в CSV ---
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