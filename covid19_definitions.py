import datetime as dt

FILE_CSV = "serie_historica_acumulados.csv"
URL_FILE_CSV = 'https://covid19.isciii.es/resources/{0}'.format(FILE_CSV)
SZ_COLUMN_CA = "CCAA"
SZ_COLUMN_DATE = "FECHA"
SZ_COLUMN_HOSPITALIZED = "Hospitalizados"
COLUMNS_USE = [SZ_COLUMN_CA, SZ_COLUMN_DATE, SZ_COLUMN_HOSPITALIZED]
BUCKET = "covid19-jota"
FILE_ENCODING = 'cp1252'
FILE_HOSPITALIZED_GA =  "Hospitalized_ga.png"
FILE_HOSPITALIZED_SP = "Hospitalized_sp.png"
FILE_HOSPITALIZED_BY_CA = "Hospitalized_ca.png"
FILE_VARIATION_GA = "Variation_ga.png"
FILE_VARIATION_SP =  "Variation_sp.png"
FILE_VARIATION_BY_CA =  "Variation_ca.png"
DATE_INIT_CONFINEMENT = dt.datetime(2020,3, 14)
DATE_INIT_HARD_CONFINEMENT = dt.datetime(2020,3, 30)

FILES_COPY = [FILE_CSV,
              FILE_HOSPITALIZED_GA,
              FILE_HOSPITALIZED_SP,
              FILE_VARIATION_GA,
              FILE_VARIATION_SP,
              FILE_VARIATION_BY_CA,
              FILE_HOSPITALIZED_BY_CA]