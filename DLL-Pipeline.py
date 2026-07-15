import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
import pymssql

data = pd.read_excel(r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/INFORMACION/2026_01/REPORTE FACTURACIÓN - ENERO 2026.xlsx')
colname = list(data.columns)
nombres_limpios = [n for n in colname if "Unnamed" not in n]


back = ['ESTATUS',
 'TIPODECOMPROBANTE',
 'SERIE',
 'FOLIO',
 'FECHAREAL',
 'FECHADOCUMENTO',
 'UUID',
 'SUBTOTAL',
 'IVA',
 'TOTAL',
 'RECEPTORRFC',
 'RECEPTOR NOMBRE',
 'METODOPAGO',
 'MONEDA',
 'CONTRATO',
 'OBSERVACIONES',
 'CONCEPTO1',
 'TOTALCONCEPTO1',
 'CLAVEPRODSERVCONCEPTO1']

data2 = data[back]
new = [
    'ESTATUS',	
    'TIPO DE COMPROBANTE',	
    'SERIE',	
    'FOLIO',	
    'FECHA REAL',	
    'FECHA DOCUMENTO',	
    'UUID',	 
    'SUBTOTAL', 	 
    'IVA', 	 
    'TOTAL', 	
    'RECEPTOR RFC',	
    'RECEPTOR NOMBRE',	
    'METODO DE PAGO',	
    'MONEDA',	
    'CONTRATO',	
    'OBSERVACIONES',	
    'CONCEPTO',	 
    'TOTAL CONCEPTO', 	 
    'CÓDIGO PRODUCTO']

data2.columns = new
df = data2[data2['TIPO DE COMPROBANTE'] == 'I']

# Diccionario con los meses en español
meses_es = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

df['FECHA REAL'] = pd.to_datetime(df['FECHA REAL'])

df['PERIODO'] = df['FECHA REAL'].dt.month.map(meses_es)

df['DIA'] = df['FECHA REAL'].dt.day

df['MES'] = df['FECHA REAL'].dt.month

df['Fecha'] = df['FECHA REAL'].dt.strftime('%d/%m/%Y')



server = '127.0.0.1'
port = '8282'            
database = 'GENERAL'
username = 'Procesos.Automatizados'
password = 'gL#W1N&a$48NsH7*'

try:
    conn = pymssql.connect(
        server = server,
        port=port,
        database=database,
        user=username,
        password=password
    )

    #connection_url = (
    #    f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}"
    #    "?driver={ODBC Driver 17 for SQL Server}"
    #)
    #engine = create_engine(connection_url)
    query = "SELECT FECHA_TC, DETERMINACION_TC FROM GENERAL.IVA.BANXICO_TIPO_CAMBIO"

    df_tc = pd.read_sql(query, conn)
    print(df_tc)
except Exception as e:
    print(f"Error durante la extracción: {e}")
finally:
    conn.close()


df_tc = df_tc.sort_values('FECHA_TC')

df_tc['DETERMINACION_TC'] = df_tc['DETERMINACION_TC'].replace(0, np.nan)

df_tc['DETERMINACION_TC'] = df_tc['DETERMINACION_TC'].ffill()
df_tc['DETERMINACION_TC'] = df_tc['DETERMINACION_TC'].bfill()

df_tc['FECHA_TC'] = df_tc['FECHA_TC'].dt.strftime('%d/%m/%Y')

df_final = df_final = pd.merge(df, df_tc, left_on='Fecha', right_on='FECHA_TC', how='left')

df_final['TC'] = np.where(df_final['MONEDA'] == 'USD', df_final['DETERMINACION_TC'], 1)

meta1 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/0DF84719-D342-4888-9EA2-D79DA4FE3682_01.txt', 
    sep='~'
)

meta2 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/3E8C8FF2-15A2-48BB-85F9-0DDA70D7E8D9_01.txt', 
    sep='~'
)

meta3 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/DCBE91DD-58F2-47B2-B289-76AA1A3CDE11_01.txt', 
    sep='~'
)

meta4 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/6CA57674-E72A-478B-B088-690AB454DB25_01.txt', 
    sep='~'
)

meta5 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/1DD73245-6482-45EB-B61A-904675C4F505_01.txt', 
    sep='~'
)

meta6 = pd.read_csv(
    r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/METADATA/659A874C-1D79-49F2-B1CB-9246750EAB54_01.txt', 
    sep='~'
)

meta_final = pd.concat([meta1, meta2, meta3, meta4, meta5, meta6])

df_final2 = pd.merge(df_final, meta_final[['Uuid', 'Monto', 'FechaEmision', 'Estatus', 'FechaCancelacion']], left_on='UUID', right_on='Uuid', how='left')

df_final2['FechaEmision'] = pd.to_datetime(df_final2['FechaEmision'])

df_final2['PERIODO_METADATA'] = df_final2['FechaEmision'].dt.month.map(meses_es)

df_final2['ESTATUS2'] = df_final2['Estatus'].apply(lambda x: 'VIGENTE' if x == 1 else 'CANCELADO')

df_final2['TC'] = pd.to_numeric(df_final2['TC'], errors='coerce')

df_final2['TC'].unique()

df_final2['TOTAL_CALCULADO'] = np.where(
    df_final2['Estatus'] == 1, 
    df_final2['TOTAL CONCEPTO'] * df_final2['TC'], 
    0
)

df_final2['ESTATUS REPORTE INTERNO VS METADATA'] = np.where(
    df_final2['ESTATUS'] == df_final2['ESTATUS2'], 
    1, 
    0
)

df_final2['CONTRATO (CLAVE)'] = df_final2['CONTRATO'].str[4:11]

df_final2['% DE IVA'] = df_final2['IVA']/df_final2['SUBTOTAL']


server = '127.0.0.1'
port = '8282'            
database = 'GENERAL'
username = 'Procesos.Automatizados'
password = 'gL#W1N&a$48NsH7*'

try:
    conn = pymssql.connect(
        server = server,
        port=port,
        database=database,
        user=username,
        password=password
    )

    #connection_url = (
    #    f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}"
    #    "?driver={ODBC Driver 17 for SQL Server}"
    #)
    #engine = create_engine(connection_url)
    query2 = "SELECT UUID_PADRE, TASA FROM DLL.SAT.REPORTE_FACTURACION_FINAL"

    df_ts = pd.read_sql(query2, conn)
    print(df_tc)
except Exception as e:
    print(f"Error durante la extracción: {e}")
finally:
    conn.close()

df_final3 = pd.merge(df_final2,df_ts, left_on='UUID', right_on='UUID_PADRE', how='left')


# 1. Normalizamos las columnas a texto en minúsculas para que las búsquedas no fallen 
# por una letra mayúscula o un espacio.
concepto = df_final3['CONCEPTO'].astype(str).str.lower()
serie = df_final3['SERIE'].astype(str).str.strip().str.upper() # Serie a mayúsculas
contrato = df_final3['CONTRATO'].astype(str).str.lower()
iva = df_final3['% DE IVA'].astype(str).str.lower()

# 2. Definimos las reglas (CONDICIONES)
# OJO: El orden importa. Siempre se ponen primero las más específicas (como renta anticipada)
# para que no choquen con las más generales (como renta).
condiciones = [
    # ---- Reglas combinadas de Concepto + IVA ----
    (concepto.str.contains('renta anticipada')) & (iva.str.contains('16')),
    (concepto.str.contains('renta anticipada')) & (iva.str.contains('0|exento')),
    (concepto.str.contains('renta')) & (iva.str.contains('16')),
    (concepto.str.contains('renta')) & (iva.str.contains('0|exento')),
    
    (concepto.str.contains('venta')) & (iva.str.contains('16')),
    (concepto.str.contains('venta')) & (iva.str.contains('0|exento')),

    # ---- Reglas específicas de Concepto ----
    (concepto.str.contains('seguro de vida|prima de seguro de vida')),
    (concepto.str.contains('seguro equipo|seguro resp civil')),
    (concepto.str.contains('subsidio|comisión mercantil')),
    (concepto.str.contains('arrendamiento financiero')),
    (concepto.str.contains('comisión por apertura')),
    (concepto.str.contains('gastos de administración')),
    (concepto.str.contains('opción a compra')),
    (concepto.str.contains('osprey')),
    (concepto.str.contains('prima seguros')),
    (concepto.str.contains('reembolso|daños de equipo')),

    (serie == 'DE'),

    (contrato.str.contains('factoraje')),
    (contrato.str.contains('arrendamiento instalaciones')),
    (contrato.str.contains('udi'))
]

prefijos = [
    'REN ANT', 'REN ANT 0%', 'REN', 'REN 0%',
    'VEN', 'VEN 0%',
    'SEG VIDA', 'SEG', 'SUB',
    'ARR', 'COM', 'GAS', 'OPC', 'OSPREY', 'PRI', 'REEMBOLSO',
    'DE',
    'Factoraje', 'SUBARR', 'UDI'
]

df_final3['Prefijo'] = np.select(condiciones, prefijos, default='OTH')
df_final3['Contrato MID'] = df_final3['CONTRATO'].str[0:3]

df_final3['USO CFDI'] = ''
df_final3[['ESTATUS', 'TIPO DE COMPROBANTE', 'SERIE', 'FOLIO', 'FECHA REAL',
       'FECHA DOCUMENTO', 'UUID', 'SUBTOTAL', 'IVA', 'TOTAL', 'RECEPTOR RFC',
       'RECEPTOR NOMBRE', 'METODO DE PAGO', 'MONEDA', 'CONTRATO',
       'OBSERVACIONES', 'CONCEPTO', 'TOTAL CONCEPTO', 'CÓDIGO PRODUCTO',
       'PERIODO', 'DIA', 'MES', 'Fecha', 'TC', 'Uuid', 'Monto', 'FechaEmision', 'PERIODO_METADATA',  'Estatus',
       'ESTATUS2', 'TOTAL_CALCULADO',
       'ESTATUS REPORTE INTERNO VS METADATA', 'FechaCancelacion',
          'CONTRATO (CLAVE)', 'Prefijo', '% DE IVA', 'TASA', 'USO CFDI','Contrato MID']].to_excel(r'/Users/alanavelinofernandezjuarez/Documents/REPO_GITHUB/DLL-main/INFORMACION/2026_01/prueba-dll.xlsx', index = False)