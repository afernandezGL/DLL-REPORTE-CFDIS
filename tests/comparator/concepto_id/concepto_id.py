"""Script para comparar dos archivos Excel y generar un archivo de salida con las diferencias en los prefijos."""
import pandas as pd
import os

from scr.loader import get_cfdi_info
from scr.transformer import transform_cfdi_info

directorio = os.getcwd()
print(f"Directorio actual: {directorio}")
# Archivos
salida_dir = os.path.join(directorio, "tests/comparator/concepto_id/salida.xlsx")
resultado_dir = os.path.join(directorio, "tests/comparator/concepto_id/resultado.xlsx")
# Archivos
salida_df = pd.read_excel(salida_dir)
fecha = "2026_04"
raw_cfdi_df = get_cfdi_info(fecha, rfc_emisor_list=["2", "1"])
transformed_cfdi_df = transform_cfdi_info(raw_cfdi_df, fecha)
faltantes = transformed_cfdi_df[
    ~transformed_cfdi_df["CONCEPTO_ID"].isin(salida_df["CONCEPTO_ID"])
].copy()
faltantes.to_excel(resultado_dir, index=False)