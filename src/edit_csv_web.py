import os
import copy

import pandas as pd
import numpy as np

from land_code_conv import LandCodeConv

LOCATION_NUM = 440 # 440


class Create_CSV_WEB:
    """
    Summary.CSVとそれぞれのCSVファイルは同じディレクトリにあることが前提
    
    """
    def __init__(self, fname):
        self.fname = fname
        self.locaton_CSV_path = 'location_numbers.csv'
        self.file_dir = os.path.dirname(self.fname)
        self.all_csv_name = self.file_dir + '\\' + 'all_data.csv'

        self.col_final = ['CSV file','PDF name','A:Age','B:Sex','C:House','D:Jobs','D:Others','E:Working','F:Shopping','G:Stay','H:Child','H:Others','Posting num','Area']

        self.df = None
        self.df_Comment = None
        self.df_anc2 = None
        self.all_df = None
        self.all_df2 = None
        self.land_code_df = None

        self.arr_TF = None
        self.arr_Eval = None

    def check_excelfile(self):
        """
        Excelファイルが存在するかチェック 
        OK : 4
        NG : 0
        """
        try:
            df = pd.read_excel(self.fname)
            col = df.columns.tolist()
            if col[1] == 'collector_id':
                self.df = df
                print('Excel file is correct')
                return 4
            else:
                print('Excel file is not correct')
                return 0
        
        except FileNotFoundError:
            print('{} is not found'.format(self.fname))
        except PermissionError:
            print('{} is not open'.format(self.fname))    
        
    def read_location_csv(self):
        self.lcc = LandCodeConv(self.locaton_CSV_path)

    def make_all_df(self, n):
        """
        make all_df
        """
        column_all = []
        for i in range(1, LOCATION_NUM+1):
            column_all.append('Q{}_TF'.format(i))
            column_all.append('Q{}_Eval'.format(i))
            column_all.append('Q{}_comment1'.format(i))
        for i in range(1, LOCATION_NUM+1):
            column_all.append('Q{}_comment2'.format(i))

        datas = [['0' for i in range(LOCATION_NUM*4)] for j in range(n)]
        datas2 = [['0' for i in range(len(self.col_final))] for j in range(n)]
        self.all_df = pd.DataFrame(datas, columns=column_all)
        self.all_df2 = pd.DataFrame(datas2, columns=self.col_final)

    def df_preprocess(self):
        df2 = self.df.iloc[1:, 9:].fillna(0)

        df_anc1 = df2.iloc[:,:df2.shape[1]-10] # アンケート1
        self.df_anc2 = df2.iloc[:,df2.shape[1]-10:] # アンケート2

        df_TF_pre = df2.iloc[:,[i for i in range(df_anc1.shape[1]) if (i%9 == 0) or (i%9 == 1)]] # TF 
        df_Eval_pre = df2.iloc[:,[i for i in range(df_anc1.shape[1]) if (i%9 in [2,3,4,5,6,7])]] # 評価
        self.df_Comment = df2.iloc[:,np.arange(9, df_anc1.shape[1]+1, 9)-1] # コメント

        
        self.arr_TF = df_TF_pre.iloc[:, [i for i in range(df_TF_pre.shape[1]) if i%2 == 0]].to_numpy()
        self.arr_Eval = df_Eval_pre.iloc[:, [i for i in range(df_Eval_pre.shape[1]) if i%6 == 0]].to_numpy()

        for i in range(df_anc1.shape[1]//9):
            TF_add = df_TF_pre.iloc[:,2*i+1].to_numpy()
            Eval_add = df_Eval_pre.iloc[:,6*i+1:6*i+5].sum(axis=1).to_numpy()
            
            self.arr_TF[:,i] += TF_add
            self.arr_Eval[:,i] += Eval_add
    
    def eval2value(self, i):
        """
        TF
        ・重なる                 : -1  これは起こらない
        ・途中でやめる            : -2
        ・ランダムで無回答        : -3
        ・評価を無回答           : -4

        評価
        ・重なる          : 平均値 これは起こらない
        ・途中でやめる     : -5 
        ・知らないを無回答 : -6
        ・評価を何一つ回答していない : -7
        ・ランダムで無回答 : -8
        """
        cur_TF = copy.deepcopy(self.arr_TF[i,:])
        cur_Eval = copy.deepcopy(self.arr_Eval[i,:])

        # 途中でやめている index を探す
        stop_index = None # やめた行のインデックス
        idxs_tf = [0] + list(np.where(cur_TF == 0)[0])
        idxs_eval = [0] + list(np.where(cur_Eval == 0)[0])
        idxs = list(set(idxs_tf) & set(idxs_eval))
        idxs.reverse()
        idxs_diff = np.diff(idxs)
        for idx, sum in zip(idxs, idxs_diff):
            if sum != -1:
                break
            stop_index = idx

        # ランダムを無回答
        cur_TF[cur_TF == 0] = -3
        # 評価を無回答
        cur_TF[np.where((cur_TF == -3) & (cur_Eval == 0))] = -4
        
        # =============================================================
        # 評価を何一つ回答していない
        if np.sum(cur_Eval) == 0:
            cur_Eval[:] = -7
        # 知らないを無回答
        eval = np.where(cur_Eval == 0)[0]
        tf = np.where(self.arr_TF[i,:] == 0)[0]
        if len(eval) == len(tf):
            if np.allclose(eval,tf) == True and len(eval) > 0:
                cur_Eval[eval] = -6
        # ランダムを無回答
        cur_Eval[cur_Eval == 0] = -8
        cur_TF[cur_Eval == -8] = -3

        # 途中でやめている
        if not stop_index is None:
            cur_TF[stop_index:] = -2
            cur_Eval[stop_index:] = -5  
        
        # =============================================================
        self.arr_TF[i,:] = cur_TF
        self.arr_Eval[i,:] = cur_Eval

    def add_all_df(self, city):
        """
        add data to all_df
        """
        
        for j in range(self.land_code_df.shape[0]):
            idx = int(self.land_code_df.iloc[j] - 1)

            cur_TF = self.arr_TF[:,j]
            cur_TF = pd.DataFrame(cur_TF, dtype=np.int8)
            cur_Eval = self.arr_Eval[:,j]
            cur_Eval = pd.DataFrame(cur_Eval, dtype=np.float16)
            cur_comment1 = self.df_Comment.iloc[:, j].tolist() # comment1
            cur_comment1 = [str(x) for x in cur_comment1]
            #cur_comment1 = [x.replace('0', '') for x in cur_comment1]
            cur_comment1 = pd.DataFrame(cur_comment1)
          
            self.all_df.iloc[:, idx*3] = cur_TF
            self.all_df.iloc[:, idx*3+1] = cur_Eval
            self.all_df.iloc[:, idx*3+2] = cur_comment1

        self.all_df2.iloc[:, 2:12] = self.df_anc2.iloc[:, :]
        self.all_df2['Area'] = city

    def save_csv(self):
        """
        all_dfをcsvに出力
        """
        self.all_df_fin = pd.concat([self.all_df2, self.all_df], axis=1)
        self.all_df_fin.to_csv(self.all_csv_name, index=False, encoding='shift-jis')
        print('finish')

    def main_process(self, city):
        # 各都市のCSVファイルをロードしておく
        self.read_location_csv()
        # excelファイルの前処理
        self.df_preprocess()
        self.make_all_df(self.arr_TF.shape[0])
        # 各行に対して処理を行う
        for i in range(self.arr_TF.shape[0]):
            self.eval2value(i)
        # 各都市の対応表を取得
        self.land_code_df = self.lcc.convert_land_code(city)
        # 各都市のデータを結合
        self.add_all_df(city)        
        # csvに出力
        self.save_csv()


if __name__ == "__main__":
    filepath = 'C:\\Users\\saisa\\OneDrive - Hiroshima University\\授業用\\4年\\Programs_py\\PDF_questionnaire_tally\\Sheet1.xlsx'
    city = '八本松A'
    csv = Create_CSV_WEB(filepath)
    csv.check_excelfile()
    csv.main_process(city=city)