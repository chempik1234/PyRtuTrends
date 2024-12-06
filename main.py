from random import randint
from ui import main_res
import sys, json, pyqtgraph, numpy, csv, xlsxwriter, openpyxl
from pyqtgraph.exporters import *
from datetime import datetime
from PyQt5 import uic, QtSvg
from PyQt5.QtWidgets import QWidget, QComboBox, QApplication, QPushButton, QListWidgetItem, QMainWindow, \
    QLabel, QLineEdit, QFileDialog, QVBoxLayout, QCheckBox, QMessageBox, QAction, QDateTimeEdit, \
    QScrollArea, QGroupBox, QProgressBar, QTimeEdit, QSplashScreen, QGridLayout, QHBoxLayout, QLCDNumber, QFormLayout, QFrame
from PyQt5.QtCore import QTimer, QEvent, Qt, QDateTime, QTranslator
from PyQt5.QtGui import QIcon, QResizeEvent, QPixmap, QPainter
from time import time
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client import ModbusSerialClient
from pyModbusTCP.client import ModbusClient
import serial.tools.list_ports
TCP_IP, RTU, PC, PLC, time_template = "TCP/IP", "RTU", "PC", "PLC", "%H:%M:%S"
LANGUAGES = {'English': '', "Русский": 'en-ru'}
FULL_PARITY = {"E": "Even", "O": "Odd", "N": "None"}
PLC_Reading_Address, RTU_settings, TCP_IP_settings, CHANNEL_NAMES, COLORS, Y_RANGE, UNIT_ID = {}, {}, {}, [], [], [], 1
current_date = ''
current_time = ''


def h_v_decode(string: str):
    if not isinstance(string, str) or len(string) <= 1 or not string[1:].isdigit() or not string[0].isalpha():
        raise ValueError
    res, mod, num_str, a = 0, 10, string[1:], len(string) - 1
    if string[0].lower() == 'v':
        mod = 8
    elif string[0].lower() == 'h':
        mod = 16
    for i, s in enumerate(num_str):
        res += int(s) * mod ** (len(num_str) - 1 - i)
    return res


def load_settings(path):
    with open(path, 'r', encoding="UTF-8") as file:
        json_data = json.load(file)
        global PLC_Reading_Address, RTU_settings, TCP_IP_settings, CHANNEL_NAMES, COLORS, Y_RANGE, UNIT_ID
        PLC_Reading_Address, RTU_settings, TCP_IP_settings, CHANNEL_NAMES, COLORS, Y_RANGE, UNIT_ID =\
            json_data["PLC_Reading_Address"], json_data.get("RTU_settings"),\
            json_data.get("TCP/IP_settings"), json_data.get("Channel_names"), json_data.get("Colors"),\
            json_data.get("Y_range"), json_data.get("unit_id")
        if not RTU_settings:
            RTU_settings = {}
        if not TCP_IP_settings:
            TCP_IP_settings = {}
        if not isinstance(UNIT_ID, int) or (isinstance(UNIT_ID, int) and UNIT_ID < 1):
            UNIT_ID = 1
        if not COLORS:
            COLORS = []
        if not CHANNEL_NAMES:
            CHANNEL_NAMES = []
        if not Y_RANGE:
            Y_RANGE = [4, 20]
        for key, item in PLC_Reading_Address.items():
            if isinstance(item, list) and isinstance(item[0], str):
                item[0] = h_v_decode(item[0])
            elif isinstance(item, str):
                PLC_Reading_Address[key] = h_v_decode(item)
        return PLC_Reading_Address, RTU_settings, TCP_IP_settings, CHANNEL_NAMES, COLORS, Y_RANGE, UNIT_ID


load_settings("./settings.json")


def qdt_from_dt(datetime_start):
    return QDateTime.fromMSecsSinceEpoch(int(datetime_start.timestamp() * 1000))


def msecs_from_num_mod(num, mod):
    if mod == 's':
        num *= 1000
    elif mod == 'm':
        num *= 1000 * 60
    elif mod == 'h':
        num *= 1000 * 60 * 60
    elif mod == 'd':
        num *= 1000 * 60 * 60 * 24
    return num


def validate_ip_address(ip):
    octects = ip.split(".")
    if len(octects) != 4:
        return False
    for number in octects:
        if not isinstance(int(number), int):
            return False
        if int(number) < 0 or int(number) > 255:
            return False
    return True


def start_stop_dt_from_filename(filename):
    """Divides the filename and converts the halves to datetime"""
    start_str, stop_str = filename.split('-DIV-')
    start_dt = datetime.fromisoformat(start_str.split()[0] + " " + start_str.split()[1].replace('-', ':'))
    stop_dt = datetime.fromisoformat(stop_str.split()[0] + " " + stop_str.split()[1].replace('-', ':'))
    return start_dt, stop_dt


def make_2_dgs(string, k=2):
    return '0' * (k - len(string)) + string


def hex_col_str(rgb):
    return ''.join([make_2_dgs(str(hex(i))[2: ]) for i in rgb])


class MainWidget(QMainWindow):
    def __init__(self, ):
        splash = QSplashScreen(QPixmap('./ui/splash.png'))
        splash.show()
        # super(QWidget, self).__init__(parent)  # на случай QWidget
        super().__init__()
        self.setWindowIcon(QIcon("ui/icon.ico"))
        uic.loadUi("ui/main_widget.ui", self)
        self.centralWidget().setLayout(self.verticalLayout)
        self.groupBox.setLayout(self.verticalLayout_2)
        self.statusLabel, self.requests_label, self.responses_label =\
            QLabel(self), QLabel(self), QLabel(self)
        self.requests_amount = self.valid_responses_amount = 0
        self.other_statusbar_widgets = []
        self.statusBar().addWidget(self.requests_label)
        self.statusBar().addWidget(self.responses_label)
        self.statusBar().addWidget(self.statusLabel)
        self.logs = []
        self.has_ever_connected = False  # для записи "First connection at" в логе
        '''##############################################################################
        ДЛЯ ВИДЖЕТА PLOTWIDGET #######################################################'''
        self.miny, self.maxy = None, None  # минимум/максимум функции для setYRange
        self.MIN_XSCALE, self.MAX_XSCALE = 1, 24 * 3600
        self.XSCALE = 0  # (self.MIN_XSCALE + self.MAX_XSCALE) / 2  # видимость по x для setXRange
        self.YRANGE_MIN, self.YRANGE_MAX = 4, 20
        if Y_RANGE:
            self.YRANGE_MIN, self.YRANGE_MAX = Y_RANGE
        self.auto_scale_on = True
        self.auto_scale_checkbox.setChecked(True)
        '''##############################################################################
        СОЗДАНИЕ ВКЛАДКИ 2 #############################################################'''
        self.tab_scan.setLayout(self.tab2grid)
        # tab_scan_layout = QHBoxLayout()                         # tab (QWidget)
        # tab_scan_layout.addWidget(self.scrollAreaScan)          # -- tab2grid (QHBoxLayout)
        # self.tab_scan.setLayout(tab_scan_layout)                # ---- scrollAreaScan (QScrollArea)
        scroll_area_content_scan = QWidget(self)                # ------ scroll_area_content_scan (QWidget)
        self.tab_scan_form_layout = QFormLayout(scroll_area_content_scan)
        self.scrollAreaScan.setWidget(scroll_area_content_scan) # -------- tab_scan_form_layout (QFormLayout)
        self.scrollAreaScan.setWidgetResizable(True)
        '''##############################################################################
        СОЗДАНИЕ ГРАФИКА #############################################################'''
        #
        # self.tabWidget.removeWidget(self.placeholder_plot)
        # self.placeholder_plot.close()
        self.colors = COLORS.copy()
        axis = pyqtgraph.DateAxisItem(orientation='bottom')
        self.plot_widget = pyqtgraph.PlotWidget(self, axisItems={'bottom': axis})
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        layout_just_for_tab_with_plot = QHBoxLayout(self)
        layout_just_for_tab_with_plot.addWidget(self.plot_widget)
        self.tab_plot.setLayout(layout_just_for_tab_with_plot)
        # self.horizontalLayout.addWidget(self.plot_widget)
        self.times = []
        self.times_xs = []
        '''##############################################################################
        СОЗДАНИЕ СХЕМЫ ###############################################################'''
        # self.schema_widget = QLabel()
        # renderer =  QtSvg.QSvgRenderer('schema.svg')
        # painter = QPainter(self.schema_widget)
        # # painter.begin()
        # renderer.render(painter)
        # self.schema_frame = QFrame(self)
        # layout_just_for_tab_with_schema = QHBoxLayout(self)
        # layout_just_for_tab_with_schema.addWidget(self.schema_frame)
        # self.tab_image.setLayout(layout_just_for_tab_with_schema)

        self.schema_widget = QFrame()

        self.schema_image_widget = QLabel(self.schema_widget)
        schema_pixmap =  QPixmap('schema.png')
        self.schema_image_widget.setPixmap(schema_pixmap)

        layout_just_for_tab_with_schema = QHBoxLayout(self)
        layout_just_for_tab_with_schema.addWidget(self.schema_widget)

        QLabel("destroyer", self.schema_widget)

        # self.schema_image_widget.setLayout(schema_layout)
        self.tab_image.setLayout(layout_just_for_tab_with_schema)

        '''#####################################'''
        self.start_time, self.datetime_start = time(), QDateTime.currentDateTime().toLocalTime()  # datetime.now()
        self.start_secs_epoch = self.datetime_start.toSecsSinceEpoch()
        '''##############################################################################
        ТАЙМЕРЫ ДЛЯ ОБНОВЛЕНИЯ #######################################################'''
        self.file_open_mode = False  # если он True, то при начале новой записи всё стирается
        self.has_made_time_marks_in_file_open_mode = False
        self.read_timer = QTimer()
        self.set_read_timer(100)  # обновление графика каждые 100мс
        self.read_timer.timeout.connect(self.update_plot)
        self.scroll_timer = QTimer()
        self.scroll_timer.setInterval(50)
        self.scroll_timer.timeout.connect(self.scroll_plot)
        self.scroll_timer.start()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.autosave)
        self.set_save_timer()
        '''##############################################################################
        ИНИЦИАЛИЗАЦИЯ СОЕДИНЕНИЯ #####################################################'''
        self.modbus_client = None
        self.reading = None
        self.stop_reading_action_triggered()
        self.unit_id = UNIT_ID
        self.connect_to(None)
        '''##############################################################################
        ФУНКЦИИ ДЛЯ КНОПОК ###########################################################'''
        self.actionConnect_to.triggered.connect(self.connect_btn_click)
        self.actionDisconnect.triggered.connect(self.disconnect_btn_click)
        self.actionLoad_settings.triggered.connect(self.load_settings_btn_click)
        self.actionSave_settings.triggered.connect(self.save_settings_btn_click)
        self.auto_scale_checkbox.stateChanged.connect(self.toggle_auto_scale)
        self.actionStart_reading.triggered.connect(self.start_reading_action_triggered)
        self.actionStop_reading.triggered.connect(self.stop_reading_action_triggered)
        self.actionOpen_from_file.triggered.connect(self.action_open_from_file_triggered)
        self.actionWriteCsv.triggered.connect(self.write_csv)
        self.action_xlsx.triggered.connect(self.write_xlsx)
        self.actionAbout_the_program.triggered.connect(self.about_triggered)
        self.actionHelp.triggered.connect(self.help_triggered)
        self.rangeEdit.timeChanged.connect(self.range_changed)
        self.timeFromEdit.timeChanged.connect(self.set_x_range_file_open_mode)
        self.set_xscale(60)
        self.autoSaveComboBox.currentTextChanged.connect(self.set_save_timer)
        self.delayEdit.currentTextChanged.connect(self.delay_changed)
        self.colorsButton.triggered.connect(self.randomize_colors)
        self.get_from_dt_field.dateTimeChanged.connect(self.get_from_dt_changed)
        '''##############################################################################
        СОЗДАНИЕ CHECKBOX ДЛЯ ВСЕХ ВХОДОВ ############################################'''
        self.input_name_to_register_widget_plot_item_LCD = {}
        self.ai_names_edits = []
        scroll_area_content = QWidget()
        self.inputsLayout = QVBoxLayout(scroll_area_content)
        self.scrollArea.setWidget(scroll_area_content)
        self.scrollArea.setWidgetResizable(True)
        self.set_input_checkboxes(PLC_Reading_Address)
        '''##############################################################################
        ПЕРЕВОДЧИК ###################################################################'''
        self.ls = []
        for name, l in LANGUAGES.items():
            qa = QAction(name)
            self.menuLanguage.addAction(qa)
            self.ls.append(qa)
            qa.triggered.connect(self.language_action)
        self.trans = QTranslator(self)
        self.retranslateUi()
        self.set_file_open_mode(False)
        splash.close()

    def note_in_log(self, text):
        """
        Makes a note in logs that will be shown in ListWidget and can be saved
        :param text: text of the created note
        """
        self.output_list_widget.addItem(QListWidgetItem(text))
        self.logs.append(text)

    def start_reading_action_triggered(self):
        """
        Starts the modbus reading process and makes a note in log about it. Resets the sidebar and the plots if a file is opened.
        :return: None
        """
        if self.modbus_client:
            self.note_in_log("Started reading at " + str(datetime.now()) + " (There was a connection)")
        else:
            self.note_in_log("Started reading at " + str(datetime.now()) + " (WITH NO CONNECTION)")
        if self.file_open_mode:
            self.start_time = time()
            self.datetime_start = QDateTime.currentDateTime().toLocalTime()  # datetime.now()
            self.start_secs_epoch = self.datetime_start.toSecsSinceEpoch()
            self.set_file_open_mode(False)
            # self.times, self.times_xs = [], []
            # self.set_time_marks(self.times, self.times_xs)
        self.reading = True
        self.actionStart_reading.setEnabled(False)
        self.actionStop_reading.setEnabled(True)

    def stop_reading_action_triggered(self):
        """
        Stops the modbus reading process and makes a note in log about it. Resets the sidebar and the plots if a file is opened.
        :return: None
        """
        if self.modbus_client:
            self.note_in_log("Paused at " + str(datetime.now()))
        if self.file_open_mode:
            self.has_made_time_marks_in_file_open_mode = False
            self.set_file_open_mode(False)
            self.times, self.times_xs = [], []
            # self.set_time_marks(self.times, self.times_xs)
            self.set_input_checkboxes()
        self.reading = False
        self.actionStop_reading.setEnabled(False)
        self.actionStart_reading.setEnabled(True)

    def randomize_colors(self):
        self.colors = []
        for r_w_p_l in self.input_name_to_register_widget_plot_item_LCD.keys():
            color = [float(randint(1, 255)), float(randint(0, 255)), float(randint(0, 255))]
            color = [i * 255 / max(color) for i in color]
            if sum(color) / 3 > 200:
                color = [i / 1.5 for i in color]
            color = list(map(int, list(color)))
            self.colors.append(color)
        self.give_colors(self.colors)

    def give_colors(self, colors):
        for i, r_w_p_l in enumerate(self.input_name_to_register_widget_plot_item_LCD.values()):
            r_w_p_l[2].setPen(pyqtgraph.mkPen(color=colors[i], width=randint(1, 3)))
            br = 0.2126 * colors[i][0] + 0.7152 * colors[i][1] + 0.0722 * colors[i][2]
            bg = "white"
            if br > 200:
                bg = "gray"
            r_w_p_l[1].setStyleSheet("QCheckBox{color: #" + hex_col_str(colors[i]) + "; background:" + bg + "}")

    def set_input_checkboxes(self, address=None, start_time=None, datetime_start=None, ai_names_texts=None):
        """
        Resets the plot, the sidebar, the scan tab and the time variables (start_time, datetime_start) of the MainWidget object.
        :param address: may contain a dictionary {name : register} or {name : [register, count]}
        :param start_time: timestamp of the moment when the plot was reset or the reading was started,
        used for file reading.
        :param datetime_start: datetime of the moment when the plot was reset or the reading was started,
        used for file reading.
        :param ai_names_texts: a list of string that will be typed in the LineEdits of the sidebar.
        :return:
        """
        if not address:
            address = PLC_Reading_Address
        for register_widget_plot_lcd in self.input_name_to_register_widget_plot_item_LCD.values():
            self.inputsLayout.removeWidget(register_widget_plot_lcd[1])
            self.plot_widget.removeItem(register_widget_plot_lcd[2])
        for i in range(self.tab_scan_form_layout.rowCount()):
            self.tab_scan_form_layout.removeRow(0)
        self.input_name_to_register_widget_plot_item_LCD.clear()
        if not ai_names_texts:
            ai_names_texts = CHANNEL_NAMES.copy()
        if self.ai_names_edits:
            for i in self.ai_names_edits:
                self.inputsLayout.removeWidget(i)
        self.ai_names_edits = []
        for i, name_reg in enumerate(address.items()):
            name, reg = name_reg
            cb, le = QCheckBox(self), QLineEdit(self)
            le.textChanged.connect(self.ai_text_ch)
            if ai_names_texts and i < len(ai_names_texts):
                le.setText(ai_names_texts[i])
            self.ai_names_edits.append(le)
            self.inputsLayout.addWidget(cb)
            self.inputsLayout.addWidget(le)
            cb.setText(name)
            cb.setChecked(True)
            cb.stateChanged.connect(self.change_plot_visibility)
            self.plot_widget.addLegend()
            num = QLCDNumber()
            reg_num, reg_type = reg, "number"
            if isinstance(reg, list) or isinstance(reg, tuple):
                reg_num = reg[0]
                if len(reg) != 2:
                    reg_type = "boolean"
            self.tab_scan_form_layout.addRow(f"{name} ({make_2_dgs(str(reg_num), 5)} | {reg_type}):", num)
            num.display(-1)
            self.input_name_to_register_widget_plot_item_LCD[name] =\
                [reg, cb,
                 self.plot_widget.plot(name=name), num]
        if not self.colors or len(self.colors) < len(self.ai_names_edits):
            self.randomize_colors()
        else:
            self.give_colors(self.colors)
        if not start_time:
            start_time = time()
        if not datetime_start:
            self.datetime_start = QDateTime.currentDateTime().toLocalTime()
        else:
            if not isinstance(datetime_start, QDateTime):
                datetime_start = qdt_from_dt(datetime_start)
            self.datetime_start = datetime_start
        self.start_time = start_time
        self.start_secs_epoch = self.datetime_start.toSecsSinceEpoch()

    def ai_text_ch(self):
        """The handler of channel names inputs that removes all ';' symbols"""
        if isinstance(self.sender(), QLineEdit) and ';' in self.sender().text():
            self.sender().setText(self.sender().text().replace(';', ''))

    def set_read_timer(self, delay=None):
        """Sets the interval between reading if delay param is greater than 0 and is an int.
        :param delay: the interval in mseconds (should be an int greater than 0 otherwise reading will be stopped)
        :return: True if the interval is valid and reading isn't stoppped
        """
        if isinstance(delay, int) and delay > 0:
            self.read_timer.setInterval(delay)
            self.read_timer.start()
            self.actionStart_reading.setEnabled(False)
            self.actionStop_reading.setEnabled(True)
            return True
        else:
            self.actionStart_reading.setEnabled(True)
            self.actionStop_reading.setEnabled(False)
            self.read_timer.stop()
        return False

    def set_save_timer(self):
        """Sets the interval between saving depending on autoSaveComboBox.
        :param delay: the interval in mseconds
        :return: True if the interval is valid and reading isn't stoppped
        """
        text = self.autoSaveComboBox.currentText()
        if ' ' not in text or ' ' in text and not text.split()[0].isdigit():
            self.auto_save_timer.stop()
            return
        num, mod = text.split()
        delay = msecs_from_num_mod(int(num), mod)
        if isinstance(delay, int) and delay > 0:
            self.auto_save_timer.setInterval(delay)
            self.auto_save_timer.start()
            return True
        else:
            self.auto_save_timer.stop()
        return False

    def file_dialog(self, filter_text, file_format_with_dot, mode='r'):
        """
        Used to define a path to a file with QFileDialog.
        :param filter_text: Short description of what the file should contain.
        :param file_format_with_dot: file extension such as .csv, .png, .jpg, etc.
        :param mode: use 'r' for obtaining an existing file or 'w' to also be able to create a new one
        :return:
        """
        fd = QFileDialog(self)
        mode_ = QFileDialog.ExistingFile
        if mode == 'w':
            mode_ = QFileDialog.AnyFile
        fd.setFileMode(mode_)
        fd.setNameFilter(f"{filter_text} (*{file_format_with_dot})")
        if fd.exec_():
            filename = fd.selectedFiles()[0]
            if not filename.endswith(file_format_with_dot):
                filename += file_format_with_dot
            return filename

    def load_settings_btn_click(self):
        """The handler of Load settings Action (loads settings and resets the sidebar and the plot)"""
        filename = self.file_dialog("JSON files", ".json")
        if filename:
            load_settings(filename)
            self.colors = COLORS
            if Y_RANGE:
                self.YRANGE_MIN, self.YRANGE_MAX = Y_RANGE
            self.set_input_checkboxes()

    def save_settings_btn_click(self):
        """The handler of Save settings Action (saves changes in the settings and put them into a json file)"""
        filename = self.file_dialog("JSON files", '.json', 'w')
        if filename:
            with open(filename, 'w', encoding="UTF-8") as file:
                data = {"PLC_Reading_Address": PLC_Reading_Address,
                        "Channel_names": [i.text() for i in self.ai_names_edits],
                        "RTU_settings": RTU_settings,
                        "TCP/IP_settings": TCP_IP_settings,
                        "Colors": self.colors,
                        "Y_range": [self.YRANGE_MIN, self.YRANGE_MAX],
                        "unit_id": self.unit_id}
                if isinstance(self.modbus_client, ModbusClient):
                    data["TCP/IP_settings"] = {"ip": self.modbus_client.host,
                                               "ip_port": self.modbus_client.port}
                elif isinstance(self.modbus_client, ModbusSerialClient):
                    data["RTU_settings"] = {"COM": self.modbus_client.params.port,
                                            "baudrate": self.modbus_client.params.baudrate,
                                            "stopbits": self.modbus_client.params.stopbits,
                                            "bytesize": self.modbus_client.params.bytesize,
                                            "parity": FULL_PARITY[self.modbus_client.params.parity]
                    }
                json.dump(data, file)

    def connect_btn_click(self):
        """The handler of Connect to Action (shows a connection form)"""
        if not self.modbus_client:
            ConnectForm(self, main_widget=self).show()

    def about_triggered(self):
        """The handler of Help Action (shows an "about" window)"""
        AboutWindow(self).show()

    def help_triggered(self):
        """The handler of Help Action (shows a "help" window)"""
        HelpWindow(self).show()

    def disconnect_btn_click(self):
        """The handler of Disconnect Action"""
        self.connect_to(None)

    def toggle_auto_scale(self):
        """The handler of auto-scale checkbox that toggles auto scale
        :return: None"""
        if self.file_open_mode:
            self.auto_scale_on = False
            self.auto_scale_checkbox.setCheckState(0)
        else:
            self.rangeEdit.setEnabled(self.auto_scale_checkbox.isChecked())
            self.auto_scale_on = self.auto_scale_checkbox.isChecked()

    def delay_changed(self):
        """
        The handler of delayEdit that coverts the chosen value in ms and calls self.set_read_timer to set the delay between requests.
        :return:
        """
        num_str, mod = self.delayEdit.currentText().split()
        num = msecs_from_num_mod(int(num_str), mod)
        self.set_read_timer(num)

    def range_changed(self):
        """
        The handler of rangeEdit (TimeEdit) that converts the chosen time into seconds and calls self.set_xscale to set the view range that is used when auto scale is turned on.
        :return: None
        """
        time_ = self.rangeEdit.time()
        h, s, m = time_.hour(), time_.second(), time_.minute()
        self.set_xscale(h * 3600 + m * 60 + s)
        if self.file_open_mode:
            self.set_x_range_file_open_mode()

    def get_from_dt_changed(self):
        x = self.get_from_dt_field.dateTime().toSecsSinceEpoch()
        for reg_w_pl_lcd in self.input_name_to_register_widget_plot_item_LCD.values():
            pl, lcd = reg_w_pl_lcd[2: 4]
            xs, ys = pl.getData()
            prev_x, past_x, ind_prev, ind_past = xs[0], xs[-1], 0, -1
            if not prev_x <= x <= past_x:
                return
            for ind, xx in enumerate(xs):
                if prev_x < xx <= x:
                    prev_x, ind_prev = xx, ind
                if x <= xx < past_x:
                    past_x, ind_past = xx, ind
            # prev_x, past_x = max([i for i in pl.getData()[0] if i < x]), min([i for i in pl.getData()[0] if i > x])
            prev_y, past_y = ys[ind_prev], ys[ind_past]
            if prev_x == past_x:
                lcd.display(prev_y)
            else:
                k = (x - past_x) / (past_x - prev_x)
                lcd.display(prev_y * k + past_y * (1 - k))

    def set_xscale(self, seconds):
        """
        Sets the view range in seconds that's used if auto scale is turned on
        :param seconds: range in seconds
        :return: None
        """
        self.XSCALE = max(min(seconds, self.MAX_XSCALE), self.MIN_XSCALE)

    def set_x_range_file_open_mode(self):
        if not self.file_open_mode:
            return
        time_ = self.timeFromEdit.time()
        h, s, m = time_.hour(), time_.second(), time_.minute()
        secs = h * 3600 + m * 60 + s
        dt_view = datetime.fromtimestamp(self.plot_widget.visibleRange().x())
        start = datetime(year=dt_view.year, month=dt_view.month, day=dt_view.day, minute=0,
                         second=0, microsecond=0).timestamp() + secs
        # dt = datetime(year=dt_view.)
        self.plot_widget.setXRange(start, start + self.XSCALE)

    def scroll_plot(self):
        """
        Scrolls the plot along the timeline if auto scale is turned on.
        :return: None
        """
        if self.auto_scale_on:
            self.plot_widget.setXRange(time() - self.start_time - self.XSCALE + self.start_secs_epoch,
                                       time() - self.start_time + self.start_secs_epoch)
            self.plot_widget.setYRange(self.YRANGE_MIN, self.YRANGE_MAX)

    def update_plot(self):
        """
        Reads values from registers (only if there's a connection) and puts them into the PlotWidget.
        :return: None
        """
        if not self.reading:
            return
        for name, reg_wid_plot_lcd in self.input_name_to_register_widget_plot_item_LCD.items():
            register, _, some_plot, lcd = reg_wid_plot_lcd
            xs, ys = some_plot.getData()
            if xs is None:
                xs = numpy.empty((0,))
            if ys is None:
                ys = numpy.empty((0,))
            value = self.read_one_modbus_register(register)
            some_plot.setData(numpy.append(xs, time() - self.start_time +
                                           self.datetime_start.toSecsSinceEpoch()),
                              numpy.append(ys, value))
            if (isinstance(register, list) or isinstance(register, tuple)) and len(register) != 2:
                value_if_1 = value == register[3]  # if value is register[3] then it's True (1) else it's False (0)
                lcd.display(int(value_if_1))
            else:
                lcd.display(value)
        _translate = QApplication.translate
        self.requests_label.setText(_translate("MainWidget", "Requests:") + " " + str(self.requests_amount))
        self.responses_label.setText(_translate("MainWidget", "Valid responses:") + " " +
                                     str(self.valid_responses_amount))

    def change_plot_visibility(self):
        """
        The handler of the checkboxes in the sidebar that are used to change plots visibility.
        :return: None
        """
        if not self.sender().isChecked():
            self.input_name_to_register_widget_plot_item_LCD[self.sender().text()][2].hide()
            # self.plot_widget.removeItem(self.input_name_to_register_widget_plot_item[self.sender().text()][2])
        else:
            self.input_name_to_register_widget_plot_item_LCD[self.sender().text()][2].show()
            # self.plot_widget.addItem(self.input_name_to_register_widget_plot_item[self.sender().text()][2])

    def connect_to(self, modbus_client, unit_id=None):
        """
        Connects to a client or disconnects if modbus_client param is None. After that the notes in logs are made, statusbar is changed and the plot is reset.
        :param modbus_client: None or a client to connect to (ModbusClient or ModbusSerialClient)
        :param unit_id: None or an int >= 1 that is set as self.unit_id
        :return: True if there is a connection, else False
        """
        for i in self.other_statusbar_widgets:
            self.statusBar().removeWidget(i)
        self.other_statusbar_widgets = []
        texts_for_statusbar = []
        if modbus_client is None:
            if self.modbus_client:
                self.modbus_client.close()
            self.actionDisconnect.setEnabled(False)
            self.actionConnect_to.setEnabled(True)
            self.actionStart_reading.setEnabled(False)
            self.actionStop_reading.setEnabled(False)
            self.modbus_client = modbus_client
            # self.statusBar().showMessage("No connection", 0)
            self.statusBar().setStyleSheet("QStatusBar{background:red;color:white}QLabel{color:white}")
            self.statusLabel.setText("No connection")
            # self.connect_btn.setText("Connect")
            if self.has_ever_connected:
                self.note_in_log("Disconnected at " + str(datetime.now()))
        elif self.file_open_mode:
            self.set_file_open_mode(False)
        if isinstance(modbus_client, ModbusSerialClient):
            if modbus_client == self.modbus_client and self.has_ever_connected:
                self.note_in_log("Trying to reconnect at " + str(datetime.now()))
            if modbus_client.connected:
                if isinstance(unit_id, int) and unit_id >= 1:
                    self.unit_id = unit_id
                self.requests_amount = self.valid_responses_amount = 0
                self.modbus_client = modbus_client
                self.statusLabel.setText(RTU)
                texts_for_statusbar = [f"port: {self.modbus_client.params.port}",
                                       f"baudrate: {self.modbus_client.params.baudrate}",
                                       f"stop bits: {self.modbus_client.params.stopbits}",
                                       f"byte size: {self.modbus_client.params.bytesize}",
                                       f"parity: {FULL_PARITY[self.modbus_client.params.parity]}",
                                       f"unit id: {unit_id}"]
                self.statusBar().setStyleSheet("QStatusBar{background:green;color:white}QLabel{color:white}")
                self.actionDisconnect.setEnabled(True)
                self.actionConnect_to.setEnabled(False)
                self.actionStart_reading.setEnabled(not self.reading)
                self.actionStop_reading.setEnabled(self.reading)
                # self.stop_reading_action_triggered()
                if not self.has_ever_connected:
                    self.has_ever_connected = True
                    self.note_in_log("(!) First connection at " + str(datetime.now()))
                else:
                    self.note_in_log("Connected at " + str(datetime.now()))
                self.note_in_log(' | '.join(texts_for_statusbar))
            else:
                self.note_in_log("Unsuccessful connection at " + str(datetime.now()))
        elif isinstance(modbus_client, ModbusClient):
            if modbus_client == self.modbus_client and self.has_ever_connected:
                self.note_in_log("Trying to reconnect at " + str(datetime.now()))
            modbus_client.open()
            if modbus_client.is_open:
                if isinstance(unit_id, int) and unit_id >= 1:
                    self.unit_id = unit_id
                self.requests_amount = self.valid_responses_amount = 0
                self.actionDisconnect.setEnabled(True)
                self.actionConnect_to.setEnabled(False)
                self.actionStart_reading.setEnabled(not self.reading)
                self.actionStop_reading.setEnabled(self.reading)
                # self.stop_reading_action_triggered()
                self.modbus_client = modbus_client
                self.statusLabel.setText(TCP_IP)
                texts_for_statusbar = [f"ip: {self.modbus_client.host}",
                                       f"port: {self.modbus_client.port}",
                                       f"unit id: {unit_id}"]
                self.statusBar().setStyleSheet("QStatusBar{background:green;color:white}QLabel{color:white}")
                if not self.has_ever_connected:
                    self.has_ever_connected = True
                    self.note_in_log("(!) First connection at " + str(datetime.now()))
                else:
                    self.note_in_log("Connected at " + str(datetime.now()))
                self.note_in_log(' | '.join(texts_for_statusbar))
            else:
                self.note_in_log("Unsuccessful connection at " + str(datetime.now()))
        for i in texts_for_statusbar:
            w = QLabel(i, self)
            self.other_statusbar_widgets.append(w)
            self.statusBar().addWidget(w)
        if isinstance(self.modbus_client, ModbusClient):
            return self.modbus_client.is_open
        elif isinstance(self.modbus_client, ModbusSerialClient):
            return self.modbus_client.connected
        else:
            return False

    def read_one_modbus_register(self, register_address, return_if_none=-1):
        """
        Used for easy reading of modbus client's registers and troubleshooting.
        :param register_address: addr or [addr, eval_] or [addr, reg_count] or [addr, bit, val_if_0, val_if_1]
        :param return_if_none: value that will be returned if response is none or invalid.
        :return: register(s)' value or return_if_none
        """
        if not self.modbus_client or not self.reading:
            return return_if_none
        if (isinstance(self.modbus_client, ModbusSerialClient) and not self.modbus_client.connected) or\
                (isinstance(self.modbus_client, ModbusClient) and not self.modbus_client.is_open):
            return return_if_none
        try:
            self.requests_amount += 1
            char, evaluate = None, ''
            if isinstance(register_address, list) or isinstance(register_address, tuple):
                if len(register_address) == 2:
                    if isinstance(register_address[1], int):
                        count = register_address[1]
                        reg = register_address[0]
                    elif isinstance(register_address[1], str):
                        reg = register_address[0]
                        count = 1
                        evaluate = register_address[1]
                else:
                    reg, char, min_, max_ = register_address
                    count = 1
            else:
                count = 1
                reg = register_address
            if isinstance(self.modbus_client, ModbusSerialClient):
                response = self.modbus_client.read_holding_registers(address=reg, slave=self.unit_id,
                                                                     count=count, unit_id=self.unit_id)
                if response.isError():
                    print("Ошибка: " + response.message)
                    self.note_in_log(response.message)
                    self.connect_to(self.modbus_client)
                    return return_if_none
                else:
                    registers = response.registers
            else:
                response = self.modbus_client.read_holding_registers(reg_addr=reg, reg_nb=count)
                if isinstance(response, list) and len(response) >= 1:
                    registers = response
                else:
                    self.connect_to(self.modbus_client)
                    self.note_in_log("Modbus Error: modbus TCP response is None or invalid")
                    print("Ошибка TCP")
                    return return_if_none
            self.valid_responses_amount += 1
            if len(registers) == 1:
                if char is None:
                    val = registers[0]  # eval(str(registers[0]) + evaluate)
                else:
                    decoder = BinaryPayloadDecoder.fromRegisters(registers, Endian.Little)
                    lst = list(reversed(decoder.decode_bits())) + list(reversed(decoder.decode_bits()))
                    value = lst[-1 - char]
                    if not value:
                        return min_
                    else:
                        return max_
                  # ''.join([str(int(i)) for i in list(reversed(decoder.decode_bits())) +
                # list(reversed(decoder.decode_bits()))])
            elif len(registers) < 4:
                decoder = BinaryPayloadDecoder.fromRegisters(registers[: 2], Endian.Big, wordorder=Endian.Little)
                val = decoder.decode_32bit_float()
            elif len(registers) >= 4:
                decoder = BinaryPayloadDecoder.fromRegisters(registers[: 4], Endian.Big, wordorder=Endian.Little)
                val = decoder.decode_64bit_float()
            else:
                return return_if_none
            return eval(str(val) + evaluate)
        except Exception as e:
            pass  # print("an error occurred (read_one_modbus_register):", e)
        return return_if_none

    def autosave(self):
        if self.modbus_client and self.reading:
            self.write_csv(use_dialog=False)
            self.note_in_log(f"Auto save at {datetime.now()}")
            self.reset_plots()

    def reset_plots(self):
        for name, reg_w_p_lcd in self.input_name_to_register_widget_plot_item_LCD.items():
            reg_w_p_lcd[2].setData([], [])
        self.datetime_start = QDateTime.currentDateTime()
        self.start_secs_epoch = self.datetime_start.toSecsSinceEpoch()
        self.start_time = time()

    def write_csv(self, *args, use_dialog=True):
        """
        Creates a file dialog and saves the plot and logs in .csv and .csv.txt extensions
        :param use_dialog: True by default, defines if a file dialog would be used or the path will be chosen automatically
        :return: None
        """
        if use_dialog:
            name = self.file_dialog("Plot file", ".csv", mode="w")
            if not name:
                return
            now = datetime.now()
        else:
            now = datetime.now()
            name = f"./Autosave/Autosave {now}.csv".replace(':', '-')
        # name = plot_file  # "{0}-DIV-{1}.csv".format(self.datetime_start.toPyDateTime(), now).replace(':', '-')
        CSVExporter(item=self.plot_widget.getPlotItem()).export(name)
        self.write_logs(name, now)

    def write_logs(self, name: str, now: datetime):
        with open(name + '.txt', 'w') as f:
            f.write('\n'.join(self.logs))
            f.write('\n' + ';'.join([' '.join(list(map(str, i))) for i in self.colors]))
            f.write('\n' + ';'.join([i.text() for i in self.ai_names_edits]))
            f.write("\n{0}-DIV-{1}".format(self.datetime_start.toPyDateTime(), now))

    def write_xlsx(self):
        """
        Creates a file dialog and saves the plot and logs in .xlsx and .xlsx.txt extensions
        :return: None
        """
        filename = self.file_dialog("Plot file", ".xlsx", mode="w")
        if not filename:
            return
        now = datetime.now()
        d = {}
        # filename = plot_file  # "{0}-DIV-{1}.xlsx".format(self.datetime_start.toPyDateTime(), now).replace(':', '-')
        for name, r_w_pl_lcd in self.input_name_to_register_widget_plot_item_LCD.items():
            d[name + "_x"], d[name + "_y"] = r_w_pl_lcd[2].getData()
        df = xlsxwriter.Workbook(filename)
        sh = df.add_worksheet("plot")
        for col, name in enumerate(d.keys()):
            sh.write(0, col, name)
            values = d[name]
            if not col % 2:
                values = [datetime.fromtimestamp(i).strftime('%d/%m/%y %H:%M:%S.%f') for i in values]
            sh.write_column(1, col, values)
        df.close()
        self.write_logs(filename, now)

    def action_open_from_file_triggered(self):
        """
        The 1st step of the file reading process. The files are opened with a QFileDialog and converted into
        iterable items.
        :return: None
        """
        fd = QFileDialog(self)
        fd.setFileMode(QFileDialog.ExistingFile)
        fd.setNameFilter("Plot file (*.csv)")  #  *.xlsx
        if fd.exec_():
            plot_file = fd.selectedFiles()[0]
        else:
            return
        file_format = plot_file.split('.')[-1]
        fd = QFileDialog(self)
        fd.setFileMode(QFileDialog.ExistingFile)
        fd.setNameFilter(f"Log file (*.{file_format}.txt)")
        if fd.exec_():
            log_file = fd.selectedFiles()[0]
        else:
            return
        self.stop_reading_action_triggered()
        self.connect_to(None)
        self.auto_scale_checkbox.setChecked(False)
        try:
            self.set_file_open_mode(True)
            if plot_file[-3:] == 'csv':
                file = open(plot_file, 'r')
                self.action_open_from_file_triggered_2(log_file, csv.reader(file))
                file.close()
            else:
                self.pb = XlsxFileReadingProgressWindow(self, plot_file, log_file)
                self.pb.show()
        except Exception as e:
            print("error while loading", e)

    def action_open_from_file_triggered_2(self, log_file, reader):  # action_open_from_file step №2
        """
        The 2nd step of the file opening process. It's called after the file was read and prepared for importing into
        the main PlotWidget(). The read plot is put into it.
        :param log_file: filename of the logs file
        :param reader: a list that the plot file was converted into. It must be an iterable item that can be read as a 2d list with names in the 1st row (name_x, name_y) in the 1st row. [ [a_x, a_y, b_x, b_y, etc.], [x, y, x, y, etc.], ... ]
        :return: None
        """
        try:
            with open(log_file, 'r') as log_file_:
                try:
                    log_lines = log_file_.readlines()
                    start_str, stop_str = log_lines[-1].split('-DIV-')
                    self.logs = []
                    self.output_list_widget.clear()
                    self.note_in_log("!! According to the logs, this record had been started at " + start_str)
                    self.note_in_log("!! According to the logs, this record had been stopped at " + stop_str)
                    for i in log_lines[: -3]:
                        self.note_in_log("(!!) FROM OPENED LOGS: " + i)
                    try:
                        self.colors = [list(map(int, i.split())) for i in log_lines[-3].split(';')]
                    except Exception:
                        self.note_in_log("!! Colors are not assigned.")
                    ai_names_texts = log_lines[-2].split(';')
                except Exception:
                    self.note_in_log("(!!) Opened log file is broken")
                    return
            # filename = csv_file.split('/')[-1][: -1 * len('.csv')]
            start_dt, stop_dt = start_stop_dt_from_filename(log_lines[-1])
            h, m, s = start_dt.hour, start_dt.minute, start_dt.second
            time_start = s + 60 * m + 3600 * h
            plots_data, names = {}, []
            for row in reader:
                if not plots_data:
                    names = [i.split('_')[0] for i in row[::2]]
                    plots_data = {name: [[], []] for name in names}
                    self.set_input_checkboxes({name: 0 for name in names},
                                              datetime_start=start_dt, start_time=time_start,
                                              ai_names_texts=ai_names_texts)
                else:
                    for i in range(0, len(names * 2), 2):
                        x, y = list(map(float, row[i: i + 2]))
                        name = names[i // 2]
                        if not plots_data[name][0]:
                            plots_data[name] = [[x], [y]]
                        else:
                            plots_data[name][0].append(x)
                            plots_data[name][1].append(y)
            for name, reg_wid_pl_lcd in self.input_name_to_register_widget_plot_item_LCD.items():
                reg_wid_pl_lcd[2].setData(*plots_data[name])
            # self.make_time_marks(start_dt, stop_dt)
            self.plot_widget.setXRange(start_dt.timestamp(), stop_dt.timestamp())
            self.datetime_start = qdt_from_dt(start_dt)
            self.set_file_open_mode(True)
            # self.timeFromEdit.setTime(start_dt.time())
        except Exception as e:
            print("error while reading plot:", e)

    def language_action(self):
        """
        The handler of language-changing actions in the Languages menu.
        :return: None
        """
        data = LANGUAGES.get(self.sender().text())
        if data is not None:
            if data:
                self.trans.load(data)
                QApplication.instance().installTranslator(self.trans)
            else:
                QApplication.instance().removeTranslator(self.trans)
            # self.retranslateUi()

    def changeEvent(self, a0: QEvent) -> None:
        """
        Standard changeEvent handler but it calls self.retranslateUi if it's a LanguageChange event.
        :param a0: and Event
        :return: None
        """
        if a0.type() == QEvent.LanguageChange:
            self.retranslateUi()
        super(MainWidget, self).changeEvent(a0)

    def closeEvent(self, event) -> None:
        """
        Standard closeEvent handler that also lets you choose if you want to save the file and then closes the modbus
        client.
        :param event: QCloseEvent
        :return: None
        """
        will_close = True
        _translate = QApplication.translate
        s = "If you quit, any unsaved data will be lost! Do you want to save the plot?"
        close = QMessageBox()
        close.setWindowTitle("QUIT")
        close.setWindowIcon(QIcon("ui/icon.ico"))
        close.setText(_translate("MainWidget", s))
        close.addButton(QPushButton("Yes"), QMessageBox.YesRole)
        close.addButton(QPushButton("No"), QMessageBox.YesRole)
        close.addButton(QPushButton("Cancel"), QMessageBox.YesRole)
        ret = close.exec()
        if ret == 0:
            self.write_csv()
            # chs = QMessageBox()
            # chs.setText(_translate("MainWidget", "Choose the extension:"))
            # chs.addButton(QPushButton(".csv"), QMessageBox.YesRole)
            # chs.addButton(QPushButton(".xlsx"), QMessageBox.NoRole)
            # chs.addButton(QPushButton("Cancel"), QMessageBox.RejectRole)
            # ret = chs.exec_()
            # if ret == 0:
            #     self.write_csv()
            # elif ret == 1:
            #     self.write_xlsx()
        elif ret == 2:
            will_close = False
            event.ignore()
        if self.modbus_client and will_close:
            self.modbus_client.close()

    # def resizeEvent(self, a0: QResizeEvent) -> None:
    #     self.groupBox.setFixedHeight(self.plot_widget.geometry().height())

    def set_file_open_mode(self, value):
        self.get_from_dt_field.setEnabled(value)
        self.timeFromEdit.setEnabled(value)
        if value:
            self.give_colors(self.colors)
            self.rangeEdit.setEnabled(True)
            self.timeFromEdit.setTime(self.datetime_start.time())
        else:
            self.rangeEdit.setEnabled(self.auto_scale_checkbox.isChecked())
            if self.file_open_mode:
                self.set_input_checkboxes()
        self.file_open_mode = value

    def retranslateUi(self):
        _translate = QApplication.translate
        self.menuFile.setTitle(_translate("MainWidget", "File"))
        self.actionLoad_settings.setText(_translate("MainWidget", "Load settings"))
        self.menuSave_plot_with_logs.setTitle(_translate("MainWidget", "Save logs and plots"))
        # self.actionxlsx.setText(_translate("MainWidget", "(DON'T CLICK) xlsx"))
        self.actionOpen_from_file.setText(_translate("MainWidget", "Open from file"))
        # self.menuModbus.setTitle(_translate("MainWidget", "Modbus"))
        self.actionConnect_to.setText(_translate("MainWidget", "Connect to"))
        self.actionDisconnect.setText(_translate("MainWidget", "Disconnect"))
        self.actionStart_reading.setText(_translate("MainWidget", "Start reading"))
        self.actionStop_reading.setText(_translate("MainWidget", "Stop reading"))
        self.menuHelp.setTitle(_translate("MainWidget", "Help"))
        self.actionAbout_the_program.setText(_translate("MainWidget", "About the program..."))
        self.menuLanguage.setTitle(_translate("MainWidget", "Language"))
        self.groupBox.setTitle(_translate("MainWidget", "Inputs"))
        self.autoScaleLabel.setText(_translate("MainWidget", "Auto-scroll"))
        self.delayLabel.setText(_translate("MainWidget", "Delay"))
        self.timeRangeLabel.setText(_translate("MainWidget", "View range"))
        self.timeFromLabel.setText(_translate("MainWidget", "Time (from)"))
        self.autoSaveLabel.setText(_translate("MainWidget", "Auto save"))
        self.requests_label.setText(_translate("MainWidget", "Requests:") + " " + str(self.requests_amount))
        self.responses_label.setText(_translate("MainWidget", "Valid responses:") + " " +
                                     str(self.valid_responses_amount))
        self.tabWidget.setTabText(0, _translate("MainWidget", "Plot"))
        self.tabWidget.setTabText(1, _translate("MainWidget", "Current values"))
        self.tabWidget.setTabText(2, _translate("MainWidget", "Image"))
        self.get_from_time_label.setText(_translate("MainWidget", "Get from time:"))


class ConnectForm(QMainWindow):
    def __init__(self, parent, main_widget=None):
        super(ConnectForm, self).__init__(parent)
        self.setWindowIcon(QIcon("ui/icon.ico"))
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.shrink_function)
        self.shrink = False
        self.widget = QWidget()
        self.main_widget = main_widget
        uic.loadUi("ui/connection.ui", self.widget)
        self.setCentralWidget(self.widget)
        self.setWindowTitle(self.widget.windowTitle())
        self.setMinimumSize(self.widget.minimumSize())
        self.setMaximumSize(self.widget.maximumSize())

        self.widget.submit_btn.clicked.connect(self.submit)

        self.tcp_fields = [self.widget.ip_field, self.widget.ip_port_field, self.widget.unitId_tcp_field]
        self.rtu_fields = [self.widget.com_field, self.widget.baudrate_field, self.widget.stopbits_field,
                           self.widget.databits_field, self.widget.parity_field, self.widget.unitId_field]

        self.widget.protocol_field.addItems(["---", TCP_IP, RTU])
        self.widget.protocol_field.currentTextChanged.connect(self.protocol_changed)
        self.protocol = self.protocol_changed(self.widget.protocol_field.currentText())
        self.widget.ip_field.setText(TCP_IP_settings.get("ip"))
        self.widget.ip_port_field.setText(str(TCP_IP_settings.get("ip_port")))

        self.update_ports()
        self.widget.update_ports_btn.clicked.connect(self.update_ports)
        self.widget.baudrate_field.setCurrentText(str(RTU_settings.get("baudrate")))
        self.widget.stopbits_field.setCurrentText(str(RTU_settings.get("stopbits")))
        self.widget.databits_field.setCurrentText(str(RTU_settings.get("bytesize")))
        self.widget.parity_field.setCurrentText(str(RTU_settings.get("parity")))

    def update_ports(self):
        self.widget.com_field.clear()
        available_ports = [str(i).split()[0] for i in serial.tools.list_ports.comports()]
        self.widget.com_field.addItems(available_ports)
        port_from_settings = RTU_settings.get("COM")
        if port_from_settings is not None and port_from_settings not in available_ports:
            msb = QMessageBox()
            msb.setWindowTitle("COM-port connection")
            msb.setText("Port {0} is NOT available at the moment!".format(RTU_settings.get("COM")))
            msb.exec()
        else:
            self.widget.com_field.setCurrentText(RTU_settings.get("COM"))

    def submit(self):
        unit_id = None
        if self.protocol == RTU:
            client = ModbusSerialClient(baudrate=int(self.widget.baudrate_field.currentText()),
                                        stopbits=int(self.widget.stopbits_field.currentText()),
                                        bytesize=int(self.widget.databits_field.currentText()),
                                        parity=self.widget.parity_field.currentText()[0],
                                        port=self.widget.com_field.currentText())
            unit_id = self.widget.unitId_field.value()
        elif self.protocol == TCP_IP:
            errors = []
            if not validate_ip_address(self.widget.ip_field.text()):
                errors.append("● IP address is not valid (follow the pattern 255.255.255.255)")
            if not self.widget.ip_port_field.text().isdigit():
                errors.append("● IP port is not valid (it must be a number)")
            if errors:
                msbox = QMessageBox()
                msbox.setWindowTitle("Field validation")
                msbox.setText('\n'.join(errors))
                msbox.setStandardButtons(QMessageBox.Ok)
                msbox.exec()
                return
            unit_id = self.widget.unitId_tcp_field.value()
            client = ModbusClient(host=self.widget.ip_field.text(), port=int(self.widget.ip_port_field.text()),
                                  auto_open=True, unit_id=unit_id)
        else:
            return
        if self.main_widget.connect_to(client, unit_id=unit_id):
            self.setMinimumHeight(0)
            self.timer.start()

    def shrink_function(self):
        if self.geometry().height() > 0:
            self.setGeometry(self.geometry().left(), self.geometry().top(), self.geometry().width(),
                             self.geometry().height() - 10)
        else:
            self.close()

    def protocol_changed(self, text):
        for i in self.tcp_fields:
            i.setEnabled(text == TCP_IP)
        for i in self.rtu_fields:
            i.setEnabled(text == RTU)
        self.protocol = text
        return text


class HelpWindow(QMainWindow):
    def __init__(self, parent):
        super(HelpWindow, self).__init__(parent)
        self.setWindowIcon(QIcon("ui/icon.ico"))
        uic.loadUi("ui/help.ui", self)
        self.trans = parent.trans
        with open("manual.txt", 'r', encoding="UTF-8") as f:
            self.pt = f.read()[1:]
        self.retranslateUi()

    def retranslateUi(self):
        _translate = QApplication.translate
        self.plainTextEdit.setPlainText(_translate("MainWidget", self.pt))


class AboutWindow(QMainWindow):
    def __init__(self, parent):
        super(AboutWindow, self).__init__(parent)
        self.setWindowIcon(QIcon("ui/icon.ico"))
        uic.loadUi("ui/about.ui", self)


class XlsxFileReadingProgressWindow(QMainWindow):
    def __init__(self, main_widget: MainWidget, filename, log_file):
        super().__init__()
        self.setWindowIcon(QIcon("ui/icon.ico"))
        self.main_widget = main_widget
        self.log_file = log_file  # needed for step 2 of file opening
        self.setWindowTitle("Loading")
        self.pb = QProgressBar(self)
        self.setFixedSize(400, 30)
        self.pb.setFixedSize(200, 30)
        self.rem_tim = QLabel(self)
        self.rem_tim.setGeometry(200, 0, 200, 30)
        self.file = openpyxl.load_workbook(filename, read_only=True)
        QTimer.singleShot(1, self.read_)

    def read_(self):
        trans = self.main_widget.trans
        rt = QApplication.translate("MainWidget", "Remaining time")
        sheet_obj, reader, row = self.file.active, [], 1
        self.pb.setRange(1, sheet_obj.max_row)
        pt = time()
        try:
            for i in range(1, sheet_obj.max_row + 1):
                self.update()
                QApplication.processEvents()
                reader.append([])
                for j in range(1, sheet_obj.max_column + 1):
                    value = sheet_obj.cell(i, j).value
                    if i == 1:
                        reader[-1].append(str(value))
                    else:
                        reader[-1].append(float(value))
                time_on_last_row = time() - pt
                s = time_on_last_row * (sheet_obj.max_row - i)
                h, m, s = str(round((s // 3600) % 24)), str(round((s // 60) % 60)), str(round(s) % 60)
                h, m, s = make_2_dgs(h), make_2_dgs(m), make_2_dgs(s)
                self.rem_tim.setText(rt + " " + h + ":" + m + ":" + s)
                pt = time()
                self.pb.setValue(i)
            self.main_widget.action_open_from_file_triggered_2(self.log_file, reader)
        except Exception:
            pass
        finally:
            self.close()

    def closeEvent(self, a0) -> None:
        self.file.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWidget()
    ex.show()
    sys.exit(app.exec())
