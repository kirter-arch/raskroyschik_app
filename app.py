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

st.header('Параметры рулона:')
roll_width = st.number_input('Ширина (см):', value=152, min_value=1, step=1, format="%d")
roll_length = st.number_input('Длина (см):', value=3000, min_value=1, step=1, format="%d")

st.header('Створки для раскроя:')
part_width_val = st.number_input('Ширина (см):', key='part_width', value=st.session_state.part_width_edit, min_value=1, step=1, format="%d", disabled=st.session_state.edit_mode)
part_length_val = st.number_input('Длина (см):', key='part_length', value=st.session_state.part_length_edit, min_value=1, step=1, format="%d", disabled=st.session_state.edit_mode)
part_quantity_val = st.number_input('Количество:', key='part_quantity', value=st.session_state.part_quantity_edit, min_value=1, format="%d")

# --- Кнопки для добавления/обновления ---
col1, col2 = st.columns(2)
with col1:
    if st.button('Добавить створку', disabled=st.session_state.edit_mode):
        if part_width_val > 0 and part_length_val > 0 and part_quantity_val > 0:
            st.session_state.parts_list.append((part_width_val, part_length_val, part_quantity_val))
            st.rerun()
        else:
            st.error('Пожалуйста, введите корректные значения для ширины, длины и количества.')

with col2:
    if st.button('Обновить створку', disabled=not st.session_state.edit_mode):
        if st.session_state.edit_index is not None and part_quantity_val > 0:
            st.session_state.parts_list[st.session_state.edit_index] = (
                st.session_state.parts_list[st.session_state.edit_index][0],
                st.session_state.parts_list[st.session_state.edit_index][1],
                part_quantity_val
            )
            reset_input_fields()
            st.rerun()
        else:
            st.error('Нечего обновлять или количество указано неверно.')

# --- Список добавленных створок ---
st.subheader('Список добавленных створок:')
if st.session_state.parts_list:
    df = pd.DataFrame(st.session_state.parts_list, columns=['Ширина (см)', 'Длина (см)', 'Количество (шт)'])
    st.dataframe(df.set_index(df.columns[0]))
    
    # --- ИЗМЕНЕНИЕ: Добавляем key для selectbox и делаем его более надежным ---
    st.session_state.selected_part_index = st.selectbox(
        'Выберите створку для действия:',
        options=range(len(st.session_state.parts_list)),
        index=st.session_state.selected_part_index if st.session_state.selected_part_index < len(st.session_state.parts_list) else len(st.session_state.parts_list) -1,
        format_func=lambda i: f"Створка: {int(st.session_state.parts_list[i][0])}x{int(st.session_state.parts_list[i][1])} см, Количество: {st.session_state.parts_list[i][2]} шт."
    )
    
    col3, col4 = st.columns(2)
    with col3:
        if st.button('Редактировать выбранную'):
            if st.session_state.selected_part_index is not None:
                st.session_state.edit_mode = True
                st.session_state.edit_index = st.session_state.selected_part_index
                
                part_to_edit = st.session_state.parts_list[st.session_state.selected_part_index]
                st.session_state.part_width_edit = part_to_edit[0]
                st.session_state.part_length_edit = part_to_edit[1]
                st.session_state.part_quantity_edit = part_to_edit[2]
                st.rerun()
            else:
                st.warning("Пожалуйста, сначала выберите створку из списка.")

    with col4:
        if st.button('Удалить выбранную створку'):
            # --- ИЗМЕНЕНИЕ: сбрасываем состояние после удаления ---
            if st.session_state.selected_part_index is not None:
                st.session_state.parts_list.pop(st.session_state.selected_part_index)
                reset_input_fields()
                st.rerun()
            else:
                st.warning("Пожалуйста, сначала выберите створку из списка.")
        
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
        
        # --- Визуализация ---
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_aspect('equal')
        ax.set_xlim(0, roll_width)
        ax.set_ylim(0, abin.height)
        ax.set_title("Схема раскроя")
        ax.set_xlabel("Ширина (см)")
        ax.set_ylabel("Длина (см)")
        
        part_counts = {}
        for rect in abin:
            ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, edgecolor='black', facecolor='skyblue'))
            center_x = rect.x + rect.width / 2
            center_y = rect.y + rect.height / 2
            ax.text(center_x, center_y, f'{int(rect.width)}x{int(rect.height)}', ha='center', va='center', fontsize=8)
            
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