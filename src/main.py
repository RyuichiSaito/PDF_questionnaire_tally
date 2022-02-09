import sys
import os

from PyQt5.QtWidgets import QWidget, QToolTip, QApplication, QGridLayout
from PyQt5.QtGui import QCloseEvent, QDoubleValidator, QFont, QIcon, QKeySequence
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import pandas as pd
import configparser
import cv2

from file_existence_check import FileExistanceCHK
from OCR_process import *

# exe file 後のエラー回避
import ctypes
import _winapi

ctypes.windll.kernel32.SetStdHandle(_winapi.STD_INPUT_HANDLE, 0)

"""
setup window 
select file and load data 
"""
class SubWindow(QWidget):
    def __init__(self, parent=None):
        super(SubWindow, self).__init__(parent)
        self.setWindowTitle('Select Directory')
        self.setGeometry(300, 300, 400, 200)

        self.fname = None

        self.initUI()
        self.show()

    def initUI(self):
        grid = QGridLayout()
        grid.setSpacing(15)

        text1 = QLabel(' フォルダを選択してください')

        btn1 = QPushButton('フォルダ選択')
        btn1.clicked.connect(self.open_file_dialog)
        self.textbox1 = QLineEdit()
        
        btn2 = QPushButton('OK')
        btn2.clicked.connect(self.run_main)

        self.btn3 = QPushButton('OCR')
        self.btn3.clicked.connect(self.run_OCR)
        self.btn3.setVisible(False)
        self.btn4 = QPushButton('CSV編集')
        self.btn4.clicked.connect(self.run_CSV)
        self.btn4.setVisible(False)

        grid.addWidget(text1, 0, 0)
        grid.addWidget(self.textbox1, 1, 0, 1, 2)
        grid.addWidget(btn1, 1, 2)
        grid.addWidget(btn2, 2, 2)
        grid.addWidget(self.btn3, 3, 0)
        grid.addWidget(self.btn4, 3, 1)
        grid.addWidget(QLabel(' '), 3, 2)
        grid.setRowStretch(4, 1)

        self.setLayout(grid)

    def open_file_dialog(self):
        self.fname = QFileDialog.getExistingDirectory(self, 'Open file')
        self.textbox1.setText(self.fname)
        print(self.fname)

    def run_main(self):
        """
        選択したディレクトリにファイルが存在するか確認
        存在しないしない場合はエラーメッセージを表示
        PDFのみ存在する場合別ウインドウを開く
        """
        if self.fname == None: # フォルダが選択されていない場合
            return

        Filechk = FileExistanceCHK(self.fname)
        print(Filechk.chk_flag)
        if Filechk.chk_flag == 0:
            QMessageBox.warning(None, "警告", "ファイルが存在しません", QMessageBox.Ok)

        elif Filechk.chk_flag == 1:
            self.pdf_files = Filechk.pdffiles
            print('PDF only')
            self.btn3.setVisible(True)
            self.ocr_window = OCRWindow(self.pdf_files)
            self.close()            

        elif Filechk.chk_flag == 2 or Filechk.chk_flag == 3:
            print('PDF + CSV')
            self.pdf_files = Filechk.pdffiles
            self.csv_files = Filechk.csvfiles

            self.btn3.setVisible(True)
            self.btn4.setVisible(True)
            """
            msgBox = QMessageBox()
            msgBox.setWindowTitle("確認")
            msgBox.setText("CSVファイルが存在します．再度OCRを行いますか？")
            msgBox.setInformativeText("再度OCRを行う場合は「いいえ」を選択してください")
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            msgBox.setDefaultButton(QMessageBox.Yes)
            res = msgBox.exec_()
            
            print(msgBox)
            if res == QMessageBox.No:
                self.ocr_window = OCRWindow(self.pdf_files)
            elif res == QMessageBox.Yes:
                self.mainwindow = MainWindow(self.fname, self.pdf_files, self.csv_files)
                self.mainwindow.show()
                self.close()
            else:
                pass
            """
            
    def run_OCR(self):
        print('ocr')
        self.ocr_window = OCRWindow(self.pdf_files)
        self.ocr_window.show()

    def run_CSV(self):
        self.mainwindow = MainWindow(self.fname, self.pdf_files, self.csv_files)
        self.mainwindow.show()
        self.close()

"""
#TODO : 事前に画像を読み込んでおく (前後2,3枚)
"""
class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        self.fn()



"""
main window calss

TODO add tab2,3 functions 

"""
class MainWindow(QWidget):
    def __init__(self, fname, pdf_files, csv_files ,parent=None):
        super(MainWindow, self).__init__(parent)

        self.fname = fname
        self.pdf_files = pdf_files
        self.csv_files = csv_files
        self.df_summary = pd.read_csv(self.fname + '/summary.csv', encoding="shift-jis")
        self.df_summary.replace(np.nan, '', inplace=True)

        self.width = 0
        self.height = 0
        self.csv_counter = 0
        self.img3_rotateang = 0
        # fig3
        self.click_xdata = None
        self.click_ydata = None
        self.release_xdata = None
        self.release_ydata = None
        self.fig3_range = None

        self.read_config()

        self.setWindowTitle('Main Window')
        self.setGeometry(100, 100, 800, 800)
        self.initUI()
        QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True) 
        self.image_show()
        self.show()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab1 = QWidget()   
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tabs.resize(600,500)

        # Add tabs
        self.tabs.addTab(self.tab1, "表面1")
        self.tabs.addTab(self.tab2, "表面2")
        self.tabs.addTab(self.tab3, "裏面")

        # Create tabs
        self.initUI_tab1()
        self.initUI_tab2()
        self.initUI_tab3()

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def initUI_tab1(self):
        self.tab1.layout = QVBoxLayout(self)

        # ----------------
        # Create Widgets
        # ----------------
        grid = QGridLayout()

        # button
        self.btn_reset = QPushButton('Reload')
        self.btn_save = QPushButton('Save(Ctrl+S)')
        self.btn_next = QPushButton('Next')
        self.btn_back = QPushButton('Back')
        self.btn_reset.clicked.connect(self.image_show)
        self.btn_save.clicked.connect(self.save_csv)
        self.btn_next.clicked.connect(self.move_next)
        self.btn_back.clicked.connect(self.move_back)

        # Figureを作成
        plt.rcParams["font.size"] = 6 #フォントサイズ
        plt.rcParams["figure.figsize"] = (8, 16) # グラフサイズ
        self.Figure = plt.figure()
        self.FigureCanvas = FigureCanvas(self.Figure)
        self.axis = self.Figure.add_subplot(1,1,1)

        self.FigureCanvas.mpl_connect('button_press_event', self.onclick)

        # set shortcut key
        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(self.save_csv)

        # set label location
        grid.addWidget(self.FigureCanvas, 0, 0, 6, 3)
        grid.addWidget(self.btn_reset, 4, 5, 1, 1)
        grid.addWidget(self.btn_save, 5, 5, 1, 1)
        grid.addWidget(self.btn_back, 6, 4, 1, 1)
        grid.addWidget(self.btn_next, 6, 5, 1, 1)

        self.tab1.setLayout(grid)

    def initUI_tab2(self):
        self.tab2.layout = QVBoxLayout(self)

        # ----------------
        # Create Widgets
        # ----------------
        grid = QGridLayout()

        # button
        self.btn_reset = QPushButton('Reload')
        self.btn_save = QPushButton('Save')
        self.btn_next = QPushButton('Next')
        self.btn_back = QPushButton('Back')
        self.btn_reset.clicked.connect(self.image_show)
        self.btn_save.clicked.connect(self.save_csv)
        self.btn_next.clicked.connect(self.move_next)
        self.btn_back.clicked.connect(self.move_back)

        # Figureを作成
        plt.rcParams["font.size"] = 6 #フォントサイズ
        plt.rcParams["figure.figsize"] = (4, 16) # グラフサイズ
        self.Figure2 = plt.figure()
        self.FigureCanvas2 = FigureCanvas(self.Figure2)
        self.axis2 = self.Figure2.add_subplot(1,1,1)

        # set shortcut key
        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(self.save_csv)

        # table
        self.table2 = QTableWidget()
        self.table2.setRowCount(self.DATANUM)
        self.table2.setColumnCount(2)
        self.table2.setHorizontalHeaderLabels(["コメント","自由記述欄"])
        self.table2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table2.cellClicked.connect(self.table2_click)
        self.table2.cellActivated.connect(self.table2_click)

        #self.FigureCanvas2.mpl_connect('button_press_event', self.onclick)
        # set label location
        splitter1 = QSplitter(Qt.Horizontal) #横向きにStackする
        splitter1.addWidget(self.FigureCanvas2)
        splitter1.addWidget(self.table2)

        #grid.addWidget(self.FigureCanvas2, 0, 0, 6, 2)
        #grid.addWidget(self.table2, 0, 2, 6, 3)
        grid.addWidget(splitter1, 0, 0, 6, 5)
        grid.addWidget(self.btn_reset, 4, 6, 1, 1)
        grid.addWidget(self.btn_save, 5, 6, 1, 1)
        grid.addWidget(self.btn_back, 6, 5, 1, 1)
        grid.addWidget(self.btn_next, 6, 6, 1, 1)

        self.tab2.setLayout(grid)

    def initUI_tab3(self):
        self.tab3.layout = QVBoxLayout(self)
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        # ----------------
        # Create Widgets
        # ----------------
        grid = QGridLayout()

        # button
        self.btn_reset = QPushButton('Reset')
        self.btn_save = QPushButton('Save(Ctrl+S)')
        self.btn_next = QPushButton('Next')
        self.btn_back = QPushButton('Back')
        self.btn_rotate_l = QPushButton('L Rotete')
        self.btn_rotate_r = QPushButton('R Rotete')
        self.btn_cutimg = QPushButton('Cut image')


        self.btn_reset.clicked.connect(self.reset_image3)
        self.btn_save.clicked.connect(self.save_csv)
        self.btn_next.clicked.connect(self.move_next)
        self.btn_back.clicked.connect(self.move_back)
        self.btn_rotate_l.clicked.connect(self.rotate_l)
        self.btn_rotate_r.clicked.connect(self.rotate_r)
        self.btn_cutimg.clicked.connect(self.cutoff_img)

        # table
        self.table3 = QTableWidget()
        self.table3.setRowCount(12)
        self.table3.setColumnCount(1)
        self.table3.setHorizontalHeaderLabels(["Data"])
        
        self.chk_table = QComboBox()
        citys = ['','あきつ','西条A','西条B','黒瀬A','黒瀬B','八本松A','八本松B','志和A','志和B','福富A','福富B','豊栄A','豊栄B','河内A','河内B','高屋A','高屋B']
        self.chk_table.addItems(citys)
        self.table3.setCellWidget(11, 0, self.chk_table)

        # set shortcut key
        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(self.save_csv)

        # Figureを作成
        plt.rcParams["font.size"] = 6 #フォントサイズ
        plt.rcParams["figure.figsize"] = (8, 16) # グラフサイズ
        self.Figure3 = plt.figure()
        self.FigureCanvas3 = FigureCanvas(self.Figure3)
        self.axis3 = self.Figure3.add_subplot(1,1,1)

        self.FigureCanvas3.mpl_connect('button_press_event', self.onclick_fig3)
        self.FigureCanvas3.mpl_connect('button_release_event', self.onrelease_fig3)
        # set label location
        splitter1 = QSplitter(Qt.Horizontal) #横向きにStackする
        splitter1.addWidget(self.FigureCanvas3)
        splitter1.addWidget(self.table3)

        
        grid.addWidget(splitter1, 0, 0, 5, 6)
        #grid.addWidget(self.FigureCanvas3, 0, 0, 6, 3)
        grid.addWidget(self.btn_rotate_l, 6, 4, 1, 1)
        grid.addWidget(self.btn_rotate_r, 6, 5, 1, 1)
        grid.addWidget(self.btn_cutimg, 7, 4, 1, 1)
        grid.addWidget(self.btn_reset, 7, 5, 1, 1)
        grid.addWidget(self.btn_save, 8, 5, 1, 1)
        grid.addWidget(self.btn_back, 9, 4, 1, 1)
        grid.addWidget(self.btn_next, 9, 5, 1, 1)
        #grid.addWidget(self.chk_table, 5, 4, 1, 2)
        #grid.addWidget(self.table3, 0, 4, 5, 3)

        self.tab3.setLayout(grid)

    def spinbox0_changed(self):
        self.slider0.setValue(self.spinbox0.value())
        #self.update_plot()

    def spinbox1_changed(self):
        self.slider1.setValue(self.spinbox1.value())
        #self.update_plot()
    
    def slider0_changed(self):
        self.spinbox0.setValue(self.slider0.value())
        #self.update_plot()

    def slider1_changed(self):
        self.spinbox1.setValue(self.slider1.value())
        #self.update_plot()

    def read_config(self):
        config_fname = self.fname + '/' + 'config.ini'
        if os.path.exists(config_fname):
            config = configparser.ConfigParser()
            config.read(config_fname, 'UTF-8')
    
            self.xp1 = int(config['DEFAULT']['XP1'])
            self.yp1 = int(config['DEFAULT']['YP1'])
            self.xp2 = int(config['DEFAULT']['XP2'])
            self.yp2 = int(config['DEFAULT']['YP2'])
            self.xp3 = int(config['DEFAULT']['XP3'])
            self.yp3 = int(config['DEFAULT']['YP3'])

            self.W_RATIO = float(config['DEFAULT']['W_RATIO']) * 0.2
            self.H_RATIO = float(config['DEFAULT']['H_RATIO']) * 0.2

            self.DATANUM = int(config['DEFAULT']['DATANUM'])

    def reset_image3(self):
        self.click_xdata = None
        self.click_ydata = None
        self.release_xdata = None
        self.release_ydata = None
        self.fig3_range = None
        self.image_show()

    def image_show(self):
        self.get_csv_data(self.csv_counter)
        
        self.cur_img, self.cur_img2, self.cur_img3 = self.get_image(self.csv_counter)
        # img3 preprocess
        self.cur_img3 = self.rotate_img(self.cur_img3)
        if self.fig3_range != None:
            self.cur_img3 = self.cur_img3[self.fig3_range[2]:self.fig3_range[3], self.fig3_range[0]:self.fig3_range[1]]

        self.cur_fname = self.csv_files[self.csv_counter]
        self.cur_df = pd.read_csv(self.cur_fname, index_col=0, encoding="shift-jis")
        self.cur_df.fillna("", inplace=True)

        idx = self.df_summary[self.df_summary['PDF name'] == self.curpdf].index.tolist()[0]
        location_txt = self.df_summary.iloc[idx,-1]
        #print(location_txt)
        self.chk_table.setCurrentText(location_txt)

        self.table2_data_add()
        # reset figure
        self.axis.cla()
        self.axis.imshow(self.cur_img)
        self.axis2.cla()
        self.axis2.imshow(self.cur_img2)
        self.axis3.cla()
        self.axis3.imshow(self.cur_img3)

        # tab1 plots
        DATANUM, YOKO_NUM = self.cur_df.shape
        YOKO_NUM -= 2
        self.TATE = [int(self.cur_img.shape[0]/DATANUM*i) for i in range(DATANUM+1)] # データの行数
        self.YOKO = [int(self.cur_img.shape[1]/YOKO_NUM*i) for i in range(YOKO_NUM+1)] # データの列数
        self.width = self.YOKO[1] - self.YOKO[0]
        self.height = self.TATE[1] - self.TATE[0]

        for i in range(DATANUM):
            for j in range(YOKO_NUM):
                if self.cur_df.iloc[i,j]:
                    rectangle = patches.Rectangle(xy=(self.YOKO[j],self.TATE[i]) , width=self.width, height=self.height, alpha = 0.4)
                    self.axis.add_patch(rectangle)

        # 
        self.axis.set_axis_off()
        self.axis2.set_axis_off()
        self.axis3.set_axis_off()
        self.Figure.tight_layout()
        self.Figure2.tight_layout()
        self.Figure3.tight_layout()
        # draw canvas
        self.FigureCanvas.draw()
        self.FigureCanvas2.draw()
        self.FigureCanvas3.draw()
        
    def get_image(self, i):
        """
        PDFファイルから処理した画像を取得
        FIXME ボトルネックネックとなっている．
        """
        curpdf = self.pdf_files[i]
        OcrProcess = ImageProcess(self.pdf_files)
        img, img2, img3 = OcrProcess.main_process(curpdf, self.xp1, self.yp1, self.xp2, self.yp2, self.xp3, self.yp3, ocr_flag=False)
        #img_resize = cv2.resize(img, (int(img.shape[1]*self.H_RATIO), int(img.shape[0]*self.W_RATIO)))
        return img, img2, img3

    def table2_data_add(self):
        for i in range(self.DATANUM):
            text1 = self.cur_df.iloc[i,8]
            text2 = self.cur_df.iloc[i,9]
            self.table2.setItem(i, 0, QTableWidgetItem(str(text1)))
            self.table2.setItem(i, 1, QTableWidgetItem(str(text2)))

    def table2_click(self):
        row = self.table2.currentRow()
        self.axis2.patches.clear()
        rectangle_tab2 = patches.Rectangle(xy=(0,self.TATE[row]) , width=self.cur_img2.shape[1], height=self.height, alpha = 0.3, color='red')
        self.axis2.add_patch(rectangle_tab2)
        self.FigureCanvas2.draw()

    def get_csv_data(self, i):
        self.curpdf = os.path.basename(self.pdf_files[i])
        cur_df = self.df_summary[self.df_summary['PDF name'] == self.curpdf].iloc[:,2:]

        for i in range(11):
            self.table3.setItem(i, 0, QTableWidgetItem(str(cur_df.iloc[0,i])))
        self.table3.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table3.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table3.setVerticalHeaderLabels(cur_df.columns.values.tolist())

    def save_table2_changed(self):
        cur_items1 = [self.table2.item(row, 0).text() for row in range(self.DATANUM)]
        cur_items2 = [self.table2.item(row, 1).text() for row in range(self.DATANUM)]
        self.cur_df.iloc[:,8] = cur_items1
        self.cur_df.iloc[:,9] = cur_items2

    def save_table3_changed(self):
        items = self.chk_table.currentText()
        cur_items = [self.table3.item(row, 0).text() for row in range(11)]
        cur_items.append(items)
        idx = self.df_summary[self.df_summary['PDF name'] == self.curpdf].index.tolist()[0]
        self.df_summary.iloc[idx,2:] = cur_items
        self.df_summary.to_csv(self.fname + '/' + 'summary.csv', index=False, encoding="shift-jis")

    def onclick(self, event):
        """
        マウスをクリックした座標を取得
        """
        if event.button == 1: # MouseButton.LEFT:
            if event.xdata == None or event.ydata == None:
                return
            xdata = int(event.xdata)
            ydata = int(event.ydata)
            i = ydata//self.height
            j = xdata//self.width

            self.change_plot(i, j)
            #print('xdata = ' + str(event.xdata))
            #print('ydata = ' + str(event.ydata))
            #print(i,j)

    def onclick_fig3(self, event):
        """
        get mouse clicked loctation of tab3
        """
        if event.button == 1:
            if event.xdata == None or event.ydata == None:
                return
            self.click_xdata = int(event.xdata)
            self.click_ydata = int(event.ydata)

            self.axis3.cla()
            self.axis3.imshow(self.cur_img3)

    def onrelease_fig3(self, event):
        """
        get mouse released loctation of tab3
        """
        if event.button == 1:
            if event.xdata == None or event.ydata == None:
                return
            self.release_xdata = int(event.xdata)
            self.release_ydata = int(event.ydata)

            ## update figure
            bx = [self.release_xdata,  self.click_xdata]
            by = [self.release_ydata,  self.click_ydata]

            bx.sort()
            by.sort()
            rect = [bx[0], by[0], bx[1]-bx[0], by[1]-by[0]]
            self.fig3_range = [*bx, *by]
            rectangle = patches.Rectangle(xy=(rect[0],rect[1]) , width=rect[2], height=rect[3], color='red', linewidth='2',fill=False)
                
            self.axis3.add_patch(rectangle)
            self.FigureCanvas3.draw()

    def cutoff_img(self):
        """
        cut off img
        """
        if self.fig3_range == None:
            return

        self.cur_img3 = self.cur_img3[self.fig3_range[2]:self.fig3_range[3], self.fig3_range[0]:self.fig3_range[1]]
        
        self.axis3.cla()
        self.axis3.imshow(self.cur_img3)
        self.FigureCanvas3.draw()

    def change_plot(self, i,j):
        """
        Tab1 クリックされた座標の色とデータを変更
        """
        if self.cur_df.iloc[i,j]:
            self.cur_df.iloc[i,j] = 0
            rectangle = patches.Rectangle(xy=(self.YOKO[j],self.TATE[i]) , width=self.width, height=self.height, alpha = 0.4, color='red')
            self.axis.add_patch(rectangle)
        else:
            self.cur_df.iloc[i,j] = 1
            rectangle = patches.Rectangle(xy=(self.YOKO[j],self.TATE[i]) , width=self.width, height=self.height, alpha = 0.4)
            self.axis.add_patch(rectangle)

        self.FigureCanvas.draw()
        # save csv
        #self.save_csv()

    def save_csv(self):
        """
        save updated CSV
        """
        self.save_table2_changed()
        self.save_table3_changed()
        self.cur_df.to_csv(self.cur_fname, encoding="shift-jis")

    def move_next(self):
        """
        nextボタンが押されたときの処理
        """
        if self.csv_counter > len(self.csv_files) - 3:
            return 
        print(self.csv_counter,len(self.csv_files))
        
        self.csv_counter += 1
        self.save_csv()
        self.image_show()

    def move_back(self):
        """
        backボタンが押されたときの処理
        """
        if self.csv_counter == 0:
            return

        self.csv_counter -= 1
        self.save_csv()
        self.image_show()

    def rotate_l(self):
        """
        画像を右回転させる
        """
        self.img3_rotateang += 90
        if self.img3_rotateang > 360:
            self.img3_rotateang -= 360
        self.cur_img3 = self.rotate_img(self.cur_img3, flag = 1)
        self.axis3.cla()
        self.axis3.imshow(self.cur_img3)
        self.FigureCanvas3.draw()

    def rotate_r(self):
        """
        画像を左回転させる
        """
        self.img3_rotateang -= 90
        if self.img3_rotateang < 0:
            self.img3_rotateang += 360
        self.cur_img3 = self.rotate_img(self.cur_img3, flag = 3)
        self.axis3.cla()
        self.axis3.imshow(self.cur_img3)
        self.FigureCanvas3.draw()

    def rotate_img(self, img, flag = False):
        """
        画像を回転させる
        """
        if not flag:
            rot_num = (self.img3_rotateang//90) %4
            #print(rot_num, self.img3_rotateang)
        else:
            rot_num = flag

        if rot_num == 1:
            img_res = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot_num == 3:
            img_res = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rot_num == 2:
            img_res = cv2.rotate(img, cv2.ROTATE_180)
        else:
            img_res = img
        
        return img_res


def main():
    fname = 'C:\\Users\\saisa\\OneDrive - Hiroshima University\\授業用\\4年\\Programs_py\\PDF_questionnaire_tally\\pdf_test'
    Filechk = FileExistanceCHK(fname)
    pdf_files = Filechk.pdffiles
    csv_files = Filechk.csvfiles
    app = QApplication(sys.argv)
    window = MainWindow(fname, pdf_files, csv_files)
    sys.exit(app.exec_())
    

if __name__ == '__main__':
    #main()
    app = QApplication(sys.argv)
    window = SubWindow()
    sys.exit(app.exec_())