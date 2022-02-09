import pandas as pd


class LandCodeConv:
    def __init__(self, csv_path) -> None:
        self.path = csv_path

        self.read_csv()

    def read_csv(self):
        self.df = pd.read_csv(self.path, encoding='shift-jis')

    def convert_land_code(self, city_name):
        try:
            city_name = city_name.strip()
            df = self.df[[city_name, city_name + '_番号']]
            df_re = df.rename(columns={city_name: city_name, city_name + '_番号': 'land_code'})
            df_re = df_re.dropna().astype(int)
            df_landcode = df_re['land_code']

            return df_landcode

        except KeyError:
            print('{} is not found'.format(city_name))
            exit()

def main():
    path = 'location_numbers.csv'
    lcc = LandCodeConv(path)
    df = lcc.convert_land_code('高屋A')
    print(df)

if __name__ == '__main__':
    main()