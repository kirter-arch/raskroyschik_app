import PySimpleGUI as sg
from rectpack import newPacker
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Список для хранения деталей, которые нужно раскроить ---
parts_list = []

# --- Глобальные переменные для визуализации ---
fig = None
canvas_elem = None
canvas = None

# ---- Описание интерфейса ----
layout = [
    [sg.Text('Параметры рулона:', font=('Helvetica', 16))],
    [sg.Text('Ширина (см):'), sg.Input(key='-ROLL_WIDTH-', default_text='152')],
    [sg.Text('Длина (см):'), sg.Input(key='-ROLL_LENGTH-', default_text='3000')],
    [sg.HorizontalSeparator()],
    [sg.Text('Детали для раскроя:', font=('Helvetica', 16))],
    [sg.Text('Ширина (см):'), sg.Input(key='-PART_WIDTH-')],
    [sg.Text('Длина (см):'), sg.Input(key='-PART_LENGTH-')],
    [sg.Text('Количество:', size=(10, 1)), sg.Input(key='-PART_QUANTITY-', default_text='1', size=(5, 1))],
    [sg.Button('Добавить деталь', key='-ADD_PART-')],
    [sg.HorizontalSeparator()],
    [sg.Button('Рассчитать', key='-CALCULATE-'), sg.Button('Очистить', key='-CLEAR-'), sg.Button('Удалить выбранную', key='-DELETE-'), sg.Button('Выйти')],
    [sg.Text('Список добавленных деталей:', font=('Helvetica', 12))],
    [sg.Listbox(values=[], size=(40, 6), key='-PARTS_LISTBOX-', enable_events=True)],
    [sg.HorizontalSeparator()],
    [sg.Text('Результат раскроя:', font=('Helvetica', 16))],
    [sg.Output(size=(60, 10), key='-OUTPUT-')],
    [sg.Canvas(key='-CANVAS-')] # <-- Новый элемент: холст для визуализации
]

# ---- Создание окна ----
window = sg.Window('Раскройщик тонировочной пленки', layout, finalize=True)

# ---- Инициализация холста Matplotlib ----
def draw_figure(canvas, figure):
    """Рисует фигуру Matplotlib на холсте PySimpleGUI."""
    global canvas_elem
    canvas_elem = FigureCanvasTkAgg(figure, canvas)
    canvas_elem.draw()
    canvas_elem.get_tk_widget().pack(side='top', fill='both', expand=1)

# ---- Функция для обновления Listbox ----
def update_parts_listbox(window, parts_list):
    display_list = [f'Деталь: {w}x{h} см, Количество: {q} шт.' for w, h, q in parts_list]
    window['-PARTS_LISTBOX-'].update(display_list)

# ---- Цикл обработки событий ----
while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == 'Выйти':
        break

    if event == '-ADD_PART-':
        try:
            width = float(values['-PART_WIDTH-'])
            height = float(values['-PART_LENGTH-'])
            quantity = int(values['-PART_QUANTITY-'])
            
            if width <= 0 or height <= 0 or quantity <= 0:
                sg.popup_error('Ширина, длина и количество должны быть положительными числами.')
                continue

            parts_list.append((width, height, quantity))
            update_parts_listbox(window, parts_list)

            window['-PART_WIDTH-'].update('')
            window['-PART_LENGTH-'].update('')
            window['-PART_QUANTITY-'].update('1')

        except (ValueError, IndexError):
            sg.popup_error('Пожалуйста, введите корректные числа для ширины, длины и количества.')

    if event == '-CLEAR-':
        parts_list.clear()
        update_parts_listbox(window, parts_list)
        window['-ROLL_WIDTH-'].update('152')
        window['-ROLL_LENGTH-'].update('3000')
        window['-OUTPUT-'].update('')
        # Очищаем холст
        if canvas_elem:
            canvas_elem.get_tk_widget().destroy()
            canvas_elem = None
        
    if event == '-DELETE-':
        selected_indices = values['-PARTS_LISTBOX-']
        if selected_indices:
            for index in sorted(window['-PARTS_LISTBOX-'].get_indexes(), reverse=True):
                parts_list.pop(index)
            update_parts_listbox(window, parts_list)
        else:
            sg.popup_error('Пожалуйста, выберите деталь для удаления.')

    if event == '-CALCULATE-':
        try:
            roll_width = float(values['-ROLL_WIDTH-'])
            roll_length = float(values['-ROLL_LENGTH-'])

            all_parts = []
            for part in parts_list:
                width, height, quantity = part
                for _ in range(quantity):
                    all_parts.append((width, height))

            if not all_parts:
                sg.popup_error('Список деталей для раскроя пуст.')
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
            
            for abin in packer:
                abin_used_length = 0
                abin_used_area = 0
                for rect in abin:
                    ax.add_patch(plt.Rectangle((rect.x, rect.y), rect.width, rect.height, edgecolor='black', facecolor='skyblue'))
                    
                    center_x = rect.x + rect.width / 2
                    center_y = rect.y + rect.height / 2
                    
                    # --- ИЗМЕНЕНИЕ 1: Преобразуем в int для вывода ---
                    ax.text(center_x, center_y, f'{int(rect.width)}x{int(rect.height)}', ha='center', va='center', fontsize=8) 
                    
                    # --- ИЗМЕНЕНИЕ 2: Преобразуем в int для вывода ---
                    print(f"  Деталь: {int(rect.width)}x{int(rect.height)} см") 
                    abin_used_length = max(abin_used_length, rect.y + rect.height)
                    abin_used_area += rect.width * rect.height
                
                total_used_area += abin_used_area
                efficiency = (abin_used_area / (abin.width * abin.height)) * 100
                print("-" * 20)
                # --- ИЗМЕНЕНИЕ 3: Преобразуем в int для вывода ---
                print(f"Рулон: {int(abin.width)}x{int(abin.height)} см ({abin.height / 100:.2f} м в рулоне)") 
                print(f"Использовано погонных метров: {abin_used_length / 100:.2f} м")
                print(f"Использовано квадратных метров: {abin_used_area / 10000:.2f} м²")
                print(f"Эффективность раскроя: {efficiency:.2f}%")
                print("=" * 30)

            draw_figure(window['-CANVAS-'].TKCanvas, fig)
            plt.close(fig)
            
        except (ValueError, IndexError):
            sg.popup_error('Пожалуйста, введите корректные числа для параметров рулона.')
        except Exception as e:
            sg.popup_error(f'Произошла ошибка при расчете: {e}')

# ---- Закрытие окна ----
window.close()