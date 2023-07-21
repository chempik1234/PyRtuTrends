<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ru_RU" sourcelanguage="en">
<context>
    <name>MainWidget</name>
    <message>
        <location filename="main.py" line="596"/>
        <source>File</source>
        <translation>Файл</translation>
    </message>
    <message>
        <location filename="main.py" line="597"/>
        <source>Load settings</source>
        <translation>Загрузить настройки</translation>
    </message>
    <message>
        <location filename="main.py" line="598"/>
        <source>Save logs and plots</source>
        <translation>Сохранить логи и графики</translation>
    </message>
    <message>
        <location filename="main.py" line="599"/>
        <source>(DON'T CLICK) xlsx</source>
        <translation>(НЕ НАЖИМАТЬ) xlsx</translation>
    </message>
    <message>
        <location filename="main.py" line="600"/>
        <source>Open from file</source>
        <translation>Открыть из файла</translation>
    </message>
    <message>
        <location filename="main.py" line="602"/>
        <source>Connect to</source>
        <translation>Подключиться к</translation>
    </message>
    <message>
        <location filename="main.py" line="603"/>
        <source>Disconnect</source>
        <translation>Отключиться</translation>
    </message>
    <message>
        <location filename="main.py" line="604"/>
        <source>Start reading</source>
        <translation>Начать чтение</translation>
    </message>
    <message>
        <location filename="main.py" line="605"/>
        <source>Stop reading</source>
        <translation>Остановить чтение</translation>
    </message>
    <message>
        <location filename="main.py" line="606"/>
        <source>Help</source>
        <translation>Помощь</translation>
    </message>
    <message>
        <location filename="main.py" line="607"/>
        <source>About the program...</source>
        <translation>О программе...</translation>
    </message>
    <message>
        <location filename="main.py" line="608"/>
        <source>Language</source>
        <translation>Язык</translation>
    </message>
    <message>
        <location filename="main.py" line="609"/>
        <source>Inputs</source>
        <translation>Входы</translation>
    </message>
    <message>
        <location filename="main.py" line="610"/>
        <source>Auto-scroll</source>
        <translation>Авто-скролл</translation>
    </message>
    <message>
        <location filename="main.py" line="611"/>
        <source>Delay</source>
        <translation>Задержка</translation>
    </message>
    <message>
        <location filename="main.py" line="612"/>
        <source>View range</source>
        <translation>Видимый
промежуток</translation>
    </message>
    <message>
        <location filename="main.py" line="612"/>
        <source>Auto save</source>
        <translation>Автосохр.</translation>
    </message>
    <message>
        <location filename="main.py" line="612"/>
        <source>Time (from)</source>
        <translation>Время (от)</translation>
    </message>
    <message>
        <location filename="main.py" line="746"/>
        <source>To use this program, you must have either a modbus (RTU or TCP) connection or the plot files.
------
How to use?
#1 Recording.
Preparing: go to settings.json file which is placed in the current directory and change the PLC_reading_address dictionary which contains input registers that will be read. You can load your own settings file with File -> Load settings.

Registers' formats:
■ register_address (int) -> for simple int numbers stored in registers
■ [address, count] -> for floats stored in 2 or 4 registers
■ [address, evaluate_string] -> for converting int into float (sometimes float is stored in 1 register as int and the value needs to be divided by 1000), for example you can type "/1000" to divide by 1000
■ [address, bit, value_if_0, value_if_1] -> for boolean values stored as one bit of a register value; bits are enumerated from 0 right-to-left; use value_if_0 and value_if_1 to separate the graphs (example: if DI00 is on (0, 1) on Y axis, then DI01  should be on (1, 2) or something like that so they don't cover each other while having the same value)

Step 1. Set up a connection with Modbus -> Connect to
Step 2. Check if the status bar in the bottom of the window is green and click on Modbus -> Start reading.
Name the inputs before step 3 to show what each of them is related to (use the empty fields in the left sidebar). Those names will be saved with the logs.
Step 3. After recording everything you need, click on File -> Save logs and plots (.csv or .xlsx). The logs will save too.

#2 Reading the records
To read the records, use the File -> Open from file. After that the current connection will be terminated for file reading.
------
Menu file:
load settings: load a json file with connection settings, path to the file is defined by the user.
save logs and plots:
■ csv: creates files that store the plot and the logs, path to the files is defined by the user.
■ xlsx: creates files that store the plot and the logs, path to the files is defined by the user.
Note that *.xlsx files always load much longer so they aren't importable
------
Menu modbus:
■ connect to: creates a connection
■ disconnect: stops current connection
■ start/stop: similar to play/pause, these options can't be used when there's no connection and don't affect it
-----
Inputs:
■ auto scroll: only used when recording; automatically moves the plot along the x axis and sets the view range depending on value of "time range"
■ view range: sets the view range of the plot (hours : minutes : seconds)
■ delay:sets the delay between requests
■ time (from): is only available in file reading mode, it's used to make navigation easier in couple with view range field
-----
Current values tab shows the latest values of each graph but it also can get them for any X if the file reading mode is on.</source>
        <translation>Чтобы использовать эту программу, необходимо иметь или соединение по Modbus (RTU или TCP), или файлы графика.
-----
Как пользоваться?
#1 Запись
Подготовка: зайдите в файл settings.json, находящийся в текущей директории, и измените словарь PLC_reading_address, что содержит входы, которые будут читаться. Вы можете загрузить свой файл с настройками с помощью Файл - Загрузить настройки.

Форматы регистров:
■ адрес_регистра (int) -> для простых целых чисел, хранящихся в 1 регистре
■ [адрес, кол-во] -> для чисел с плавающей точкой (десятичных дробей), хранящихся в 2 или 4 регистрах
■ [адрес, строка_вычислений] -> для конвертирования целого числа в дробь (иногда дробь хранится в 1 регистре как целое число, и значение надо разделить на 1000), например, можно ввести "/1000" для деления на 1000
■ [адрес, бит, знач_если_0, знач_если_1] -> для логических значений, хранящихся как 1 бит в регистре; биты нумеруются с 0 справа налево; используйте знач_если_0 и знач_если_1, чтобы разделить графики (пример: если DI00 на (0, 1) по оси Y, то  DI01  должен быть на (1, 2) или как-то ещё, так что они не закрывают друг друга, когда имеют одинаковые значения)

Шаг 1. Установите соединение с помощью Modbus -> Подключиться к
Шаг 2. Проверьте, что статусная строка внизу окна зелёная, и нажмите на Modbus -> Начать чтение.
Назовите входы до 3 шаг, чтобы показать, к чему относится каждый из них (используйте пустые поля вводы в левой панели). Эти названия сохранятся вместе с логами.
Шаг 3. После записи всего необходимого, нажмите Файл -> Сохранить логи и графики (.csv или .xlsx). Логи тоже сохранятся.

#2 Чтение записей
Чтобы читать записи, воспользуйтесь опцией Файл -> Открыть из файла. После этого текущее соединение будет прекращено для чтения фала.
-----
Меню Файл:
Загрузить настройки: загрузите json-файл с настройками подключения, путь к файлу определяется пользователем.
Сохранить логи и графики:
■ csv: сохраняет файлы, которые содержат графики и логи, путь к файлам определяется пользователем.
■ xlsx: сохраняет файлы, которые содержат графики и логи, путь к файлам определяется пользователем.
Заметьте, что файлы *.xlsx всегда загружаются гораздо дольше, поэтому не импортируются.
-----
Меню Modbus:
■ Подключиться к: создаёт соединение
■ Отключиться: прекращает текущее соединение
■ Начать/остановить чтение: то же, что и
-----
Входы:
■ автоприбл.: используется только во время записи; автоматически двигает график по оси x и задаёт область видимости в зависимости от значения "временного промежутка"
■ временной промежуток: задаёт область видимости графика (часы : минуты : секунды)
■ задержка: задаёт задержку между запросами
-----
Вкладка "Текущие значения" показывает последние значения всех графиков, но может также получить их для любого X в режиме чтения файла.</translation>
    </message>
    <message>
        <location filename="main.py" line="713"/>
        <source>Remaining time</source>
        <translation>Оставшееся время</translation>
    </message>
    <message>
        <location filename="main.py" line="651"/>
        <source>Requests:</source>
        <translation>Запросы:</translation>
    </message>
    <message>
        <location filename="main.py" line="651"/>
        <source>Valid responses:</source>
        <translation>Нормальные ответы:</translation>
    </message>
    <message>
        <location filename="main.py" line="636"/>
        <source>If you quit, any unsaved data will be lost! Do you want to save the plot?</source>
        <translation>Если Вы выйдете, любые несохранённые данные будут утеряны! Вы хотите сохранить график?</translation>
    </message>
    <message>
        <location filename="main.py" line="642"/>
        <source>Choose the extension:</source>
        <translation>Выберите расширение:</translation>
    </message>
    <message>
        <location filename="main.py" line="960"/>
        <source>Plot</source>
        <translation>График</translation>
    </message>
    <message>
        <location filename="main.py" line="961"/>
        <source>Current values</source>
        <translation>Текущие значения</translation>
    </message>
    <message>
        <location filename="main.py" line="1015"/>
        <source>Get from time:</source>
        <translation>Получить из времени:</translation>
    </message>
</context>
</TS>
