import glob
from re import T
import sys
import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPixmap

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import cv2
import numpy as np
import pandas as pd
import configparser
from pdf2image import convert_from_path

from file_existence_check import FileExistanceCHK

class ImageProcess():
    def __init__(self, pdffiles) -> None:
        self.pdffiles = pdffiles # pdf file path
        self.pdf2image()

        self.DATANUM = 30 # 質問の行数
        self.YOKO_NUM = 8 # 質問の列数

        self.W_RATIO = 2.5 # 縦方向への拡大率
        self.H_RATIO = 1 # 横方向への拡大率

        # 検出パラメータ
        self.X_OFFSET = 15 # X方向オフセット量：誤検出が大きい場合，大きな値に変更するといいかも 
        self.Y_OFFSET = 15 # Y方向オフセット量：誤検出が大きい場合，大きな値に変更するといいかも 
        self.DETECT_RATIO = 0.1 #検出倍率 小さくするほど検出されやすくなるが誤検出も増加する．
    


    def pdf2image(self):
        """
        convert pdf to image
        """
        pdfimages = convert_from_path(self.pdffiles[0], dpi=150)
        frame_raw0 = np.asarray(pdfimages[0])

        self.frame_trans0 = self.ArUco_process(frame_raw0)

    def ArUco_process(self, frame_raw ,ub = 0, lb = 0):
        """
        read ArUco marker and affine transformation
        """
        ### ARマーカーを読み取る
        dictionary_name = cv2.aruco.DICT_4X4_50
        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_name)

        # ArUcoの処理
        corners, ids, _ = cv2.aruco.detectMarkers(frame_raw, dictionary)
        frame = cv2.aruco.drawDetectedMarkers(frame_raw, corners, ids)

        Coner = [[] for _ in range(3)]
        for i in range(3):
            idx = ids[i][0]
            cur = corners[i][0][0].astype(np.int32)
            Coner[idx] = cur

        p1 = Coner[0] # 右下
        p1[1] -= 60
        p2 = Coner[2] # 左上
        p3 = Coner[1] # 左下
        p4 = p2 + (p1 - p3) # 右上
        p1[0] += lb
        p3[0] += lb
        p2[0] += ub
        p4[0] += ub

        Ps = [p2,p4,p3,p1]
        wide = np.linalg.norm(p3 - p1)
        wide = int(wide)
        height = np.linalg.norm(p3 - p2)
        height = int(height)

        # 変換前後の対応点を設定
        p_original = np.float32(Ps)
        p_trans = np.float32([[0, 0],[wide, 0],[0, height], [wide, height]])

        # 変換マトリクスと射影変換
        M = cv2.getPerspectiveTransform(p_original, p_trans)
        frame_trans = cv2.warpPerspective(frame, M, (wide, height))
        return frame_trans

    def plot_img0(self):
        """
        plot image (left upper)
        """
        cur_img = self.frame_trans0[0:600,0:600]        
        return cv2.cvtColor(cur_img, cv2.COLOR_BGR2RGB)
    
    def plot_img1(self):
        """
        plot image (right bottom)
        """
        x_ = self.frame_trans0.shape[0]
        y_ = self.frame_trans0.shape[1]
        cur_img = self.frame_trans0[x_-400:x_,y_-400:y_]      
        return cv2.cvtColor(cur_img, cv2.COLOR_BGR2RGB)
    
    def plot_img2(self, xp1, yp1, xp2, yp2):
        """
        plot image (wide)
        """
        self.frame_resize = self.frame_trans0[yp1:self.frame_trans0.shape[0]+yp2, xp1:self.frame_trans0.shape[1]+xp2]
        return cv2.cvtColor(self.frame_resize, cv2.COLOR_BGR2RGB)       

    def plot_img3(self, xp3, yp3):
        """
        final check
        """
        frame_res = self.frame_resize[0:self.frame_resize.shape[0], 0:xp3]
        return cv2.cvtColor(frame_res, cv2.COLOR_BGR2RGB)

    def frame_prepare(self, frame_trans, xp1, yp1, xp2, yp2, xp3, yp3):
        frame_resize = frame_trans[yp1:frame_trans.shape[0]+yp2, xp1:frame_trans.shape[1]+xp2]
        frame_res = frame_resize[0:frame_resize.shape[0], 0:xp3]
        
        p_original = np.float32([[0, 0],[frame_res.shape[1], 0],[0, frame_res.shape[0]], [frame_res.shape[1], frame_res.shape[0]]])
        wide   = int(frame_res.shape[1]*self.W_RATIO)
        height = int(frame_res.shape[0]*self.H_RATIO)
        p_trans = np.float32([[0, 0],[wide, 0],[0, height], [wide, height]])

        # 変換マトリクスと射影変換
        M = cv2.getPerspectiveTransform(p_original, p_trans)
        frame_res = cv2.warpPerspective(frame_res, M, (wide, height))
        return frame_res

    def image_chk(self, img):
        ### 画像処理
        TATE = [int(img.shape[0]/self.DATANUM*i) for i in range(self.DATANUM+1)] # データの行数
        YOKO = [int(img.shape[1]/self.YOKO_NUM*i) for i in range(self.YOKO_NUM+1)] # データの列数
        RES = [[0]*8 for _ in range(self.DATANUM)] 

        for i in range(len(YOKO)-1):
            for j in range(len(TATE)-1):
                x1,y1 = YOKO[i], TATE[j]
                x2,y2 = YOKO[i+1], TATE[j+1]

                ## 各格子の前処理
                img_cur = img[y1:y2,x1:x2]
                img_cur = cv2.cvtColor(img_cur, cv2.COLOR_BGR2GRAY)
                ret, img_cur = cv2.threshold(img_cur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                
                img_cur_ = img_cur[self.X_OFFSET:img_cur.shape[0]-self.X_OFFSET, self.Y_OFFSET:img_cur.shape[1]-self.Y_OFFSET]
                img_bw = cv2.bitwise_not(img_cur_)

                ## なにか描いてあるかどうかの判定
                if np.sum(np.sum(img_bw)) > img_cur_.shape[0]*img_cur_.shape[1]*self.DETECT_RATIO:
                    RES[j][i] = 1

        df = pd.DataFrame(RES)
        return df

    def main_process(self, filepath, xp1, yp1, xp2, yp2, xp3, yp3, ocr_flag = True): 
        pdfimages = convert_from_path(filepath, dpi=150)
        frame_raw = np.asarray(pdfimages[0])
        frame_trans = self.ArUco_process(frame_raw)
        
        if ocr_flag:
            frame_res  =  self.frame_prepare(frame_trans, xp1, yp1, xp2, yp2, xp3, yp3)
            df_all = self.image_chk(frame_res)
            Index = ['Point{}'.format(i) for i in range(df_all.shape[0])]
            Col = ['True','False','Very Good', 'Good', 'A little Good', 'Not so so Bad', 'Not so Bad', 'Bad']
            df_all.index = Index
            df_all.columns = Col
            df_all = df_all.reindex(columns=Col + ['Comment','Comment 2'])

            df_all.to_csv(filepath.split('.')[0] + '.csv', encoding='shift_jis')
            return frame_res, df_all
        else:
            frame_resize = frame_trans[yp1:frame_trans.shape[0]+yp2, xp1:frame_trans.shape[1]+xp2]
            frame_res1 = frame_resize[0:frame_resize.shape[0], 0:xp3]
            frame_res2 = frame_resize[0:frame_resize.shape[0], xp3:frame_resize.shape[1]]
            frame_res3 = np.asarray(pdfimages[1])
            return frame_res1, frame_res2, frame_res3
    
"""
GUI Window
画像を切り取る位置を指定する．

"""
class OCRWindow(QWidget):
    def __init__(self, pdffiles = None):
        super().__init__()
        self.setWindowTitle('OCR')
        self.setGeometry(100, 100, 800, 800)

        self.img_count = 0
        self.pdffiles = pdffiles
        self.img_preprocess = ImageProcess(pdffiles)

        self.initUI()
        self.show()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab1 = QWidget()   
        self.tab2 = QWidget()
        self.tabs.resize(600,500)

        # Add tabs
        self.tabs.addTab(self.tab1, "Image")
        self.tabs.addTab(self.tab2, "パラメータ設定")

        # Create tabs
        self.initUI_tab1()
        self.initUI_tab2()

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def initUI_tab1(self):
        self.tab1.layout = QVBoxLayout(self)

        # ----------------
        # Create Widgets
        # ----------------
        grid = QGridLayout()
        grid.setSpacing(10)

        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        # Figureを作成
        plt.rcParams["font.size"] = 8 #フォントサイズ
        self.Figure = plt.figure()
        self.FigureCanvas = FigureCanvas(self.Figure)
        self.axis = self.Figure.add_subplot(1,1,1)

        # button
        self.button_next = QPushButton('Next')
        self.button_next.clicked.connect(self.next_img)
        self.button_reset = QPushButton('Reset')
        self.button_reset.clicked.connect(self.reset_img)
        self.button_return = QPushButton('Exit')
        self.button_return.clicked.connect(self.return_main)

        # slider
        self.slider0 = QSlider(self)
        self.slider0.setOrientation(Qt.Horizontal)
        self.slider0.setSizePolicy(size_policy)

        self.slider1 = QSlider(self)
        self.slider1.setOrientation(Qt.Horizontal)
        self.slider1.setSizePolicy(size_policy)

        # spinbox
        self.spinbox0 = QSpinBox(self)
        self.spinbox1 = QSpinBox(self)

        self.slider0.valueChanged.connect(self.slider0_changed)
        self.slider1.valueChanged.connect(self.slider1_changed)
        self.spinbox0.valueChanged.connect(self.spinbox0_changed)
        self.spinbox1.valueChanged.connect(self.spinbox1_changed)

        # figplot
        self.img_plot(self.img_preprocess.plot_img0())
        # set label location
        grid.addWidget(self.FigureCanvas, 0, 0, 6, 3)
        grid.addWidget(QLabel('X方向'), 1, 4, 1, 1)
        grid.addWidget(self.spinbox0, 1, 5, 1, 1)
        grid.addWidget(self.slider0, 2, 4, 1, 5)
        grid.addWidget(QLabel('Y方向'), 3, 4, 1, 1)
        grid.addWidget(self.spinbox1, 3, 5, 1, 1)
        grid.addWidget(self.slider1, 4, 4, 1, 5)
        grid.addWidget(self.button_return, 6, 4, 1, 1)
        grid.addWidget(self.button_reset, 6, 6, 1, 1)
        grid.addWidget(self.button_next, 6, 7, 1, 1)
        #self.setLayout(grid)
        self.tab1.setLayout(grid)
    
    def spinbox0_changed(self):
        self.slider0.setValue(self.spinbox0.value())
        self.update_plot()

    def spinbox1_changed(self):
        self.slider1.setValue(self.spinbox1.value())
        self.update_plot()
    
    def slider0_changed(self):
        self.spinbox0.setValue(self.slider0.value())
        self.update_plot()

    def slider1_changed(self):
        self.spinbox1.setValue(self.slider1.value())
        self.update_plot()

    def img_plot(self, img = None):
        self.cur_img = img

        height, width, channel = self.cur_img.shape
        self.slider0.setRange(0, width)
        self.slider1.setRange(0, height)
        self.slider0.setValue(50)
        self.slider1.setValue(50)
        self.spinbox0.setRange(0, width)
        self.spinbox1.setRange(0, height)
        self.spinbox0.setValue(108)
        self.spinbox1.setValue(429)

        self.update_plot()

    def update_plot(self):
        self.axis.cla()
        self.axis.imshow(self.cur_img)

        x,y = self.spinbox0.value(), self.spinbox1.value()
        self.axis.scatter(x,y)
        self.axis.plot([x,x],[y-40,y+40])
        self.axis.plot([x-40,x+40],[y,y])

        self.FigureCanvas.draw()
    
    def initUI_tab2(self):
        self.tab2.layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setSpacing(20)

        #self.setStyleSheet(' font-size: 15px')
        # ----------------
        # spinbox
        self.spinbox2 = QSpinBox(self)
        self.spinbox3 = QSpinBox(self)
        self.spinbox4 = QDoubleSpinBox(self)
        self.spinbox5 = QDoubleSpinBox(self)
        self.spinbox6 = QSpinBox(self)
        self.spinbox7 = QSpinBox(self)
        self.spinbox8 = QDoubleSpinBox(self)

        # set initial value
        self.spinbox2.setRange(0, 50)
        self.spinbox2.setValue(30)
        self.spinbox3.setRange(0, 20)
        self.spinbox3.setValue(8)

        self.spinbox4.setRange(0, 4)
        self.spinbox4.setValue(2.5)
        self.spinbox4.setSingleStep(0.1)
        self.spinbox5.setRange(0, 4)
        self.spinbox5.setValue(1)
        self.spinbox5.setSingleStep(0.1)

        self.spinbox6.setRange(0, 30)
        self.spinbox6.setValue(15)
        self.spinbox7.setRange(0, 30)
        self.spinbox7.setValue(15)

        self.spinbox8.setRange(0, 2)
        self.spinbox8.setValue(0.1)
        self.spinbox8.setSingleStep(0.05)

        # labels
        label1 = QLabel('質問の数')
        label2 = QLabel('画像の前処理パラメータ')
        label3 = QLabel('OCR 検出パラメータ')
        label3_1 = QLabel('誤検出が多い場合，この値を大きくする')
        label3_2 = QLabel('誤検出が少ない場合，この値を大きくする')
        label4_1 = QLabel('小さくするほど検出されやすくなるが，誤検出が多くなる')

        grid.addWidget(label1, 0, 1, 1, 1)
        grid.addWidget(QLabel('質問の行数'), 1, 0, 1, 1)
        grid.addWidget(self.spinbox2, 1, 1, 1, 1)
        grid.addWidget(QLabel('質問の列数'), 2, 0, 1, 1)
        grid.addWidget(self.spinbox3, 2, 1, 1, 1)

        grid.addWidget(label2, 3, 1, 1, 1)
        grid.addWidget(QLabel('縦方向への拡大率'), 4, 0, 1, 1)
        grid.addWidget(self.spinbox4, 4, 1, 1, 1)
        grid.addWidget(QLabel('横方向への拡大率'), 5, 0, 1, 1)
        grid.addWidget(self.spinbox5, 5, 1, 1, 1)
        
        grid.addWidget(label3, 6, 1, 1, 1)
        grid.addWidget(QLabel('X方向オフセット量'), 7, 0, 1, 1)
        grid.addWidget(self.spinbox6, 7, 1, 1, 1)
        grid.addWidget(label3_1, 7, 2, 1, 1)
        grid.addWidget(QLabel('Y方向オフセット量'), 8, 0, 1, 1)
        grid.addWidget(self.spinbox7, 8, 1, 1, 1)
        grid.addWidget(label3_2, 8, 2, 1, 1)

        grid.addWidget(QLabel('検出倍率'), 9, 0, 1, 1)
        grid.addWidget(self.spinbox8, 9, 1, 1, 1)
        grid.addWidget(label4_1, 9, 2, 1, 1)

        grid.addWidget(QLabel(' '), 10, 0, 1, 1)

        self.tab2.setLayout(grid)

    def next_img(self):
        """
        画像の切り替え
        """
        self.spinbox0.setVisible(True)
        self.spinbox1.setVisible(True)
        self.slider0.setVisible(True)
        self.slider0.setVisible(True)

        self.img_count += 1
        if self.img_count == 1:
            self.xp1, self.yp1 = self.spinbox0.value(), self.spinbox1.value()
            cur_img = self.img_preprocess.plot_img1()
            self.img_plot(cur_img)
            self.spinbox0.setValue(387)
            self.spinbox1.setValue(385)
        
        elif self.img_count == 2:
            self.xp2, self.yp2 = self.spinbox0.value()-400, self.spinbox1.value()-400
            cur_img = self.img_preprocess.plot_img2(self.xp1, self.yp1, self.xp2, self.yp2)
            self.img_plot(cur_img)
            self.spinbox0.setValue(1024)

        elif self.img_count == 3:
            self.xp3, self.yp3 = self.spinbox0.value(), self.spinbox1.value()
            cur_img = self.img_preprocess.plot_img3(self.xp3, self.yp3)
            self.img_plot(cur_img)
            self.spinbox0.setVisible(False)
            self.spinbox1.setVisible(False)
            self.slider0.setVisible(False)
            self.slider0.setVisible(False)

        elif self.img_count >= 4:
            msgBox = QMessageBox.question(None, "確認", "実行しますか？", QMessageBox.Ok, QMessageBox.Cancel)
            if msgBox == QMessageBox.Ok:
                print('run')
                self.take_over_param()
                self.subWindow = OCRSubWindow(len(self.pdffiles))
                self.subWindow.show()
                self.run_ocr()
            else:
                cur_img = self.img_preprocess.plot_img0()
                self.img_plot(cur_img)
                self.img_count = 0
                print('cancel')
    
    def reset_img(self):
        msgBox = QMessageBox.question(None, "確認", "リセットしますか？", QMessageBox.Ok, QMessageBox.Cancel)
        if msgBox == QMessageBox.Ok:
            self.img_count = 0
            cur_img = self.img_preprocess.plot_img0()
            self.img_plot(cur_img)

    def take_over_param(self):
        """
        各パラメータを設定
        """
        self.img_preprocess.DATANUM = self.spinbox2.value()
        self.img_preprocess.YOKO_NUM = self.spinbox3.value()
        self.img_preprocess.W_RATIO = self.spinbox4.value()
        self.img_preprocess.H_RATIO = self.spinbox5.value()
        self.img_preprocess.X_OFFSET = self.spinbox6.value()
        self.img_preprocess.Y_OFFSET = self.spinbox7.value()
        self.img_preprocess.DETECT_RATIO = self.spinbox8.value()

    def run_ocr(self):
        """
        OCRを実行
        CSVファイルが存在する場合は，警告を表示し，続行するかどうかを確認する．
        """
        fname = os.path.dirname(self.pdffiles[0])
        chk_fileexist = FileExistanceCHK(fname)
        chk_flag = chk_fileexist.chk_flag
        if chk_flag == 2:
            msgBox = QMessageBox.warning(None, "警告", "CSVファイルが存在します．上書きしますか？", QMessageBox.Ok, QMessageBox.Cancel)
            if msgBox == QMessageBox.Cancel:
                self.subWindow.close()
                return

        self.config_write()
        self.make_summary_csv()
        self.timer_ = QTimer(self)
        self.i = 0
        self.timer_.timeout.connect(self._run)
        self.timer_.start(100)

    def _run(self):
        cur_pdf = self.pdffiles[self.i]
        #print(self.i)
        img, df = self.img_preprocess.main_process(cur_pdf, self.xp1, self.yp1, self.xp2, self.yp2, self.xp3, self.yp3)
        self.subWindow.show_img(img, df, self.i)
        self.i += 1
        if self.i == len(self.pdffiles):
            self.timer_.stop()
            self.subWindow.close()

    def config_write(self):
        """
        設定ファイルを書き込む
        """
        fname = os.path.dirname(self.pdffiles[0])
        fname = fname + '/' + 'config.ini'
        config = configparser.ConfigParser()
        config['DEFAULT'] = {'XP1': str(self.xp1),
                             'YP1': str(self.yp1),
                             'XP2': str(self.xp2),
                             'YP2': str(self.yp2),
                             'XP3': str(self.xp3),
                             'YP3': str(self.yp3),
                             'DATANUM': str(self.img_preprocess.DATANUM),
                             'YOKO_NUM': str(self.img_preprocess.YOKO_NUM),
                             'W_RATIO': str(self.img_preprocess.W_RATIO),
                             'H_RATIO': str(self.img_preprocess.H_RATIO),
                             'X_OFFSET': str(self.img_preprocess.X_OFFSET),
                             'Y_OFFSET': str(self.img_preprocess.Y_OFFSET),
                             'DETECT_RATIO': str(self.img_preprocess.DETECT_RATIO)}
        with open(fname, 'w') as configfile:
            config.write(configfile)

    def make_summary_csv(self):
        """
        make summary csv
        """
        fname = os.path.dirname(self.pdffiles[0])
        csvname = fname + '/' + 'summary.csv'
        csvnames = [curpdf.replace('pdf','csv') for curpdf in self.pdffiles]
        names = [os.path.basename(filepath) for filepath in self.pdffiles]
        df = pd.DataFrame({'CSV file':csvnames,'PDF name':names})
        df = df.reindex(columns= ['CSV file','PDF name', 'A:Age','B:Sex','C:House','D:Jobs','D:Others','E:Working','F:Shopping','G:Stay','H:Child','H:Others','Posting num','Area'])
        df.to_csv(csvname, index=False, encoding='shift jis')

    def return_main(self):
        msgBox = QMessageBox.question(None, "確認", "終了しますか？", QMessageBox.Ok, QMessageBox.Cancel)
        if msgBox == QMessageBox.Ok:
            self.close()

"""
OCR の実行時に表示されるウィンドウ
プログレスバーと認識結果が表示される
"""
class OCRSubWindow(QWidget):
    def __init__(self, PDF_NUM = 0, parent = None):
        super(OCRSubWindow, self).__init__(parent)
        self.setWindowTitle('OCR Processing')
        self.setGeometry(100, 100, 800, 800)

        self.PDF_NUM = PDF_NUM
        self.W_RATIO = 2.5 # 縦方向への拡大率
        self.H_RATIO = 1 # 横方向への拡大率

        self.initUI()

    def initUI(self):
        grid = QGridLayout()

        # Figureを作成
        plt.rcParams["font.size"] = 8 #フォントサイズ
        plt.rcParams["figure.figsize"] = (8, 16) # グラフサイズ
        self.Figure = plt.figure()
        self.FigureCanvas = FigureCanvas(self.Figure)
        self.axis = self.Figure.add_subplot(1,1,1)

        self.progress_bar = QProgressBar(self)
        # set label location
        grid.addWidget(self.FigureCanvas, 0, 0, 6, 3)
        grid.addWidget(self.progress_bar, 6, 0, 1, 3)
        self.setLayout(grid)

    def show_img(self, img, df, i_num):
        self.axis.cla()

        img = cv2.resize(img, dsize=None, fx=1/self.W_RATIO , fy=1/self.H_RATIO)
        self.axis.imshow(img)


        DATANUM, YOKO_NUM = df.shape
        YOKO_NUM -= 2 ################
        TATE = [int(img.shape[0]/DATANUM*i) for i in range(DATANUM+1)] # データの行数
        YOKO = [int(img.shape[1]/YOKO_NUM*i) for i in range(YOKO_NUM+1)] # データの列数
        width = YOKO[1] - YOKO[0]
        height = TATE[1] - TATE[0]

        #for y in TATE:
        #    for x in YOKO:
        #        self.axis.scatter(x,y)

        for i in range(DATANUM):
            for j in range(YOKO_NUM):
                if df.iloc[i,j]:
                    rectangle = patches.Rectangle(xy=(YOKO[j],TATE[i]) , width=width, height=height, alpha = 0.4)
                    self.axis.add_patch(rectangle)
        self.FigureCanvas.draw()
        self.progress_bar.setValue(int(100*(i_num+1)/self.PDF_NUM))


if __name__ == '__main__':
    fname = 'C:\\Users\\saisa\\OneDrive - Hiroshima University\\授業用\\4年\\Programs_py\\PDF_questionnaire_tally\\pdfs'
    pdffiles = glob.glob(fname + '/*.pdf')

    app = QApplication(sys.argv)
    window = OCRWindow(pdffiles)
    sys.exit(app.exec_())