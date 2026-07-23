import logging
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


def transform_metadata_info(raw_metadata_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transforming metadata info", extra={"rows": int(raw_metadata_df.shape[0])})
    selected_raw_metadata_cols = get_metadata_normalized_column_names(raw_metadata_df)
    old_metadata_df = raw_metadata_df[selected_raw_metadata_cols]
    new_metadata_df = old_metadata_df.copy()
    new_metadata_df["FechaEmision"] = pd.to_datetime(
        new_metadata_df["FechaEmision"], format="%Y-%m-%d %H:%M:%S"
    )

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
    ## Check if all raws_metadata_column_names are present in the raw_metadata_df
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
    edicom_colname = list(raw_edicom_df.columns)
    clean_edicom_colname = [n for n in edicom_colname if "Unnamed" not in n]
    logger.debug("Inspecting edicom columns", extra={"columns": clean_edicom_colname})

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
        for c in clean_edicom_colname
        if any(pattern in c for pattern in patterns_raw_edicom_column_names)
    ]
    logger.debug("Selected edicom columns for transformation", extra={"selected": selected_raw_edicom_cols})
    return selected_raw_edicom_cols


def transform_edicom_info(raw_edicom_df: pd.DataFrame) -> pd.DataFrame:
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


def transform_cfdi_info(raw_cfdi_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transforming cfdi info", extra={"rows": int(raw_cfdi_df.shape[0])})
    transformer_cfdi_df = raw_cfdi_df.copy()
    transformer_cfdi_df["USO CFDI"] = transformer_cfdi_df["CFDI_USE"].map(CFDI_USE_MAP)
    transformer_cfdi_df = transformer_cfdi_df.rename(columns={"TASA":"% DE IVA POR CONCEPTO"})
    transformer_cfdi_df["% DE IVA POR CONCEPTO"] = transformer_cfdi_df["% DE IVA POR CONCEPTO"].fillna("0%")
    transformer_cfdi_df["% DE IVA POR CONCEPTO"] = np.where(
        transformer_cfdi_df["% DE IVA POR CONCEPTO"] == "16%",
        transformer_cfdi_df["% DE IVA POR CONCEPTO"],
        "Exento"
    )
    return transformer_cfdi_df


def transform_banxico_info(raw_banxico_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transforming banxico info", extra={"rows": int(raw_banxico_df.shape[0])})
    transformer_banxico_df = raw_banxico_df.sort_values("FECHA_TC")

    transformer_banxico_df["DETERMINACION_TC"] = transformer_banxico_df[
        "DETERMINACION_TC"
    ].replace(0, np.nan)

    transformer_banxico_df["DETERMINACION_TC"] = transformer_banxico_df[
        "DETERMINACION_TC"
    ].ffill()
    transformer_banxico_df["DETERMINACION_TC"] = transformer_banxico_df[
        "DETERMINACION_TC"
    ].bfill()

    transformer_banxico_df["FECHA_TC"] = transformer_banxico_df["FECHA_TC"].dt.strftime(
        "%d/%m/%Y"
    )
    logger.debug("Transformed banxico dataframe", extra={"rows": int(transformer_banxico_df.shape[0])})
    return transformer_banxico_df
