"""Transformation utilities for normalizing and enriching source datasets before consolidation."""

import logging
import re
import pandas as pd
import numpy as np
from scr.models import (
    normalized_edicom_column_names,
    raw_edicom_column_names,
    patterns_raw_edicom_column_names,
    patterns_normalized_edicom_column_names,
    raw_metadata_column_names,
    MONTH_MAP,
    CFDI_USE_MAP,
)

logger = logging.getLogger(__name__)

def normalize_concepts(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Convert wide concept columns into a long-form DataFrame.

    The source files may contain concept-related columns such as CONCEPTO1,
    TOTALCONCEPTO1, and CLAVEPRODSERVCONCEPTO1 across multiple repeated groups.
    This function reshapes those columns into a normalized structure with a single
    concept row per record.

    Args:
        wide_df: A DataFrame containing one or more repeated concept column groups.

    Returns:
        A normalized DataFrame with concept, total, and product-code columns.
    """
    logger.debug("Starting normalize_concepts", extra={"rows": int(wide_df.shape[0])})
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
    logger.debug("Found concept indices", extra={"indices": indxs})
    long_dfs = []
    try:
        for i in indxs:
            concepto = next(
                (c for c in (f"CONCEPTO{i}", f"CONCEPT{i}") if c in wide_df.columns),
                None,
            )

            total = f"TOTALCONCEPTO{i}"
            clave = f"CLAVEPRODSERVCONCEPTO{i}"

            if concepto is None:
                logger.debug("No concepto column for index", extra={"index": i})
                continue

            cols_presentes = [
                c for c in [concepto, total, clave] if c in wide_df.columns
            ]

            mask = wide_df[cols_presentes].notna().any(axis=1)
            df_temp = pd.DataFrame(
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
            if "OBSERVACIONES" in df_temp.columns and i > 1:
                df_temp["OBSERVACIONES"] = "-"
                if df_temp.empty:
                    logger.debug("df_temp is empty for index", extra={"index": i})
            long_dfs.append(df_temp)
    except Exception as e:
        logger.exception("Error while normalizing concepts", exc_info=e)
        raise
    if not long_dfs:
        logger.warning("No concept columns found; returning empty DataFrame")
        return pd.DataFrame()
    long_df = pd.concat(long_dfs, ignore_index=True)
    logger.info("Concatenated long dataframe", extra={"rows": int(long_df.shape[0])})
    return long_df

def filter_metadata_info(raw_metadata_df: pd.DataFrame, date_: str) -> pd.DataFrame:
    """Filter metadata rows to include only those relevant to the requested period.

    Args:
        raw_metadata_df: Raw metadata DataFrame.
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A filtered DataFrame containing only rows from the specified year and month.
    """
    logger.info("Filtering metadata info", extra={"rows": int(raw_metadata_df.shape[0])})
    raw_metadata_df = raw_metadata_df.drop_duplicates()
    raw_metadata_df = raw_metadata_df[raw_metadata_df["EfectoComprobante"] == "I"]
    year, month = map(int, date_.split("_"))
    raw_metadata_df["FechaEmision"] = pd.to_datetime(raw_metadata_df["FechaEmision"])
    filtered_df = raw_metadata_df[
        (raw_metadata_df["FechaEmision"].dt.year == year)
        & (raw_metadata_df["FechaEmision"].dt.month <= month)
    ]
    logger.info(
        "Filtered metadata info", extra={"rows": int(filtered_df.shape[0])}
    )
    return filtered_df

def transform_metadata_info(raw_metadata_df: pd.DataFrame, date_: str) -> pd.DataFrame:
    """Normalize metadata rows into the format expected by downstream integration logic.

    Args:
        raw_metadata_df: Raw metadata rows read from the input archive.

    Returns:
        A transformed DataFrame with standardized dates, period fields, and status values.
    """
    logger.info("Transforming metadata info", extra={"rows": int(raw_metadata_df.shape[0])})
    # raw_metadata_df = filter_metadata_info(raw_metadata_df, date_)
    selected_raw_metadata_cols = get_metadata_normalized_column_names(raw_metadata_df)
    old_metadata_df = raw_metadata_df[selected_raw_metadata_cols]
    new_metadata_df = old_metadata_df.copy()
    new_metadata_df["FechaEmision"] = pd.to_datetime(
        new_metadata_df["FechaEmision"], format="%Y-%m-%d %H:%M:%S"
    )
    new_metadata_df["FechaCancelacion"] = pd.to_datetime(
            new_metadata_df["FechaCancelacion"], format="%Y-%m-%d %H:%M:%S"
        )

    new_metadata_df["FechaCancelacion"] = new_metadata_df["FechaCancelacion"].dt.strftime("%d/%m/%Y")
    new_metadata_df["Fecha"] = new_metadata_df["FechaEmision"].dt.strftime("%m/%d/%Y")
    new_metadata_df["Día"] = new_metadata_df["FechaEmision"].dt.day
    new_metadata_df["Mes"] = new_metadata_df["FechaEmision"].dt.month
    new_metadata_df["Periodo"] = new_metadata_df["FechaEmision"].dt.month.map(MONTH_MAP)
    new_metadata_df["PERIODO"] = new_metadata_df["Periodo"]
    new_metadata_df["FechaEmision"] = new_metadata_df["FechaEmision"].dt.strftime("%d/%m/%Y")
    new_metadata_df = new_metadata_df.rename(columns={"Estatus": "ESTATUS METADATA"})
    new_metadata_df["ESTATUS"] = new_metadata_df["ESTATUS METADATA"].map(
        {
            1: "VIGENTE",
            0: "CANCELADO",
        }
    )
    logger.debug("Transformed metadata info", extra={"rows": int(new_metadata_df.shape[0])})
    return new_metadata_df

def get_metadata_normalized_column_names(raw_metadata_df: pd.DataFrame) -> list[str]:
    """Validate that the required metadata columns are present before transformation.

    Args:
        raw_metadata_df: Raw metadata DataFrame to inspect.

    Returns:
        The ordered list of metadata columns required for transformation.

    Raises:
        ValueError: If any required metadata column is missing.
    """
    missing_columns = [
        col for col in raw_metadata_column_names if col not in raw_metadata_df.columns
    ]
    if missing_columns:
        logger.error("Missing required metadata columns", extra={"missing": missing_columns})
        raise ValueError(
            f"Las siguientes columnas requeridas no se encuentran en el DataFrame de metadatos: {', '.join(missing_columns)}"
        )
    return raw_metadata_column_names

def get_edicom_normalized_column_names(raw_edicom_df: pd.DataFrame) -> list[str]:
    """Select and validate the Edicom columns needed for transformation.

    Args:
        raw_edicom_df: Raw Edicom workbook content.

    Returns:
        The normalized column list that will be used for the transformation step.

    Raises:
        ValueError: If the source schema does not match the expected layout.
    """
    edicom_colname = list(raw_edicom_df.columns)
    clean_edicom_colname = [n for n in edicom_colname if "Unnamed" not in n]

    # Buscar la última columna válida CLAVEPRODSERVCONCEPTOX
    last_clave = next(
        col
        for col in reversed(edicom_colname)
        if (
            "Unnamed" not in col
            and col.startswith("CLAVEPRODSERVCONCEPTO")
        )
    )

    # Obtener el número X
    last_num = int(re.search(r"(\d+)$", last_clave).group(1))

    new_columns = []
    current_num = last_num + 1
    position_in_group = 0

    for col in edicom_colname:

        if "Unnamed" not in col:
            new_columns.append(col)
            continue

        if position_in_group == 0:
            new_columns.append(f"CONCEPTO{current_num}")
        elif position_in_group == 1:
            new_columns.append(f"TOTALCONCEPTO{current_num}")
        else:
            new_columns.append(f"CLAVEPRODSERVCONCEPTO{current_num}")
            current_num += 1

        position_in_group = (position_in_group + 1) % 3

    raw_edicom_df.columns = new_columns
    # logger.debug("Inspecting edicom columns", extra={"columns": clean_edicom_colname})

    if len(normalized_edicom_column_names) != len(raw_edicom_column_names):
        logger.error("Mismatch edicom columns length", extra={"expected": len(raw_edicom_column_names), "actual": len(normalized_edicom_column_names)})
        raise ValueError(
            f"El número de columnas en el archivo Edicom ({len(clean_edicom_colname)}) no coincide con el número esperado de columnas ({len(raw_edicom_column_names)})."
        )

    if len(patterns_raw_edicom_column_names) != len(
        patterns_normalized_edicom_column_names
    ):
        logger.error("Mismatch patterns length", extra={"patterns_raw": len(patterns_raw_edicom_column_names), "patterns_normalized": len(patterns_normalized_edicom_column_names)})
        raise ValueError(
            f"El número de patrones en patterns_raw_column_names ({len(patterns_raw_edicom_column_names)}) no coincide con el número esperado de patrones en patterns_normalized_column_names ({len(set(patterns_normalized_edicom_column_names))})."
        )

    selected_raw_edicom_cols = raw_edicom_column_names + [
        c
        for c in new_columns
        if any(pattern in c for pattern in patterns_raw_edicom_column_names)
    ]
    logger.debug("Selected edicom columns for transformation", extra={"selected": selected_raw_edicom_cols})
    return selected_raw_edicom_cols

def transform_edicom_info(raw_edicom_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Edicom rows into the internal structure used by the pipeline.

    The function standardizes dates, filters invoice-type rows, derives contract
    metadata, and computes the IVA percentage field expected later in the workflow.

    Args:
        raw_edicom_df: Raw Edicom data loaded from the source workbook.

    Returns:
        A transformed DataFrame ready for integration with metadata and CFDI data.
    """
    logger.info("Transforming edicom info", extra={"rows": int(raw_edicom_df.shape[0])})
    selected_raw_edicom_cols = get_edicom_normalized_column_names(raw_edicom_df)
    old_edicom_df = raw_edicom_df[selected_raw_edicom_cols]
    new_edicom_df = old_edicom_df.copy()
    new_edicom_df["FECHADOCUMENTO"] = pd.to_datetime(
        new_edicom_df["FECHADOCUMENTO"],
        dayfirst=True,
        errors="coerce"
    )

    new_edicom_df["FECHADOCUMENTO"] = new_edicom_df["FECHADOCUMENTO"].dt.strftime("%d/%m/%Y")

    new_edicom_df["FECHAREAL"] = pd.to_datetime(
        new_edicom_df["FECHAREAL"],
        dayfirst=True,
        errors="coerce"
    )

    new_edicom_df["FECHAREAL"] = new_edicom_df["FECHAREAL"].dt.strftime("%d/%m/%Y %H:%M:%S")

    new_edicom_df = new_edicom_df[new_edicom_df["TIPODECOMPROBANTE"] == "I"]
    new_edicom_df["CONTRATO (CLAVE)"] = new_edicom_df["CONTRATO"].str[4:11]
    new_edicom_df["% DE IVA"] = new_edicom_df["IVA"] / new_edicom_df["SUBTOTAL"]
    new_edicom_df["% DE IVA"] = new_edicom_df["% DE IVA"].fillna(0)
    new_edicom_df["% DE IVA"] = new_edicom_df["% DE IVA"].map('{:.0%}'.format)
    new_edicom_df["Contrato MID"] = new_edicom_df["CONTRATO"].str[0:3]
    logger.debug("Transformed edicom dataframe", extra={"rows": int(new_edicom_df.shape[0])})
    return new_edicom_df

def transform_cfdi_info(raw_cfdi_df: pd.DataFrame, date_: str) -> pd.DataFrame:
    """Enrich CFDI rows with business-friendly usage labels and column aliases.

    Args:
        raw_cfdi_df: Raw CFDI data retrieved from the database.

    Returns:
        A transformed DataFrame with normalized usage and IVA-related columns.
    """
    logger.info("Transforming cfdi info", extra={"rows": int(raw_cfdi_df.shape[0])})
    transformer_cfdi_df = raw_cfdi_df.copy()
    transformer_cfdi_df = transformer_cfdi_df[transformer_cfdi_df["TIPO_COMPROBANTE"] == "I"]
    year, month = map(int, date_.split("_"))
    transformer_cfdi_df["FECHA"] = pd.to_datetime(
        transformer_cfdi_df["FECHA"]
    )

    transformer_cfdi_df = transformer_cfdi_df[
        (transformer_cfdi_df["FECHA"].dt.year == year) &
        (transformer_cfdi_df["FECHA"].dt.month <= month)
    ]
    transformer_cfdi_df["USO CFDI"] = transformer_cfdi_df["CFDI_USE"].map(CFDI_USE_MAP)
    transformer_cfdi_df["FECHA_PERIODO"] = (
        transformer_cfdi_df["FECHA"].dt.month.map(MONTH_MAP)
    )
    transformer_cfdi_df = transformer_cfdi_df.rename(columns={"CONCEPTO_IVA":"% DE IVA POR CONCEPTO"})
    return transformer_cfdi_df