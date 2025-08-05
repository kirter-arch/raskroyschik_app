import PySimpleGUI as sg
from rectpack import newPacker
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from datetime import datetime

# --- Список для хранения створок, которые нужно раскроить ---
parts_list = []
# --- Глобальные переменные для визуализации и результатов ---
fig = None
canvas_elem = None
canvas = None
last_calculation_results = []
summary_results = {}
# --- ИЗМЕНЕНИЕ: Переменная для отслеживания редактируемого элемента ---
edit_index = None

# ---- Описание интерфейса ----
layout = [
    [sg.Text('Параметры рулона:', font=('Helvetica', 16))],
    [sg.Text('Ширина (см):'), sg.Input(key='-ROLL_WIDTH-', default_text='152')],
    [sg.Text('Длина (см):'), sg.Input(key='-ROLL_LENGTH-', default_text='3000')],
    [sg.HorizontalSeparator()],
    [sg.Text('Створки для раскроя:', font=('Helvetica', 16))],
    [sg.Text('Ширина (см):'), sg.Input(key='-PART_WIDTH-')],
    [sg.Text('Длина (см):'), sg.Input(key='-PART_LENGTH-')],
    [sg.Text('Количество:', size=(10, 1)), sg.Input(key='-PART_QUANTITY-', default_text='1', size=(5, 1))],
    # --- ИЗМЕНЕНИЕ: Добавляем кнопку "Обновить" и кнопку "Редактировать" ---
    [sg.Button('Добавить створку', key='-ADD_PART-', size=(20,1)), 
     sg.Button('Обновить створку', key='-UPDATE_PART-', size=(20,1), visible=False)],
    [sg.HorizontalSeparator()],
    [sg.Button('Рассчитать', key='-CALCULATE-'), sg.Button('Очистить', key='-CLEAR-'), 
     sg.Button('Удалить выбранную', key='-DELETE-'), sg.Button('Редактировать створку', key='-EDIT_PART-', disabled=True)],
    [sg.Button('Сохранить в CSV', key='-SAVE_CSV-'), sg.Button('Выйти')],
    [sg.Text('Список добавленных створок:', font=('Helvetica', 12))],
    [sg.Listbox(values=[], size=(40, 6), key='-PARTS_LISTBOX-', enable_events=True)],
    [sg.HorizontalSeparator()],
    [sg.Text('Результат раскроя:', font=('Helvetica', 16))],
    [sg.Output(size=(60, 10), key='-OUTPUT-')],
    [sg.Canvas(key='-CANVAS-')]
]

# ---- Создание окна ----
window = sg.Window('Раскройщик тонировочной пленки', layout, finalize=True)

def draw_figure(canvas, figure):
    global canvas_elem
    if canvas_elem:
        canvas_elem.get_tk_widget().destroy()
    canvas_elem = FigureCanvasTkAgg(figure, canvas)
    canvas_elem.draw()
    canvas_elem.get_tk_widget().pack(side='top', fill='both', expand=1)

def update_parts_listbox(window, parts_list):
    display_list = [f'Створка: {int(w)}x{int(h)} см, Количество: {q} шт.' for w, h, q in parts_list]
    window['-PARTS_LISTBOX-'].update(display_list)

# --- ИЗМЕНЕНИЕ: Функция для сброса полей и состояния кнопок ---
def reset_ui():
    global edit_index
    edit_index = None
    window['-PART_WIDTH-'].update('')
    window['-PART_LENGTH-'].update('')
    window['-PART_QUANTITY-'].update('1')
    window['-PART_WIDTH-'].update(disabled=False)
    window['-PART_LENGTH-'].update(disabled=False)
    window['-ADD_PART-'].update(visible=True)
    window['-UPDATE_PART-'].update(visible=False)
    window['-EDIT_PART-'].update(disabled=True)
    window['-PARTS_LISTBOX-'].update(set_to_index=[], scroll_to_index=None)


# ---- Цикл обработки событий ----
while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == 'Выйти':
        break

    # --- ИЗМЕНЕНИЕ: Обработка события выбора элемента в списке ---
    if event == '-PARTS_LISTBOX-':
        if values['-PARTS_LISTBOX-']:
            window['-EDIT_PART-'].update(disabled=False)
        else:
            window['-EDIT_PART-'].update(disabled=True)

    # --- ИЗМЕНЕНИЕ: Обработка добавления новой створки ---
    if event == '-ADD_PART-':
        try:
            width = int(values['-PART_WIDTH-'])
            height = int(values['-PART_LENGTH-'])
            quantity = int(values['-PART_QUANTITY-'])
            
            if width <= 0 or height <= 0 or quantity <= 0:
                sg.popup_error('Ширина, длина и количество должны быть положительными числами.')
                continue

            parts_list.append((width, height, quantity))
            update_parts_listbox(window, parts_list)

            reset_ui()

        except (ValueError, IndexError):
            sg.popup_error('Пожалуйста, введите корректные числа для ширины, длины и количества.')

    # --- ИЗМЕНЕНИЕ: Обработка нажатия на кнопку "Редактировать" ---
    if event == '-EDIT_PART-':
        if values['-PARTS_LISTBOX-']:
            edit_index = window['-PARTS_LISTBOX-'].get_indexes()[0]
            part_to_edit = parts_list[edit_index]
            window['-PART_WIDTH-'].update(part_to_edit[0], disabled=True)
            window['-PART_LENGTH-'].update(part_to_edit[1], disabled=True)
            window['-PART_QUANTITY-'].update(part_to_edit[2])
            window['-ADD_PART-'].update(visible=False)
            window['-UPDATE_PART-'].update(visible=True)
            
    # --- ИЗМЕНЕНИЕ: Обработка нажатия на кнопку "Обновить" ---
    if event == '-UPDATE_PART-':
        try:
            new_quantity = int(values['-PART_QUANTITY-'])
            if new_quantity <= 0:
                sg.popup_error('Количество должно быть положительным числом.')
                
            
            # Обновляем количество в списке деталей
            parts_list[edit_index] = (parts_list[edit_index][0], parts_list[edit_index][1], new_quantity)
            update_parts_listbox(window, parts_list)
            
            reset_ui()
            
        except (ValueError, IndexError):
            sg.popup_error('Пожалуйста, введите корректное число для количества.')

    if event == '-CLEAR-':
        parts_list.clear()
        update_parts_listbox(window, parts_list)
        window['-ROLL_WIDTH-'].update('152')
        window['-ROLL_LENGTH-'].update('3000')
        window['-OUTPUT-'].update('')
        if canvas_elem:
            canvas_elem.get_tk_widget().destroy()
            reset_ui()
            
    if event == '-DELETE-':
        selected_indices = values['-PARTS_LISTBOX-']
        if selected_indices:
            for index in sorted(window['-PARTS_LISTBOX-'].get_indexes(), reverse=True):
                parts_list.pop(index)
            update_parts_listbox(window, parts_list)
            reset_ui()
        else:
            sg.popup_error('Пожалуйста, выберите створку для удаления.')

    if event == '-CALCULATE-':
        try:
            roll_width = int(values['-ROLL_WIDTH-'])
            roll_length = int(values['-ROLL_LENGTH-'])

            all_parts = []
            for part in parts_list:
                width, height, quantity = part
                for _ in range(quantity):
                    all_parts.append((width, height))

            if not all_parts:
                sg.popup_error('Список створок для раскроя пуст.')
                continue

            packer = newPacker()
            for part in all_parts:
                packer.add_rect(part[0], part[1])
            packer.add_bin(roll_width, roll_length)
            packer.pack()

            window['-OUTPUT-'].update('')
            
            print("--- Результаты раскроя ---")
            total_used_area = 0
            
            if canvas_elem:
                canvas_elem.get_tk_widget().destroy()
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_aspect('equal')
            ax.set_xlim(0, roll_width)
            ax.set_ylim(0, roll_length)
            ax.set_title("Схема раскроя")
            ax.set_xlabel("Ширина (см)")
            ax.set_ylabel("Длина (см)")

            last_calculation_results = []
            part_counts = {}
            
            for abin in packer:
                abin_used_length = 0
                abin_used_area = 0
                for rect in abin:
                    ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, edgecolor='black', facecolor='skyblue'))
                    
                    center_x = rect.x + rect.width / 2
                    center_y = rect.y + rect.height / 2
                    ax.text(center_x, center_y, f'{int(rect.width)}x{int(rect.height)}', ha='center', va='center', fontsize=8)
                    
                    print(f"  Створка: {int(rect.width)}x{int(rect.height)} см")
                    abin_used_length = max(abin_used_length, rect.y + rect.height)
                    abin_used_area += rect.width * rect.height
                    
                    part_key = (int(rect.width), int(rect.height))
                    if part_key in part_counts:
                        part_counts[part_key]['quantity'] += 1
                    else:
                        part_counts[part_key] = {
                            'part_width_cm': int(rect.width),
                            'part_length_cm': int(rect.height),
                            'part_area_sq_m': (rect.width * rect.height) / 10000,
                            'part_running_meters': rect.height / 100,
                            'quantity': 1
                        }

                total_used_area += abin_used_area
                abin_efficiency = (abin_used_area / (abin.width * abin.height)) * 100
                print("-" * 20)
                print(f"Рулон: {int(abin.width)}x{int(abin.height)} см ({abin.height / 100:.2f} м в рулоне)")
                print(f"Использовано погонных метров: {abin_used_length / 100:.2f} м")
                print(f"Использовано квадратных метров: {abin_used_area / 10000:.2f} м²")
                print(f"Эффективность раскроя: {abin_efficiency:.2f}%")
                print("=" * 30)

                summary_results['total_running_meters'] = abin_used_length / 100
                summary_results['total_area_sq_m'] = abin_used_area / 10000
                summary_results['efficiency'] = abin_efficiency
                summary_results['roll_width'] = abin.width
                summary_results['roll_length'] = abin.height

            last_calculation_results = list(part_counts.values())

            draw_figure(window['-CANVAS-'].TKCanvas, fig)
            plt.close(fig)
            
        except (ValueError, IndexError):
            sg.popup_error('Пожалуйста, введите корректные числа для параметров рулона.')
        except Exception as e:
            sg.popup_error(f'Произошла ошибка при расчете: {e}')
            
    if event == '-SAVE_CSV-':
        if not last_calculation_results:
            sg.popup_error('Сначала выполните расчет, чтобы сохранить результаты.')
            continue
            
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = sg.popup_get_file('Сохранить файл как...', save_as=True, no_window=True, 
                                           default_path=f'раскрой_{timestamp}.csv', file_types=(("CSV Files", "*.csv"),))

            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['Длина (см)', 'Ширина (см)', 'Количество (шт)', 'Погонные метры (м)', 'Площадь (м²)']
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                    
                    writer.writeheader()
                    
                    for row in last_calculation_results:
                        total_running_meters_for_part = row['part_running_meters'] * row['quantity']
                        total_area_for_part = row['part_area_sq_m'] * row['quantity']
                        
                        writer.writerow({
                            'Длина (см)': row['part_length_cm'],
                            'Ширина (см)': row['part_width_cm'],
                            'Количество (шт)': row['quantity'],
                            'Погонные метры (м)': total_running_meters_for_part,
                            'Площадь (м²)': total_area_for_part
                        })
                    
                    if summary_results:
                        f.write('\n\n')
                        f.write('Общие результаты:\n')
                        f.write(f'Ширина рулона (см);{int(summary_results["roll_width"])}\n')
                        f.write(f'Длина рулона (см);{int(summary_results["roll_length"])}\n')
                        f.write(f'Использовано погонных метров;{summary_results["total_running_meters"]:.2f} м\n')
                        f.write(f'Использовано квадратных метров;{summary_results["total_area_sq_m"]:.2f} м²\n')
                        f.write(f'Эффективность раскроя;{summary_results["efficiency"]:.2f}%\n')
                
                sg.popup(f'Результаты успешно сохранены в файл:\n{filename}')

        except Exception as e:
            sg.popup_error(f'Произошла ошибка при сохранении: {e}')

# ---- Закрытие окна ----
window.close()