import os

import pandas as pd
import numpy as np

from land_code_conv import LandCodeConv



LOCATION_NUM = 440 # 440


class Create_CSV:
    """
    Summary.CSVとそれぞれのCSVファイルは同じディレクトリにあることが前提
    
    """
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.main_csv_name = self.file_dir + '\\' + 'summary.csv'
        self.locaton_CSV_path = 'location_numbers.csv'
        self.all_csv_name = self.file_dir + '\\' + 'all_data.csv'
         
        self.csv_files = None
        self.progress_state = None
        self.col = ['True', 'False', 'Very Good', 'Good', 'A little Good', 'Not so so Bad', 'Not so Bad', 'Bad','Comment','Comment 2']

    def chk_file_exists(self):
        try:
            pd.read_csv(self.main_csv_name, encoding='shift-jis')
            print('summary.csv exists')
            return True
        except FileNotFoundError:
            print('summary.csv not found')
            return False

    def read_location_csv(self):
        self.lcc = LandCodeConv(self.locaton_CSV_path)

    def read_single_csv(self, csv_name):
        """
        read single csv file 
        
        """
        csv_name = os.path.basename(csv_name)
        filepath = self.file_dir + '\\' + csv_name
        df = pd.read_csv(filepath, encoding='shift-jis', index_col=0)
        df = df.set_axis(self.col, axis=1, inplace=False)
        df_res = self.eval2value(df)

        df_res2 = df_res.set_axis([i for i in range(df.shape[0])], axis=0, inplace=False)
        return df_res2
    
    def read_main_csv(self):
        """
        read summary csv
        """
        self.summary_df = pd.read_csv(self.main_csv_name, encoding='shift-jis')
        self.csv_files = self.summary_df['CSV file'].tolist()
        #print(self.summary_df)

        df_length = self.summary_df.shape[0]
        # all csvs
        column_all = []
        for i in range(1, LOCATION_NUM+1):
            column_all.append('Q{}_TF'.format(i))
            column_all.append('Q{}_Eval'.format(i))
            column_all.append('Q{}_comment1'.format(i))
        for i in range(1, LOCATION_NUM+1):
            column_all.append('Q{}_comment2'.format(i))
        self.all_df = pd.DataFrame(np.zeros((df_length, LOCATION_NUM*4)), columns=column_all).astype(int)

    def main_csv_conv(self, i):
        """
        summary.CSVの各行の処理

        その後 all_dfに追加
        """
        single_csv_path = self.summary_df.iloc[i,0]
        area = self.summary_df.iloc[i,13]

        ### conv df 
        single_df = self.read_single_csv(single_csv_path)
        land_code_df = self.lcc.convert_land_code(area)
        single_df = pd.concat([single_df, land_code_df], axis=1)

        print(area, single_csv_path)
        #print(single_df)
        ### add to all_df
        for n in range(single_df.shape[0]):
            idx = single_df.iloc[n,12] - 1
            try: 
                idx = int(idx)
                #print(area, idx)
                cur_TF = single_df.iloc[n, 10] # TF
                cur_Eval = single_df.iloc[n, 11] # Eval
                cur_comment1 = str(single_df.iloc[n, 8]) # comment1
                cur_comment2 = str(single_df.iloc[n, 9]) # comment2

                self.all_df.iloc[i, idx*3] = int(cur_TF)
                self.all_df.iloc[i, idx*3+1] = float(cur_Eval)
                self.all_df.iloc[i, idx*3+2] = (lambda x: x if x != 'nan' else '')(cur_comment1)
                self.all_df.iloc[i, LOCATION_NUM*3 + idx] = (lambda x: x if x != 'nan' else '')(cur_comment2)

            except ValueError:
                print('地域指定が間違っています, file:' + single_csv_path)



    def eval2value(self, df):
        """
        TF
        ・重なる                 : -1
        ・途中でやめる            : -2
        ・ランダムを無回答        : -3
        ・評価を無回答           : -4

        評価
        ・重なる          : 平均値
        ・途中でやめる     : -5
        ・知らないを無回答 : -6
        ・評価を何一つ回答していない    : -7
        ・ランダムで無回答 : -8
        """
        df['TF'] = df['True'].values + df['False'].values*2
        df['Eval'] = df['Very Good'].values*1 + df['Good'].values*2 + df['A little Good'].values*3 \
                        + df['Not so so Bad'].values*4 + df['Not so Bad'].values*5 + df['Bad'].values*6
        
          
        # 途中でやめている行数をカウント
        stop_index = None # やめた行のインデックス
        stop_indexs = df.index[(df['TF'] == 0) & (df['Eval'] == 0)].tolist()[::-1]
        stop_indexs = [int(i[5:]) for i in stop_indexs]
        stop_cumsum = np.diff([df.shape[0]] + stop_indexs)
        for idx, sum in zip(stop_indexs, stop_cumsum):
            if sum != -1:
                break
            stop_index = idx
        # 重なる
        df['TF'] = df['TF'].apply(lambda x: -1 if x == 3 else x)
        # ランダムを無回答
        df['TF'] = df['TF'].apply(lambda x: -3 if x == 0 else x)
        # 評価を無回答
        df['TF'] = df.apply(lambda x: -4 if x['Eval'] == 0 else x['TF'], axis=1)
        
        # =============================================================
        # 重なる
        df['Eval'] = df['Eval'].apply(lambda x: x/2 if x > 6 else x)
        # 評価を何一つ回答していない
        if df['Eval'].sum() == 0:
            df['Eval'] = -7
        # 知らないを無回答
        if ((df['False'] == 1) == (df['Eval'] == 0)).all():
            if np.sum(df['False']) != 0:
                df['Eval'] = df.apply(lambda x: -6 if x['False']==1 else x['Eval'], axis=1)
        # ランダムを無回答
        df['Eval'] = df['Eval'].apply(lambda x: -8 if x == 0 else x)
        df['TF'] = df.apply(lambda x: -3 if x['Eval'] == -8 else x['TF'], axis=1)
        # 途中でやめている

        if not stop_index is None:
            df.iloc[stop_index:,11] = -5
            df.iloc[stop_index:, 10] = -2        

        return df

    def all_df2csv(self):
        """
        all_dfをcsvに出力
        """
        self.all_df_fin = pd.concat([self.summary_df, self.all_df], axis=1)
        self.all_df_fin.to_csv(self.all_csv_name, index=False, encoding='shift-jis')
        print('finish')

    def main_process(self):
        if not self.chk_file_exists():
            return 
        
        self.read_location_csv()
        self.read_main_csv()

        for i in range(self.summary_df.shape[0]):
            self.main_csv_conv(i)
        
        self.all_df2csv()


if __name__ == "__main__":
    filepath = '景観　アンケート　結果　30項目　済'
    csv = Create_CSV(filepath)
    csv.main_process()