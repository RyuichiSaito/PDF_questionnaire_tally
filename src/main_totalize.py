import imp
import os
import sys

from PyQt5.QtWidgets import QWidget, QToolTip, QApplication, QGridLayout
from PyQt5.QtGui import QCloseEvent, QDoubleValidator, QFont, QIcon, QKeySequence, QPixmap, QTextCursor
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from file_existence_check import FileExistanceCHK
from edit_csv import Create_CSV
from edit_csv_web import Create_CSV_WEB

# exe file 後のエラー回避
import ctypes
import _winapi

ctypes.windll.kernel32.SetStdHandle(_winapi.STD_INPUT_HANDLE, 0)

LOCATION_NUM = 440 # 440

class Stream(QObject):
    message = pyqtSignal(str)

    def write(self, message):
        self.message.emit(str(message))

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle('CSV Totalize')
        self.setGeometry(100, 100, 600, 700)

        self.fname = None
        self.csvpath = None
        self.dtype = 'csv'

        self.initUI()

        sys.stdout = Stream(message = self.on_udate_text)
        self.show()

    def initUI(self):
        grid = QGridLayout()
        grid.setSpacing(15)

        text1 = QLabel('summary.csvを選択してください')

        btn1 = QPushButton('ファイル選択')
        btn1.clicked.connect(self.open_file_dialog)
        self.textbox1 = QLineEdit()
        
        btn2 = QPushButton('OK')
        btn2.clicked.connect(self.dir_check)

        self.btn3 = QPushButton('実行')
        self.btn3.setVisible(False)
        self.btn3.clicked.connect(self.exec_main)

        self.btn4 = QPushButton('Clear Log')
        self.btn4.clicked.connect(self.clear_text)

        self.city_table = QComboBox()
        citys = ['地域を選択','あきつ','西条A','西条B','黒瀬A','黒瀬B','八本松A','八本松B','志和A','志和B','福富A','福富B','豊栄A','豊栄B','河内A','河内B','高屋A','高屋B']
        self.city_table.addItems(citys)
        self.city_table.setVisible(False)

        self.process = QTextEdit()
        self.process.setLineWrapMode(QTextEdit.NoWrap)

        grid.addWidget(text1, 0, 0)
        grid.addWidget(self.textbox1, 1, 0, 1, 2)
        grid.addWidget(btn1, 1, 2)
        grid.addWidget(btn2, 2, 2)
        grid.addWidget(self.btn3, 3, 2)
        grid.addWidget(self.btn4, 3, 0)
        grid.addWidget(self.city_table, 3, 1)
        grid.setRowStretch(4, 1)
        grid.addWidget(self.process, 4, 0, 5, 3)

        self.setLayout(grid)

    def open_file_dialog(self):
        """
        CSVファイル, Excelファイルを選択する
        """
        # 初期化
        self.btn3.setVisible(False)
        self.city_table.setVisible(False)

        self.csvpath = QFileDialog.getOpenFileName(self, 'ファイルを開く', '', 'CSV, Excelファイル (*.csv *xlsx)')[0]
        #self.fname = QFileDialog.getExistingDirectory(self, 'Open file')
        self.textbox1.setText(self.csvpath)
        self.fname = os.path.dirname(self.csvpath)
        print(self.fname)

    def clear_text(self):
        self.process.clear()

    def dir_check(self):
        """
        選択したディレクトリにファイルが存在するか確認
        存在しないしない場合はエラーメッセージを表示
        PDFのみ存在する場合別ウインドウを開く
        """

        if self.fname == None: # フォルダが選択されていない場合
            return

        root, ext = os.path.splitext(self.csvpath)
        Filechk = FileExistanceCHK(self.fname)
        if ext == '.xlsx':
            self.csv_totalize_web = Create_CSV_WEB(self.csvpath)
            flag = self.csv_totalize_web.check_excelfile()
            if flag == 4:
                self.btn3.setVisible(True)
                self.city_table.setVisible(True)
                self.dtype = 'xlsx'
                print('Web Data : OK!')

        elif Filechk.chk_flag != 3:
            QMessageBox.warning(None, "警告", "ファイルが存在しません", QMessageBox.Ok)

        elif Filechk.chk_flag == 3:
            self.dtype = 'csv'
            self.btn3.setVisible(True)
            print('Paper Data : OK!')


    def exec_main(self):
        if self.dtype == 'csv':
            csv_totalize = Create_CSV(self.fname)
            csv_totalize.main_process()
        else:
            city = self.city_table.currentText()
            if city == '地域を選択':
                QMessageBox.warning(None, "警告", "地域を選択してください", QMessageBox.Ok)
                return
            self.csv_totalize_web.main_process(city)

    def on_udate_text(self, text):
        cursor = self.process.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.process.setTextCursor(cursor)
        self.process.ensureCursorVisible()

    def closeEvent(self, event):
        sys.stdout = sys.__stdout__
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())