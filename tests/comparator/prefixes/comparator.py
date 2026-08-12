"""Script para comparar dos archivos Excel y generar un archivo de salida con las diferencias en los prefijos."""

import os

import pandas as pd

directorio = os.getcwd()
print(f"Directorio actual: {directorio}")
# Archivos
salida_dir = os.path.join(directorio, "tests/comparator/prefixes/salida.xlsx")
objetivo_dir = os.path.join(directorio, "tests/comparator/prefixes/objetivo.xlsx")
resultado_dir = os.path.join(directorio, "tests/comparator/prefixes/resultado.xlsx")
# Archivos
salida_df = pd.read_excel(salida_dir)
objetivo_df = pd.read_excel(objetivo_dir)

# Cambia estos nombres si tus columnas se llaman distinto
UUID_COL = "UUID"
MONTO_COL = "TOTAL CONCEPTO"
PREFIJO_COL = "PREFIJO"

# Numerar ocurrencias dentro de cada UUID+MONTO
salida_df["_seq"] = salida_df.groupby([UUID_COL, MONTO_COL]).cumcount()
objetivo_df["_seq"] = objetivo_df.groupby([UUID_COL, MONTO_COL]).cumcount()


# Unir 1ro con 1ro, 2do con 2do, etc.
resultado = salida_df[[UUID_COL, MONTO_COL, PREFIJO_COL, "CONCEPTO", "_seq"]].merge(
    objetivo_df[[UUID_COL, MONTO_COL, PREFIJO_COL, "CONCEPTO", "_seq"]],
    on=[UUID_COL, MONTO_COL, "_seq"],
    how="left",
    suffixes=("_izq", "_der"),
)

# Comparar prefijos
resultado["prefijo_igual"] = (
    resultado[f"{PREFIJO_COL}_izq"] == resultado[f"{PREFIJO_COL}_der"]
)

"FILTER: Solo filas donde los prefijos no coinciden y que prefijo derecho no sea nulo"
resultado = resultado[
    (~resultado["prefijo_igual"]) & (resultado[f"{PREFIJO_COL}_der"].isna())
]

# Limpiar columna auxiliar
resultado.drop(columns=["_seq"], inplace=True)

# Guardar resultado
resultado.to_excel(resultado_dir, index=False)

print("Listo: resultado.xlsx")
