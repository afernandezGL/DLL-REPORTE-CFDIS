import logging
import pandas as pd
import numpy as np
import re

# Module logger
logger = logging.getLogger(__name__)
from scr.models import (
    prefixes,
    raw_edicom_column_names,
    raw_metadata_column_names,
    normalized_edicom_column_names,
    normalized_metadata_column_names,
)


def integrate_data(consolidated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Integrate the consolidated DataFrame with additional data sources if needed.

    Args:
        consolidated_dataframe (pd.DataFrame): The consolidated DataFrame to be integrated.
    """
    logger.info(
        "Starting integrate_data", extra={"rows": int(consolidated_df.shape[0])}
    )
    try:
        consolidated_df["ESTATUS REPORTE INTERNO VS METADATA"] = np.where(
            consolidated_df["ESTATUS_EDICOM"].str.upper()
            == consolidated_df["ESTATUS_METADATA"].str.upper(),
            1,
            0,
        )
    except Exception as e:
        logger.exception(
            "Error computing ESTATUS REPORTE INTERNO VS METADATA", exc_info=e
        )
        raise
    if "ESTATUS_METADATA" in consolidated_df.columns:
        consolidated_df = consolidated_df.rename(
            columns={"ESTATUS_METADATA": "ESTATUS"}
        )
        logger.debug("Renamed ESTATUS_METADATA to ESTATUS")
    else:
        logger.warning("ESTATUS_METADATA column not found; ESTATUS rename skipped")
    try:
        consolidated_df["Tipo de cambio"] = np.where(
            consolidated_df["MONEDA"] == "USD", consolidated_df["DETERMINACION_TC"], 1
        )
    except Exception as e:
        logger.exception("Error assigning Tipo de cambio", exc_info=e)
        raise

    consolidated_df["Tipo de cambio"] = pd.to_numeric(
        consolidated_df["Tipo de cambio"], errors="coerce"
    )
    logger.debug(
        "Converted Tipo de cambio to numeric",
        extra={"unique_tc_values": consolidated_df["Tipo de cambio"].unique().tolist()},
    )

    consolidated_df["Tipo de cambio"].unique()

    normalized_df = normalize_concepts(consolidated_df)
    logger.info(
        "normalize_concepts completed",
        extra={"rows_after": int(normalized_df.shape[0])},
    )

    try:
        normalized_df["TOTAL CONCEPTO MXN"] = np.where(
            normalized_df.get("ESTATUS METADATA", 0) == 1,
            normalized_df["TOTAL CONCEPTO"] * normalized_df["Tipo de cambio"],
            0,
        )
    except Exception as e:
        logger.exception("Error computing TOTAL CONCEPTO MXN", exc_info=e)
        raise
    # # Normalize the columns to lowercase text so that searches do not fail due to an uppercase letter or a space.
    # concepto = normalized_df["CONCEPTO"].astype(str).str.lower()
    # serie = (
    #     normalized_df["SERIE"].astype(str).str.strip().str.upper()
    # )  # Serie a mayúsculas
    # contrato = normalized_df["CONTRATO"].astype(str).str.lower()
    # iva = normalized_df["% DE IVA POR CONCEPTO"].astype(str).str.lower()
    concepto = (
        normalized_df["CONCEPTO"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

    contrato = (
        normalized_df["CONTRATO"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    serie = (
        normalized_df["SERIE"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    iva = (
        normalized_df["% DE IVA POR CONCEPTO"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # ==================================
    # IVA normalizado
    # ==================================

    iva_16 = iva.isin([
        "16",
        "16%",
        "16.0",
        "16.00"
    ])

    iva_0 = iva.isin([
        "0",
        "0%",
        "0.0",
        "0.00",
        "exento"
    ])

    # ==================================
    # Reglas
    # ==================================

    condiciones = [

        # REN ANT
        concepto.str.contains(
            r"\brenta anticipada\b",
            regex=True,
            na=False
        ) & iva_16,

        # REN ANT 0%
        concepto.str.contains(
            r"\brenta anticipada\b",
            regex=True,
            na=False
        ) & iva_0,

        # REN
        (
            concepto.str.contains(r"\brenta\b", regex=True, na=False)
            &
            ~concepto.str.contains(r"\brenta anticipada\b", regex=True, na=False)
            &
            iva_16
        ),

        # REN 0%
        (
            concepto.str.contains(r"\brenta\b", regex=True, na=False)
            &
            ~concepto.str.contains(r"\brenta anticipada\b", regex=True, na=False)
            &
            iva_0
        ),

        # VEN
        concepto.str.contains(
            r"\bventa\b",
            regex=True,
            na=False
        ) & iva_16,

        # VEN 0%
        concepto.str.contains(
            r"\bventa\b",
            regex=True,
            na=False
        ) & iva_0,

        # SEG VIDA
        concepto.str.contains(
            r"seguro de vida|prima de seguro de vida",
            regex=True,
            na=False
        ),

        # SEG
        concepto.str.contains(
            r"seguro equipo|seguro resp civil",
            regex=True,
            na=False
        ),

        # SUB
        concepto.str.contains(
            r"subsidio|comisión mercantil|comision mercantil",
            regex=True,
            na=False
        ),

        # GAS
        concepto.str.contains(
            r"gastos de administración|gastos de administracion",
            regex=True,
            na=False
        ),

        # OPC
        concepto.str.contains(
            r"opción a compra|opcion a compra",
            regex=True,
            na=False
        ),

        # OSPREY
        concepto.str.contains(
            r"osprey",
            na=False
        ),

        # PRI
        concepto.str.contains(
            r"prima seguros",
            na=False
        ),

        # REEMBOLSO
        concepto.str.contains(
            r"reembolso|daños de equipo|danos de equipo",
            regex=True,
            na=False
        ),

        # ARR
        concepto.str.contains(
            r"arrendamiento financiero",
            na=False
        ),

        # COM
        concepto.str.contains(
            r"comisión por apertura|comision por apertura",
            regex=True,
            na=False
        ),

        # DE
        serie.eq("DE"),

        # FACTORAJE
        contrato.str.contains(
            r"\bfactoraje\b",
            regex=True,
            na=False
        ),

        # SUBARR
        contrato.str.contains(
            r"arrendamiento instalaciones",
            na=False
        ),

        # UDI
        contrato.str.contains(
            r"\budi\b",
            regex=True,
            na=False
        ),
    ]
    normalized_df["IVA"] = normalized_df["IVA"].fillna("-")

    try:
        normalized_df["PREFIJO"] = np.select(condiciones, prefixes, default="OTH")
        logger.debug(
            "Prefijo assigned",
            extra={"prefixes_used": list(set(normalized_df["PREFIJO"].tolist()))},
        )
    except Exception as e:
        logger.exception("Error assigning PREFIJO", exc_info=e)
        raise
    edicom_column_names = dict(
        zip(raw_edicom_column_names, normalized_edicom_column_names)
    )
    metadata_column_names = dict(
        zip(raw_metadata_column_names, normalized_metadata_column_names)
    )
    edicom_column_names.pop("ESTATUS", None)

    normalized_column_names = edicom_column_names | metadata_column_names
    normalized_df = normalized_df.rename(columns=normalized_column_names)

    logger.info(
        "integrate_data completed", extra={"final_rows": int(normalized_df.shape[0])}
    )
    return normalized_df


def normalize_concepts(wide_df: pd.DataFrame) -> pd.DataFrame:
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
                (c for c in (f"CONCEPTO{i}", f"CONCEPT1{i}") if c in wide_df.columns),
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
    # Ensure UUID exists before sort
    if "UUID" in long_df.columns:
        long_df["priority"] = (long_df["OBSERVACIONES"] == "-").astype(int)
        df_sorted = long_df.sort_values(["UUID", "priority"]).drop(columns="priority")
    else:
        logger.warning("UUID column not present; skipping sort")
        df_sorted = long_df
    return df_sorted
