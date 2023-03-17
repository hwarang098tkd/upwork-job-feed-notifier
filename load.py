from PyQt5 import uic
from PyQt5.QtCore import QTimer, QTime, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QListWidgetItem, QHeaderView
from main import parse_and_store
import sys
import os
import logging
from datetime import datetime

#--------- Variable --------
data = {}
logging.basicConfig(filename='upwork_rss.log', level=logging.INFO)  # Set up logging


def logging_info(message, current_datetime):
    logging.info(f"{message} - {current_datetime}")

# Create a custom QThread to run parsing in a separate thread
class ParseThread(QThread):
    dataReady = pyqtSignal(dict) # signal to emit when data is ready

    def __init__(self, audio_cb=True, brow_cb=True):
        super().__init__()
        self.audio_cb = audio_cb
        self.brow_cb = brow_cb

    def run(self):
        print("ParseThread: started")
        data = parse_and_store(self.audio_cb, self.brow_cb)
        self.dataReady.emit(data)  # emit dataReady signal when data is parsed


class Login(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('mainUI.ui', self)
        # Initialize QTimer instance to handle timed updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)  # update every second
        self.next_run = QTime.currentTime().addSecs(10)  # 10 seconds from now
        self.parse_thread = ParseThread()
        self.parse_thread.dataReady.connect(
            self.on_parse_finished)  # connect on_parse_finished method to dataReady signal
        self.ui.power_btn.clicked.connect(
            self.toggle_timer)  # connect toggle_timer method to power_btn's clicked signal
        self.ui.run_now_btn.clicked.connect(self.run_now)  # connect run_now method to run_now_btn's clicked signal

        # Connect doubleClicked signal to slot
        self.ui.data_tv.doubleClicked.connect(self.on_table_row_double_clicked)

        # -------- Settings --------
        self.ui.settings_btn.clicked.connect(self.open_settings_config)
        self.ui.settings_btn.setText("")
        self.ui.settings_btn.setIcon(QIcon("assets/icons/gear.png"))
        # -------- Log --------
        self.ui.log_btn.clicked.connect(self.open_log_file)
        self.ui.log_btn.setText("")
        self.ui.log_btn.setIcon(QIcon("assets/icons/log.png"))

        self.show()

    def on_table_row_double_clicked(self, index):
        global data
        # Get the row number from the index
        row = index.row()
        print(row)

    def open_settings_config(self):
        log_file_path = os.path.join(os.path.dirname(__file__), "settings.json")
        os.startfile(log_file_path)

    def open_log_file(self):
        log_file_path = os.path.join(os.path.dirname(__file__), "upwork_rss.log")
        os.startfile(log_file_path)

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.timeout.disconnect()  # disconnect the timeout signal
            self.remaining_time = QTime.currentTime().secsTo(self.next_run)
            self.timer.stop()
            self.ui.timer_lb.setStyleSheet("color: red")  # set text color to red when stopped
        else:
            self.next_run = QTime.currentTime().addSecs(self.remaining_time)
            self.timer.timeout.connect(self.update_timer)  # reconnect the timeout signal
            self.timer.start(1000)
            self.ui.timer_lb.setStyleSheet("color: rgb(138, 138, 138)")

    def run_now(self):
        print("Login: run_now")
        if not self.timer.isActive():
            self.timer.stop()
        self.timer.start(1000)  # update every second
        self.parse_and_store()
        self.ui.timer_lb.setStyleSheet("color: green")
        self.ui.timer_lb.setText("Running...")
        self.next_run = QTime.currentTime().addSecs(300)

    def parse_and_store(self):
        print("Login: parse_and_store")

        if self.parse_thread.isRunning():
            self.parse_thread.quit()  # stop the thread if it's running
        # get the values of the checkboxes
        self.parse_thread.audio_cb = self.ui.audio_cb.isChecked()
        self.parse_thread.brow_cb = self.ui.brow_cb.isChecked()

        self.parse_thread.start()

    def on_parse_finished(self, data):
        print("Login: on_parse_finished")
        self.next_run = QTime.currentTime().addSecs(300)  # 5 minutes from now
        if "Error" in data:
            self.info_label(data["Error"], "red")
        else:
            self.info_label("Jobs Found: " + str(len(data.keys())), "Green")
            # create a QStandardItemModel and set it as the model for the QTableView
            model = QStandardItemModel(self.ui.data_tv)
            model.setHorizontalHeaderLabels(["Title", "Date Published"])
            self.ui.data_tv.setModel(model)

            # set up column stretch
            header = self.ui.data_tv.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

            for title, info in data.items():
                link, date_published = info[0], info[1]
                formatted_date = date_published.strftime("%d/%m/%Y %H:%M")
                model.insertRow(model.rowCount())
                model.setData(model.index(model.rowCount() - 1, 0), title)
                model.setData(model.index(model.rowCount() - 1, 1), formatted_date)

    def update_timer(self):
        # print("Login: update_timer")
        current_time = QTime.currentTime()
        remaining_time = current_time.secsTo(self.next_run)
        if remaining_time > 0:
            minutes, seconds = divmod(remaining_time, 60)
            self.ui.timer_lb.setStyleSheet("color: rgb(138, 138, 138)")
            time_str = f"{minutes} min {seconds} sec"
        else:
            self.ui.timer_lb.setStyleSheet("color: green")
            time_str = "Running..."
            self.parse_and_store()

        self.ui.timer_lb.setText(time_str)

    def info_label(self, message, color):
        self.ui.error_lb.setStyleSheet("color:" + color)
        self.ui.error_lb.setText(message)

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        login_window = Login()
        login_window.setWindowTitle("Upwork Rss feed")
        # set the window icon
        icon = QIcon("assets/icons/rss.png")
        login_window.setWindowIcon(icon)
        sys.exit(app.exec())
    except(Exception):
        logging_info(Exception,str(datetime.now()))

