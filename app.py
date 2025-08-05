import PySimpleGUI as sg

# ---- Шаг 1: Описание интерфейса ----
# Создаем список с элементами, которые будут в окне.
# sg.Text - это простой текст.
# sg.Input - это поле для ввода текста.
# sg.Button - это кнопка.
layout = [
    [sg.Text('Параметры рулона:', font=('Helvetica', 16))],
    [sg.Text('Ширина (мм):'), sg.Input(key='-ROLL_WIDTH-')],
    [sg.Text('Длина (мм):'), sg.Input(key='-ROLL_LENGTH-')],
    [sg.HorizontalSeparator()],
    [sg.Text('Детали для раскроя:', font=('Helvetica', 16))],
    [sg.Text('Ширина (мм):'), sg.Input(key='-PART_WIDTH-')],
    [sg.Text('Длина (мм):'), sg.Input(key='-PART_LENGTH-')],
    [sg.Button('Добавить деталь', key='-ADD_PART-')],
    [sg.HorizontalSeparator()],
    [sg.Button('Рассчитать', key='-CALCULATE-'), sg.Button('Выйти')]
]

# ---- Шаг 2: Создание окна ----
# Создаем окно с названием "Раскройщик" и нашим описанием (layout).
window = sg.Window('Раскройщик тонировочной пленки', layout)

# ---- Шаг 3: Цикл обработки событий ----
# Это главный цикл, который ждет, пока ты что-нибудь сделаешь (нажмешь кнопку).
while True:
    event, values = window.read() # Ждем события и получаем данные из полей ввода.

    # Если пользователь закрывает окно или нажимает "Выйти",
    # то мы выходим из цикла.
    if event == sg.WIN_CLOSED or event == 'Выйти':
        break

    # Если нажата кнопка "Добавить деталь"
    if event == '-ADD_PART-':
        # Здесь мы будем обрабатывать добавление детали.
        # Пока просто выведем то, что ввел пользователь, в консоль.
        print(f"Добавлена деталь: Ширина={values['-PART_WIDTH-']}, Длина={values['-PART_LENGTH-']}")

    # Если нажата кнопка "Рассчитать"
    if event == '-CALCULATE-':
        # Здесь будет логика расчета.
        # Пока просто выведем данные рулона в консоль.
        print("Начало расчета...")
        print(f"Параметры рулона: Ширина={values['-ROLL_WIDTH-']}, Длина={values['-ROLL_LENGTH-']}")

# ---- Шаг 4: Закрытие окна ----
window.close()