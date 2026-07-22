import pandas as pd
import numpy as np
import re
from scr.models import prefixes, raw_edicom_column_names, raw_metadata_column_names, normalized_edicom_column_names, normalized_metadata_column_names


def integrate_data(consolidated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Integrate the consolidated DataFrame with additional data sources if needed.

    Args:
        consolidated_dataframe (pd.DataFrame): The consolidated DataFrame to be integrated.
    """
    consolidated_df["ESTATUS REPORTE INTERNO VS METADATA"] = np.where(
        consolidated_df["ESTATUS_EDICOM"].str.upper()
        == consolidated_df["ESTATUS_METADATA"].str.upper(),
        1,
        0,
    )
    consolidated_df = consolidated_df.rename(columns={"ESTATUS_METADATA": "ESTATUS"})
    consolidated_df['Tipo de cambio'] = np.where(consolidated_df['MONEDA'] == 'USD', consolidated_df['DETERMINACION_TC'], 1)

    consolidated_df['Tipo de cambio'] = pd.to_numeric(consolidated_df['Tipo de cambio'], errors='coerce')

    consolidated_df['Tipo de cambio'].unique()

    normalized_df = normalize_concepts(consolidated_df)

    normalized_df['TOTAL CONCEPTO MXN'] = np.where(
        normalized_df['ESTATUS METADATA'] == 1,
        normalized_df['TOTAL CONCEPTO'] * normalized_df['Tipo de cambio'],
        0
    )
    # Normalize the columns to lowercase text so that searches do not fail due to an uppercase letter or a space.
    concepto = normalized_df['CONCEPTO'].astype(str).str.lower()
    serie = normalized_df['SERIE'].astype(str).str.strip().str.upper() # Serie a mayúsculas
    contrato = normalized_df['CONTRATO'].astype(str).str.lower()
    iva = normalized_df['% DE IVA'].astype(str).str.lower()

    # Define the conditions and corresponding prefixes for the 'Prefijo' column based on the specified rules.
    # WARNING: The order of the conditions matters. More specific conditions should be placed before more general ones to avoid conflicts.
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

    normalized_df['PREFIJO'] = np.select(condiciones, prefixes, default='OTH')
    edicom_column_names = dict(
        zip(raw_edicom_column_names, normalized_edicom_column_names)
    )
    metadata_column_names = dict(
        zip(raw_metadata_column_names,  normalized_metadata_column_names)
    )
    edicom_column_names.pop("ESTATUS", None)

    normalized_column_names = edicom_column_names | metadata_column_names
    normalized_df = normalized_df.rename(columns=normalized_column_names)
    return normalized_df


def normalize_concepts(wide_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = [
        c
        for c in wide_df.columns
        if not re.match(
            r"^(CONCEPTO|CONCEPT1|TOTALCONCEPTO|CLAVEPRODSERVCONCEPTO)\d+$", c
        )
    ]

    indxs = sorted(
        {
            int(re.search(r"(\d+)$", c).group(1))
            for c in wide_df.columns
            if re.search(r"(\d+)$", c)
            and re.match(
                r"^(CONCEPTO|CONCEPT1|TOTALCONCEPTO|CLAVEPRODSERVCONCEPTO)\d+$",
                c,
                re.IGNORECASE,
            )
        }
    )

    dfs = []

    for i in indxs:

        concepto = next(
            (c for c in (f"CONCEPTO{i}", f"CONCEPT1{i}") if c in wide_df.columns), None
        )

        total = f"TOTALCONCEPTO{i}"
        clave = f"CLAVEPRODSERVCONCEPTO{i}"

        if concepto is None:
            continue

        cols_presentes = [c for c in [concepto, total, clave] if c in wide_df.columns]

        mask = wide_df[cols_presentes].notna().any(axis=1)

        dfs.append(
            pd.DataFrame(
                {
                    **{c: wide_df.loc[mask, c].values for c in base_cols},
                    "CONCEPTO": wide_df.loc[mask, concepto].values,
                    "TOTAL CONCEPTO": (
                        wide_df.loc[mask, total].values if total in wide_df else None
                    ),
                    "CÓDIGO PRODUCTO": (
                        wide_df.loc[mask, clave].values if clave in wide_df else None
                    ),
                }
            )
        )
    return pd.concat(dfs, ignore_index=True)
