import glob
import os

"""
ファイルの存在を確認
何も存在しない : chk_flag = 0
PDFのみ存在 : chk_flag = 1
PDF+CSVが存在 : chk_flag = 2

CSVとPDFの名前が等しくないと chk_flag = 2にならないので注意
"""
class FileExistanceCHK():
    def __init__(self, fname = None) -> None:
        self.fname = fname
        self.chk_flag = 0
        self.pdffiles = None

        self.check_pdf_exitance()
        self.check_csv_exitance()
        self.check_summary_csv_exitance()
        #print(self.chk_flag)


    def check_pdf_exitance(self):
        self.pdffiles = glob.glob(self.fname + '/*.pdf')
        if len(self.pdffiles) != 0:
            self.chk_flag = 1
        
    def check_csv_exitance(self):
        self.csvfiles = glob.glob(self.fname + '/*.csv')

        if len(self.csvfiles) == 0:
            return

        pdf_basenemes = [os.path.basename(pdf).split('.',1)[0] for pdf in self.pdffiles]
        csv_basenames = [os.path.basename(csv).split('.',1)[0] for csv in self.csvfiles]

        pdf_basenemes.sort()
        csv_basenames.sort()

        for pdf_basename, csv_basename in zip(pdf_basenemes, csv_basenames):
            if pdf_basename != csv_basename:
                print('{} is not match {}'.format(pdf_basename, csv_basename))
                self.chk_flag = 1
                break
            else:
                self.chk_flag = 2
    
    def check_summary_csv_exitance(self):
        summary_csv = self.fname + '\\' + 'summary.csv'
        if os.path.exists(summary_csv):
            self.chk_flag = 3

if __name__ == '__main__':
    fname = 'C:\\Users\\saisa\\OneDrive - Hiroshima University\\授業用\\4年\\Programs_py\\PDF_questionnaire_tally\\pdfs'
    FileExistanceCHK(fname)