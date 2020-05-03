import requests
import pandas as pd
import matplotlib.pyplot as plt
import math
import pycountry
from google.cloud import storage
from shutil import copyfile
from typing import List
import argparse
from covid19_definitions import *
from typing import Optional
import datetime as dt

FILE_CSV = "serie_historica_acumulados.csv"
FILE_CSV_CA_POPULATION = "PopulationCA.csv"
URL_FILE_CSV = 'https://covid19.isciii.es/resources/{0}'.format(FILE_CSV)
SZ_COLUMN_CA = "CCAA"
SZ_COLUMN_DATE = "FECHA"
SZ_COLUMN_HOSPITALIZED = "Hospitalizados"

COLUMNS_USE = [SZ_COLUMN_CA, SZ_COLUMN_DATE, SZ_COLUMN_HOSPITALIZED]
FILE_ENCODING = 'cp1252'
FILE_HOSPITALIZED_GA = "Hospitalized_ga.png"
FILE_HOSPITALIZED_SP = "Hospitalized_sp.png"
FILE_HOSPITALIZED_BY_CA = "Hospitalized_ca.png"
FILE_HOSPITALIZED_BY_POPULATION = "Hospitalized_by_population.png"
FILE_QUADRANTS_CA = "Quadrants_ca.png"
FILE_VARIATION_GA = "Daily_ga.png"
FILE_VARIATION_SP = "Daily_sp.png"
FILE_VARIATION_BY_CA = "Daily_ca.png"
DATE_INIT_CONFINEMENT = dt.datetime(2020, 3, 14)
DATE_INIT_HARD_CONFINEMENT = dt.datetime(2020, 3, 30)
FILES_COPY = [FILE_CSV,
              FILE_HOSPITALIZED_GA,
              FILE_HOSPITALIZED_SP,
              FILE_VARIATION_GA,
              FILE_VARIATION_SP,
              FILE_VARIATION_BY_CA,
              FILE_HOSPITALIZED_BY_CA,
              FILE_HOSPITALIZED_BY_POPULATION]


SPECIAL_DATES = [{"date": dt.datetime(2020, 3, 14), "label": 'Soft Confinement', "color": "orange"},
                 {"date": dt.datetime(2020, 3, 30), "label": 'Hard Confinement', "color": "r"},
                 {"date": dt.datetime(2020, 4, 13), "label": 'Soft Confinement', "color": "orange"},
                 {"date": dt.datetime(2020, 4, 26), "label": 'Child walk', "color": "blue"},
                 {"date": dt.datetime(2020, 5, 2),  "label": 'Walk and sport', "color": "green"}]
CA_REMOVE = ["ME", "CE"]
DATA_REMOVE = [{"CA": "MD", "DATE": "2020-04-26"}]


def get_tmp_path(file: str) -> str:
    return "/tmp/{0}".format(file)


def get_code(description: str) -> Optional[str]:
    description_last = description.split()[-1]
    if description_last == "Cataluña":
        description_last = "Catalunya"
    for st in pycountry.subdivisions:
        if st.country_code == 'ES':
            if description_last in st.name:
                if st.code.split("-")[1] == 'M':
                    return 'MD'
                return st.code.split("-")[1]
    return None


def get_data(url_file_csv: str,
             local_file_csv: str) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame):
    r = requests.get(url_file_csv, allow_redirects=True)
    open(local_file_csv, 'wb').write(r.content)
    df_read = pd.read_csv(local_file_csv,
                          encoding=FILE_ENCODING,
                          skipfooter=2,
                          engine='python')
    ldf = df_read[COLUMNS_USE].copy()
    ldf["Date"] = pd.to_datetime(ldf[SZ_COLUMN_DATE], format='%d/%m/%Y')
    ldf = ldf[~ldf[SZ_COLUMN_CA].isin(CA_REMOVE)]
    ldf[SZ_COLUMN_HOSPITALIZED] = ldf[SZ_COLUMN_HOSPITALIZED].fillna(0)
    ldf = ldf.dropna()
    ldf_ga = ldf[ldf[SZ_COLUMN_CA] == "GA"]
    ldf_es = ldf.groupby("Date").sum()
    ldf_es["Date"] = ldf_es.index
    return ldf, ldf_ga, ldf_es


def load_ca_population_from_gs(bucket_name: str, file: str) -> pd.DataFrame:
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(file)
    blob.download_to_filename(filename=get_tmp_path(file))
    df_ca = pd.read_csv(get_tmp_path(file),
                        encoding=FILE_ENCODING,
                        delimiter=';')
    df_ca['Total'] = df_ca['Total'].str.replace('.', '')
    df_ca['Total'] = pd.to_numeric(df_ca['Total'])
    df_ca["Code"] = df_ca["Comunidades y Ciudades Autónomas"].apply(get_code)
    return df_ca


def get_diff_hospitalized_by_day(df: pd.DataFrame,
                                 filter: bool = False) -> List:
    lst = df[SZ_COLUMN_HOSPITALIZED] - df[SZ_COLUMN_HOSPITALIZED].shift(1)
    if filter:
        wrong_values = lst[lst > 20000].values
        if len(wrong_values) > 0:
            lst = lst.replace(wrong_values, method='ffill')
    return lst


def get_hospitalized_by_population(df: pd.DataFrame, df_ca: pd.DataFrame) -> (pd.DataFrame,
                                                                              float):
    max_date = df["Date"].max()
    df_last = df[df["Date"] == max_date][["Date", "Hospitalizados", "CCAA"]]
    df_ca_hospitalized_population = pd.merge(df_last[["Hospitalizados", "CCAA"]],
                                             df_ca[["Total", "Code"]],
                                             left_on='CCAA',
                                             right_on='Code')
    df_ca_hospitalized_population["Relation"] = (df_ca_hospitalized_population["Hospitalizados"] * 10000 /
                                                 df_ca_hospitalized_population["Total"])
    df_ca_hospitalized_population["Name"] = df_ca_hospitalized_population["Code"].apply(ca_get_name)
    hospitalized_population_sp = (df_ca_hospitalized_population["Hospitalizados"].sum() * 10000 /
                                  df_ca_hospitalized_population["Total"].sum())
    df_ca_hospitalized_population["Relation_with_sp"] = (df_ca_hospitalized_population["Relation"] -
                                                         hospitalized_population_sp)
    return df_ca_hospitalized_population, hospitalized_population_sp


def plot_special_dates(ax, list_dates: list) -> None:
    for special_date in list_dates:
        ax.axvline(special_date["date"],
                   color=special_date["color"],
                   label=special_date["label"])

def plot_merda(
         value: List,
         title: str = "",
         file_to_save: str = None) -> None:
    """
    Plot a graph
    :param legend:
    :param dates: x values
    :param value: y value
    :param title:
    :param file_to_save: Name file to save, None, not save
    :return:
    """
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.plot(value)
    if file_to_save is not None:
        fig.savefig(file_to_save)

def plot(dates: List,
         value: List,
         title: str = "",
         file_to_save: str = None) -> None:
    """
    Plot a graph
    :param legend:
    :param dates: x values
    :param value: y value
    :param title:
    :param file_to_save: Name file to save, None, not save
    :return:
    """
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.plot(dates, value)
    fig.autofmt_xdate()
    plot_special_dates(ax, SPECIAL_DATES)
    plt.legend()
    if file_to_save is not None:
        fig.savefig(file_to_save)


def ca_get_name(code: str) -> str:
    try:
        st = pycountry.subdivisions.get(code='ES-' + code)
        return st.name.split(',')[0].split('/')[0]
    except:
        return code


def plot_by_ca(df: pd.DataFrame,
               plot_diff: bool = True,
               file_to_save: str = None,
               title: str = None) -> None:
    """
    Plot data by ca
    :param title:
    :param df:
    :param plot_diff: False.- Plot hospitalized
                      True .- Plot hospitalized daily variation
    :param file_to_save:Name file to save, None, not save
    :return:
    """
    lst_ca = list(df[SZ_COLUMN_CA].unique())
    n_columns = 2
    n_rows = math.ceil(len(lst_ca) / n_columns)
    fig, ax = plt.subplots(n_rows,
                           n_columns,
                           figsize=(5, 20))
    for ca in lst_ca:
        index = lst_ca.index(ca)
        column = math.floor(index / n_columns)
        row = index - column * n_columns
        df_ca = df[df[SZ_COLUMN_CA] == ca]
        if plot_diff:
            values = get_diff_hospitalized_by_day(df_ca)
        else:
            values = df_ca[SZ_COLUMN_HOSPITALIZED]
        plot_special_dates(ax[column, row], SPECIAL_DATES)
        ax[column, row].set_title(ca_get_name(ca)[:15])
        ax[column, row].plot(df_ca["Date"], values)
    plt.subplots_adjust(hspace=0.5)
    fig.autofmt_xdate()
    if title is not None:
        fig.suptitle(title, fontsize=16)
    if len(lst_ca) % 2 != 0:
        fig.delaxes(ax[n_rows - 1, n_columns - 1])
    if file_to_save is not None:
        fig.savefig(file_to_save, format='png')


def plot_bars(names: pd.DataFrame,
              values: pd.DataFrame,
              mean: float,
              legend_mean: str = None,
              title: str = None,
              file_to_save: str = None) -> None:
    fig, ax = plt.subplots()
    if title is not None:
        ax.set_title(title)
    fig.autofmt_xdate()
    ax.bar(names,
           values)
    ax.axhline(y=mean,
               color="k",
               label=legend_mean)
    plt.legend()
    if file_to_save is not None:
        fig.savefig(file_to_save, format='png')


def plot_quadrants(x: pd.DataFrame,
                   y: pd.DataFrame,
                   column_merge: str,
                   column_x: str,
                   column_y: str,
                   column_name: str,
                   title: str = None,
                   x_description: str = None,
                   y_description: str = None,
                   file_to_save: str = None,
                   y_center: int = 0,
                   text_show: str = None) -> None:
    df_all = pd.merge(x,
                      y,
                      left_on=column_merge,
                      right_on=column_merge)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.plot(df_all[column_x], df_all[column_y], 'ro')
    ax.spines['left'].set_position('zero')
    ax.spines['bottom'].set_position(('data', y_center))
    for index, row in df_all.iterrows():
        plt.annotate(row[column_name],
                     [row[column_x], row[column_y]])
    ax.set_ylabel(y_description)
    ax.set_xlabel(x_description)
    ax.xaxis.set_label_coords(0.9, 0.42)
    print(x[column_x].min())
    if text_show is not None:
        ax.text(x[column_x].min(),
                0,
                text_show, bbox=dict(facecolor='red', alpha=0.5))
    if title is not None:
        ax.set_title(title)
    if file_to_save is not None:
        fig.savefig(file_to_save, format='png')


def copy_to_gs(lst_files: List, bucket_name: str) -> None:
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    for file in lst_files:
        blob = bucket.blob(file)
        blob.upload_from_filename(filename=get_tmp_path(file))


def copy_to_local(lst_files: List) -> None:
    for file in lst_files:
        copyfile(get_tmp_path(file), "./{0}".format(file))


def last_value_to_str(last_value: tuple) -> str:
    return "{0} - {1}".format(last_value[0], last_value[1])


def do_calc_temp() -> str:
    df_general, df_ga, df_sp = get_data(URL_FILE_CSV, get_tmp_path(FILE_CSV))
    df_ca = load_ca_population_from_gs(BUCKET, FILE_CSV_CA_POPULATION)
    (df_hospitalized_by_population,
     hospitalized_by_population_sp) = get_hospitalized_by_population(df_general, df_ca)
    max_date = df_general["Date"].max()

    last_value_ga = df_ga[df_ga["Date"] == max_date][SZ_COLUMN_HOSPITALIZED].values[0]
    last_value_sp = df_sp[df_sp["Date"] == max_date][SZ_COLUMN_HOSPITALIZED].values[0]

    print(last_value_ga)

    plot(df_ga["Date"],
         df_ga[SZ_COLUMN_HOSPITALIZED],
         title="Accumulated Hospitalized Galician From {0} to {1}. Last {2} ".format(
             df_general["Date"].min().date(),
             df_general["Date"].max().date(),
             last_value_ga),
         file_to_save=get_tmp_path(FILE_HOSPITALIZED_GA))
    plot(df_sp["Date"],
         df_sp[SZ_COLUMN_HOSPITALIZED],
         title="Accumulated Hospitalized Spain From {0} to {1}. Last {2}".format(df_general["Date"].min().date(),
                                                                                 df_general["Date"].max().date(),
                                                                                 last_value_sp),
         file_to_save=get_tmp_path(FILE_HOSPITALIZED_SP))
    diff_sp_day = get_diff_hospitalized_by_day(df_sp, filter=True)
    plot(df_sp["Date"],
         diff_sp_day,
         title="Daily hospitalized by covid19 Spain.Last  {0}".format(diff_sp_day.iloc[-1]),
         file_to_save=get_tmp_path(FILE_VARIATION_SP))
    diff_ga_day = get_diff_hospitalized_by_day(df_ga)
    plot(df_ga["Date"],
         diff_ga_day,
         title="Daily hospitalized by covid19 Galician.Last  {0}".format(diff_ga_day.iloc[-1]),
         file_to_save=get_tmp_path(FILE_VARIATION_GA))
    plot_by_ca(df_general,
               plot_diff=True,
               file_to_save=get_tmp_path(FILE_VARIATION_BY_CA),
               title="Daily by CA")
    plot_by_ca(df_general,
               plot_diff=False,
               file_to_save=get_tmp_path(FILE_HOSPITALIZED_BY_CA),
               title="Accumulated by CA")
    plot_bars(df_hospitalized_by_population['Name'],
              df_hospitalized_by_population['Relation'],
              hospitalized_by_population_sp,
              legend_mean="Mean spain",
              title="Accumulated Hostipalized by 10000 persons",
              file_to_save=get_tmp_path(FILE_HOSPITALIZED_BY_POPULATION))
    '''
    plot_quadrants(df_diff,
                   df_hospitalized_by_population,
                   'CCAA',
                   "Diff_percent",
                   "Relation",
                   "CCAA",
                   title="CCAA comparation. x= % Variation hospilized last week vs y= Hospitalized by 10000",
                   file_to_save=get_tmp_path(FILE_QUADRANTS_CA),
                   x_description="variation",
                   y_description="hospitalizad",
                   y_center=hospitalized_by_population_sp,
                   text_show= "x axel in y spain mean")
    '''
    return "From {0} to {1}".format(max_date.date(),
                                    df_general["Date"].max().date())


def do_calc(event, context) -> str:
    description = do_calc_temp()
    copy_to_gs(FILES_COPY, BUCKET)
    return description


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Variation of people hospitalized by covid19.')
    parser.add_argument('--copy_gs', dest='copy_gs', action='store_const',
                        const=True, default=False,
                        help='Copy to gs')
    parser.add_argument('--show', dest='show', action='store_const',
                        const=True, default=False,
                        help='plot the graph, default only save graphs to files')
    args = parser.parse_args()

    sz = do_calc_temp()
    copy_to_local(FILES_COPY)
    if args.copy_gs:
        copy_to_gs(FILES_COPY, BUCKET)
    if args.show:
        plt.show()
    print(sz)
