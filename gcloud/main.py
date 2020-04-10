import requests
import pandas as pd
import matplotlib.pyplot as plt
import math
import pycountry
from google.cloud import storage
from shutil import copyfile
import datetime as dt
from typing import List
import argparse

FILE_CSV = "serie_historica_acumulados.csv"
URL_FILE_CSV = 'https://covid19.isciii.es/resources/{0}'.format(FILE_CSV)
SZ_COLUMN_CA = "CCAA"
SZ_COLUMN_DATE = "FECHA"
SZ_COLUMN_HOSPITALIZED = "Hospitalizados"
COLUMNS_USE = [SZ_COLUMN_CA, SZ_COLUMN_DATE, SZ_COLUMN_HOSPITALIZED]
BUCKET = "covid19-jota"
FILE_ENCODING = 'cp1252'
FILE_HOSPITALIZED_GA = "Hospitalized_ga.png"
FILE_HOSPITALIZED_SP = "Hospitalized_sp.png"
FILE_HOSPITALIZED_BY_CA = "Hospitalized_ca.png"
FILE_VARIATION_GA = "Variation_ga.png"
FILE_VARIATION_SP = "Variation_sp.png"
FILE_VARIATION_BY_CA = "Variation_ca.png"
DATE_INIT_CONFINEMENT = dt.datetime(2020, 3, 14)
DATE_INIT_HARD_CONFINEMENT = dt.datetime(2020, 3, 30)
FILES_COPY = [FILE_CSV,
              FILE_HOSPITALIZED_GA,
              FILE_HOSPITALIZED_SP,
              FILE_VARIATION_GA,
              FILE_VARIATION_SP,
              FILE_VARIATION_BY_CA,
              FILE_HOSPITALIZED_BY_CA]


def get_tmp_path(file: str) -> str:
    return "/tmp/{0}".format(file)


def plot(dates: List,
         value: List,
         title: str = "",
         file_to_save: str = None) -> None:
    """
    Plot a graph
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
    plt.axvline(DATE_INIT_CONFINEMENT,
                color='r',
                label='Confinement')
    plt.axvline(DATE_INIT_HARD_CONFINEMENT,
                color='orange',
                label='Hard Confinement')
    plt.legend()
    if file_to_save is not None:
        fig.savefig(file_to_save)


def ca_get_name(code: str) -> str:
    try:
        st = pycountry.subdivisions.get(code='ES-' + code)
        return st.name.split(',')[0].split('/')[0]
    except:
        return code


def get_data(url_file_csv: str,
             local_file_csv: str) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame):
    r = requests.get(url_file_csv, allow_redirects=True)
    open(local_file_csv, 'wb').write(r.content)
    df_read = pd.read_csv(local_file_csv, encoding=FILE_ENCODING)
    ldf = df_read[COLUMNS_USE].copy()
    ldf["Date"] = pd.to_datetime(ldf[SZ_COLUMN_DATE], format='%d/%m/%Y')
    ldf[SZ_COLUMN_HOSPITALIZED] = ldf[SZ_COLUMN_HOSPITALIZED].fillna(0)
    ldf = ldf.dropna()
    ldf_ga = ldf[ldf[SZ_COLUMN_CA] == "GA"]
    ldf_es = ldf.groupby("Date").sum()
    ldf_es["Date"] = ldf_es.index
    return ldf, ldf_ga, ldf_es


def get_diff_hospitalized_by_day(df: pd.DataFrame) -> List:
    return df[SZ_COLUMN_HOSPITALIZED] - df[SZ_COLUMN_HOSPITALIZED].shift(1)


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
        ax[column, row].axvline(DATE_INIT_CONFINEMENT, color='r')
        ax[column, row].axvline(DATE_INIT_HARD_CONFINEMENT, color='orange')
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


def copy_to_gs(lst_files: List, bucket_name: str) -> None:
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    for file in lst_files:
        blob = bucket.blob(file)
        blob.upload_from_filename(filename=get_tmp_path(file))


def copy_to_local(lst_files: List) -> None:
    for file in lst_files:
        copyfile(get_tmp_path(file), "./{0}".format(file))


def do_calc_temp() -> str:
    df_general, df_ga, df_es = get_data(URL_FILE_CSV, get_tmp_path(FILE_CSV))
    plot(df_ga["Date"],
         df_ga[SZ_COLUMN_HOSPITALIZED],
         title="Hospitalized Galician",
         file_to_save=get_tmp_path(FILE_HOSPITALIZED_GA))
    plot(df_es["Date"],
         df_es[SZ_COLUMN_HOSPITALIZED],
         title="Hospitalized Spain",
         file_to_save=get_tmp_path(FILE_HOSPITALIZED_SP))
    plot(df_es["Date"],
         get_diff_hospitalized_by_day(df_es),
         title="Variation hospitalized by covid19 Spain",
         file_to_save=get_tmp_path(FILE_VARIATION_SP))
    plot(df_ga["Date"],
         get_diff_hospitalized_by_day(df_ga),
         title="Variation hospitalized by covid19 Galician",
         file_to_save=get_tmp_path(FILE_VARIATION_GA))
    plot_by_ca(df_general,
               plot_diff=True,
               file_to_save=get_tmp_path(FILE_VARIATION_BY_CA),
               title="Variation by CA")
    plot_by_ca(df_general,
               plot_diff=False,
               file_to_save=get_tmp_path(FILE_HOSPITALIZED_BY_CA),
               title="Hospitalized by CA")
    return "From {0} to {1}".format(df_general["Date"].min().date(),
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
