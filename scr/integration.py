"""Business-rule integration logic for consolidating source datasets and producing summaries."""

import logging
import pandas as pd
import numpy as np
from scr.models import MONTHS

# Module logger
logger = logging.getLogger(__name__)
from scr.models import (
    prefixes,
    raw_edicom_column_names,
    raw_metadata_column_names,
    normalized_edicom_column_names,
    normalized_metadata_column_names,
)

def build_prefix_conditions(consolidated_df: pd.DataFrame) -> list:
    concepto = (
        consolidated_df["CONCEPTO"].fillna("").astype(str).str.lower().str.strip()
    )

    contrato = (
        consolidated_df["CONTRATO"].fillna("").astype(str).str.lower().str.strip()
    )

    serie = consolidated_df["SERIE"].fillna("").astype(str).str.upper().str.strip()

    iva = (
        consolidated_df["% DE IVA POR CONCEPTO"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # ==================================
    # IVA normalizado
    # ==================================

    iva_16 = iva.isin(["16", "16%", "16.0", "16.00"])

    iva_0 = iva.isin(["0", "0%", "0.0", "0.00"])

    iva_exe = iva.eq("exento")

    interes = concepto.str.contains(r"interes", case=False, na=False)

    # ==================================
    # Reglas
    # ==================================
    condiciones = [
        # SUBARR
        contrato.str.contains(r"arrendamiento instalaciones|renta mobiliario", na=False),
        # REN ANT
        concepto.str.contains(r"\brenta anticipada\b|\brentas anticipadas\b", regex=True, na=False) & iva_16,
        # REN ANT 0%
        concepto.str.contains(r"\brenta anticipada\b|\brentas anticipadas\b", regex=True, na=False)
        & (iva_0 | iva_exe),
        # REN
        (
            concepto.str.contains(r"\brenta\b", regex=True, na=False)
            & ~concepto.str.contains(r"\brentas anticipadas\b", regex=True, na=False)
            & iva_16
        ),
        # REN 0%
        (
            concepto.str.contains(r"\brenta\b", regex=True, na=False)
            & ~concepto.str.contains(r"\brentas anticipadas\b", regex=True, na=False)
            & (iva_0 | iva_exe)
        ),
        # DE
        serie.eq("DE"),
        # UDI
        contrato.str.contains(r"\budi\b", regex=True, na=False),
        # VEN
        concepto.str.contains(r"\bventa\b", regex=True, na=False) & iva_16,
        # VEN 0%
        concepto.str.contains(r"\bventa\b", regex=True, na=False) & (iva_0 | iva_exe),
        # SEG VIDA
        concepto.str.contains(
            r"seguro vida|seguro de vida|prima de seguro vida|prima de seguro de vida",
            regex=True,
            na=False,
        ),
        # PRI
        concepto.str.contains(r"prima seguro", na=False),
        # SUB
        concepto.str.contains(
            r"subsidio|comisión mercantil|comision mercantil|comisiã³n mercantil", regex=True, na=False
        ),
        # GAS
        concepto.str.contains(
            r"gastos de administración|gastos de administracion", regex=True, na=False
        ),
        # OPC
        concepto.str.contains(r"opción a compra|opcion a compra|opción de compra|opcion de compra", regex=True, na=False),
        # OSPREY
        concepto.str.contains(r"osprey", na=False),
        # SEG
        concepto.str.contains(r"seguro equipo|seguro resp civil|seguro de equipo", regex=True, na=False),
        # REEMBOLSO
        concepto.str.contains(
            r"reembolso|daños de equipo|danos de equipo", regex=True, na=False
        ),
        # ARR
        concepto.str.contains(r"arrendamiento financiero", na=False),
        # COM
        concepto.str.contains(
            r"comisión por apertura|comision por apertura", regex=True, na=False
        ),
        # FACTORAJE
        contrato.str.contains(r"\bfactoraje\b", regex=True, na=False),
        # INT MOR
        concepto.str.contains(
            r"cargo por adeudo|intereses moratorios", regex=True, na=False
        ),
        # INT 16%
        concepto.str.contains(
            r"contrato\s*(?:001|002|007|008|009|015|016|018)",
            regex=True,
            case=False,
            na=False,
        )
        & iva_16
        & interes,
        # INT ARR FIN%
        concepto.str.contains(
            r"contrato\s*(?:005|006|035|305|010)", regex=True, case=False, na=False
        )
        & iva_16
        & interes,
        # INT 0%
        interes
        & concepto.str.contains(
            r"contrato\s*(?:006|009)", regex=True, case=False, na=False
        )
        & iva_0
        & interes,
        # INT EX<E%
        (
            (
                concepto.str.contains(
                    r"interes plan piso", regex=True, case=False, na=False
                )
                | (
                    interes
                    & concepto.str.contains(
                        r"contrato\s*:?\s*(?:001|002|007|015|016|018|033|302|307)",
                        regex=True,
                        case=False,
                        na=False,
                    )
                )
                | concepto.str.contains(r"prepago", regex=True, case=False, na=False)
            )
            & iva_exe
        ),
        
    ]
    return condiciones

def build_conciliation_conditions(consolidated_df: pd.DataFrame) -> tuple[list, list]:
    condiciones = [
            consolidated_df["UUID"].notna()
            & consolidated_df["Uuid"].notna()
            & consolidated_df["RFC_EMISOR"].notna(),
            consolidated_df["UUID"].notna()
            & consolidated_df["Uuid"].notna()
            & consolidated_df["RFC_EMISOR"].notna()
            & consolidated_df["TOTAL CONCEPTO"]
            != consolidated_df["TOTAL_CONCEPTO"],
            consolidated_df["UUID"].notna()
            & consolidated_df["Uuid"].notna()
            & consolidated_df["RFC_EMISOR"].isna(),
            consolidated_df["UUID"].notna()
            & consolidated_df["Uuid"].isna()
            & consolidated_df["RFC_EMISOR"].notna(),
            consolidated_df["UUID"].notna()
            & consolidated_df["Uuid"].isna()
            & consolidated_df["RFC_EMISOR"].isna(),
        ]
    valores = [
        "Conciliado Total",
        "Conciliado Total con Diferencia",
        "Conciliado Metadata",
        "Conciliado Facturas",
        "Sin Conciliar",
    ]
    return condiciones, valores

def integrate_data(consolidated_df: pd.DataFrame) -> pd.DataFrame:
    """Apply integration rules and enrich the consolidated DataFrame with status, prefix, and reconciliation fields.

    This function evaluates source comparisons between Edicom, metadata, and CFDI
    data to derive business status flags, conversion values, and a normalized
    prefix for each record.

    Args:
        consolidated_df: A merged DataFrame containing the preprocessed source rows.

    Returns:
        A DataFrame enriched with integration outcomes and normalized columns.
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

    consolidated_df["Tipo de cambio"] = pd.to_numeric(
        consolidated_df["TIPO_CAMBIO"], errors="coerce"
    )
    logger.debug(
        "Converted Tipo de cambio to numeric",
        extra={"unique_tc_values": consolidated_df["TIPO_CAMBIO"].unique().tolist()},
    )

    consolidated_df["Tipo de cambio"].unique()

    try:
        consolidated_df["TOTAL CONCEPTO MXN"] = np.where(
            consolidated_df.get("ESTATUS METADATA", 0) == 1,
            consolidated_df["TOTAL CONCEPTO"] * consolidated_df["Tipo de cambio"],
            0,
        )
        consolidated_df["TOTAL_EDICOM_MXN"] = (
            consolidated_df["TOTAL"] * consolidated_df["Tipo de cambio"]
        )
        consolidated_df["TOTAL_METADATA_MXN"] = (
            consolidated_df["Monto"] * consolidated_df["Tipo de cambio"]
        )
    except Exception as e:
        logger.exception("Error computing TOTAL CONCEPTO MXN", exc_info=e)
        raise
    prefix_conditions = build_prefix_conditions(consolidated_df)
    consolidated_df["IVA"] = consolidated_df["IVA"].fillna("-")

    try:
        consolidated_df["PREFIJO"] = np.select(prefix_conditions, prefixes, default="OTH")
        logger.debug(
            "Prefijo assigned",
            extra={"prefixes_used": list(set(consolidated_df["PREFIJO"].tolist()))},
        )
    except Exception as e:
        logger.exception("Error assigning PREFIJO", exc_info=e)
        raise

    conciliation_conditions, conciliation_values = build_conciliation_conditions(consolidated_df)


    consolidated_df["IDENTIFICADO"] = np.select(conciliation_conditions, conciliation_values, default="")

    # Ensure UUID exists before sort
    if "UUID" in consolidated_df.columns:
        consolidated_df["priority"] = (consolidated_df["OBSERVACIONES"] == "-").astype(
            int
        )
        df_sorted = consolidated_df.sort_values(
            ["RFC_EMISOR", "Mes", "Día", "UUID", "priority"]
        ).drop(columns="priority")
    else:
        logger.warning("UUID column not present; skipping sort")
        df_sorted = consolidated_df
    edicom_column_names = dict(
        zip(raw_edicom_column_names, normalized_edicom_column_names)
    )
    metadata_column_names = dict(
        zip(raw_metadata_column_names, normalized_metadata_column_names)
    )
    edicom_column_names.pop("ESTATUS", None)

    normalized_column_names = edicom_column_names | metadata_column_names
    df_sorted = df_sorted.rename(columns=normalized_column_names)

    logger.info(
        "integrate_data completed", extra={"final_rows": int(df_sorted.shape[0])}
    )
    return df_sorted

def get_summary(
    normalized_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build monthly summaries for Edicom, metadata, and CFDI results.

    Args:
        normalized_df: The consolidated DataFrame produced by the integration stage.

    Returns:
        Three DataFrames containing summary statistics for Edicom, metadata, and invoice data.
    """
    edicom_base = normalized_df.groupby(["Periodo", "UUID"], as_index=False).agg(
        RFC_EMISOR=("RFC_EMISOR", "first"),
        EDICOM_TOTAL=("TOTAL", "first"),
        ESTATUS_EDICOM=("ESTATUS_EDICOM", "first")
    )
    metadata_base = transformed_metadata_info_df.groupby(["Periodo", "Uuid"], as_index=False).agg(
            RFC_EMISOR=("RfcEmisor", "first"),
            METADATA_TOTAL=("Monto", "first"),
            ESTATUS_METADATA=("FechaCancelacion", "first"),
        )
    cfdi_base = transformed_cfdi_info_df.groupby(["FECHA_PERIODO", "UUID"], as_index=False).agg(
            RFC_EMISOR=("RFC_EMISOR", "first"),
            FACTURA_TOTAL=("TOTAL_FACTURA", "first"),
            ESTATUS_FACTURA=("TIPO_ESTATUS", "first"),
        )

    edicom_resumen = (
        edicom_base.groupby(["Periodo", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": x["ESTATUS_EDICOM"].eq("Vigente").sum(),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_EDICOM"].eq("Vigente"), "EDICOM_TOTAL"
                    ].sum(),
                    "FACTURAS_CANCELADAS": x["ESTATUS_EDICOM"].eq("Cancelado").sum(),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_EDICOM"].eq("Cancelado"), "EDICOM_TOTAL"
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    edicom_resumen["Periodo"] = pd.Categorical(
        edicom_resumen["Periodo"],
        categories=MONTHS,
        ordered=True
    )

    edicom_resumen = (
        edicom_resumen
        .sort_values(["RFC_EMISOR", "Periodo"])
        .reset_index(drop=True)
        )
    
    metadata_resumen = (
        metadata_base.groupby(["Periodo", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": x["ESTATUS_METADATA"].isna().sum(),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_METADATA"].isna(), "METADATA_TOTAL"
                    ].sum(),
                    "FACTURAS_CANCELADAS": x["ESTATUS_METADATA"].notna().sum(),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_METADATA"].notna(), "METADATA_TOTAL"
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    metadata_resumen["Periodo"] = pd.Categorical(
        metadata_resumen["Periodo"],
        categories=MONTHS,
        ordered=True
    )

    metadata_resumen = (
        metadata_resumen
        .sort_values(["RFC_EMISOR", "Periodo"])
        .reset_index(drop=True)
        )
    
    factura_resumen = (
        cfdi_base.groupby(["FECHA_PERIODO", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": x["ESTATUS_FACTURA"].eq("Vigente").sum(),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_FACTURA"].eq("Vigente"), "FACTURA_TOTAL"
                    ].sum(),
                    "FACTURAS_CANCELADAS": (
                        x["ESTATUS_FACTURA"].eq("Cancelados")
                    ).sum(),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_FACTURA"].eq("Cancelados"), "FACTURA_TOTAL"
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    factura_resumen["FECHA_PERIODO"] = pd.Categorical(
        factura_resumen["FECHA_PERIODO"],
        categories=MONTHS,
        ordered=True
    )

    factura_resumen = (
        factura_resumen
        .sort_values(["RFC_EMISOR", "FECHA_PERIODO"])
        .reset_index(drop=True)
        )

    factura_resumen = factura_resumen.rename(columns={"FECHA_PERIODO":"Periodo"})
    metadata_resumen = metadata_resumen.rename(columns={"Uuid":"UUID"})


    column_order = [
        "RFC_EMISOR",
        "PERIODO",
        "FACTURAS_VIGENTES",
        "TOTAL_VIGENTES",
        "FACTURAS_CANCELADAS",
        "TOTAL_CANCELADAS",
    ]

    for resumen in [edicom_resumen, metadata_resumen, factura_resumen]:
        resumen["TOTAL_VIGENTES"] = (
            resumen["TOTAL_VIGENTES"].round(0).astype(int)
        )

        resumen["TOTAL_CANCELADAS"] = (
            resumen["TOTAL_CANCELADAS"].round(0).astype(int)
        )

        resumen["FACTURAS_CANCELADAS"] = (
            resumen["FACTURAS_CANCELADAS"].round(0).astype(int)
        )

        resumen["FACTURAS_VIGENTES"] = (
            resumen["FACTURAS_VIGENTES"].round(0).astype(int)
        )

        resumen.loc[len(resumen)] = {
            "Periodo": "TOTAL",
            "FACTURAS_VIGENTES": resumen["FACTURAS_VIGENTES"].sum(),
            "TOTAL_VIGENTES": resumen["TOTAL_VIGENTES"].sum(),
            "FACTURAS_CANCELADAS": resumen["FACTURAS_CANCELADAS"].sum(),
            "TOTAL_CANCELADAS": resumen["TOTAL_CANCELADAS"].sum(),
        }
        resumen.rename(
            columns={"Periodo": "PERIODO"},
            inplace=True
            )

    edicom_resumen = edicom_resumen[column_order]
    edicom_resumen[:] = edicom_resumen[column_order]
    metadata_resumen = metadata_resumen[column_order]
    metadata_resumen[:] = metadata_resumen[column_order]
    factura_resumen = factura_resumen[column_order]
    factura_resumen[:] = factura_resumen[column_order]
    return edicom_resumen, metadata_resumen, factura_resumen

def get_missing_systems(row):
    missing = []

    if not row["FACTURAS"]:
        missing.append("FACTURAS")

    if not row["EDICOM"]:
        missing.append("EDICOM")

    if not row["METADATA"]:
        missing.append("METADATA")

    return ", ".join(missing)


def get_present_systems(row):
    present = []

    if row["FACTURAS"]:
        present.append("FACTURAS")

    if row["EDICOM"]:
        present.append("EDICOM")

    if row["METADATA"]:
        present.append("METADATA")

    return ", ".join(present)

def get_differences(
    consolidated_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Identify differences between the consolidated DataFrame and the source datasets.

    Args:
        consolidated_df: The consolidated DataFrame.
        transformed_metadata_info_df: Transformed metadata rows.
        transformed_cfdi_info_df: Transformed CFDI rows.

    Returns:
        A DataFrame highlighting the differences.
    """
    cfdis_uuids = set(transformed_cfdi_info_df["UUID"].dropna())
    edicom_uuids = set(consolidated_df["UUID"].dropna())
    metadata_uuids = set(transformed_metadata_info_df["Uuid"].dropna())

    all_uuids = cfdis_uuids | edicom_uuids | metadata_uuids

    differences = pd.DataFrame({
        "UUID": list(all_uuids)
    })

    differences["FACTURAS"] = differences["UUID"].isin(cfdis_uuids)
    differences["EDICOM"] = differences["UUID"].isin(edicom_uuids)
    differences["METADATA"] = differences["UUID"].isin(
        metadata_uuids
    )

    differences["TOTAL_PRESENTE"] = (
        differences["FACTURAS"].astype(int)
        + differences["EDICOM"].astype(int)
        + differences["METADATA"].astype(int)
    )

    # Me quedo solamente con los que NO están en los 3
    differences = differences[
        differences["TOTAL_PRESENTE"] < 3
    ].copy()


    differences["PRESENTE_EN"] = differences.apply(
        get_present_systems,
        axis=1,
    )

    differences["FALTA_EN"] = differences.apply(
        get_missing_systems,
        axis=1,
    )

    differences["TIPO"] = differences["TOTAL_PRESENTE"].map({
        2: "PRESENTE EN 2 DE 3",
        1: "PRESENTE SOLO EN 1"
    })

    differences = differences[
        [
            "UUID",
            "TIPO",
            "PRESENTE_EN",
            "FALTA_EN",
            "FACTURAS",
            "EDICOM",
            "METADATA",
        ]
    ].sort_values(
        ["TIPO", "UUID"]
    )
    return differences



def join_dfs(
    transformed_edicom_info_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join Edicom, metadata, and CFDI data using a staged matching strategy.

    The function first performs an exact merge, then falls back to tolerance-based
    matching and UUID-based matching to reconcile records from the different sources.

    Args:
        transformed_edicom_info_df: Normalized Edicom rows.
        transformed_metadata_info_df: Normalized metadata rows.
        transformed_cfdi_info_df: Normalized CFDI rows.

    Returns:
        A merged DataFrame representing the reconciled dataset.
    """
    metadata_unique = transformed_metadata_info_df.drop_duplicates(
        subset=["Uuid"], keep="first"
    )
    consolidated_df = pd.merge(
        transformed_edicom_info_df,
        metadata_unique,
        left_on="UUID",
        right_on="Uuid",
        how="left",
        suffixes=("_EDICOM", "_METADATA"),
    )
    # =====================================================
    # 1. Phase 1: Exact merge
    # =====================================================

    left = consolidated_df.copy()
    right = transformed_cfdi_info_df.copy()
    left["_row_id"] = left.index
    left = left.sort_values(["UUID", "TOTAL CONCEPTO", "_row_id"])
    right = right.sort_values(["UUID", "TOTAL_CONCEPTO", "CONCEPTO_ID"])
    left["_seq"] = left.groupby(["UUID", "TOTAL CONCEPTO"]).cumcount()
    right["_seq"] = right.groupby(["UUID", "TOTAL_CONCEPTO"]).cumcount()

    exact_matches = left.merge(
        right,
        left_on=["UUID", "TOTAL CONCEPTO", "_seq"],
        right_on=["UUID", "TOTAL_CONCEPTO", "_seq"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    matched_exact = exact_matches[exact_matches["_merge"] == "both"].copy()

    # =====================================================
    # 2. Phase 2: Match with tolerance
    # =====================================================

    unmatched_edicom = exact_matches[exact_matches["_merge"] == "left_only"].copy()

    unmatched_edicom = unmatched_edicom.loc[
        :,
        ~(
            unmatched_edicom.columns.isin(
                [c for c in transformed_cfdi_info_df.columns if c != "UUID"]
            )
            | unmatched_edicom.columns.isin(["_seq", "_row_id", "_merge"])
        ),
    ]

    print(f"Matches exactos: {len(matched_exact)}")

    used_cfdi_keys = set(
        zip(
            matched_exact["UUID"],
            matched_exact["TOTAL_CONCEPTO"],
        )
    )

    available_cfdi = transformed_cfdi_info_df[
        ~transformed_cfdi_info_df.apply(
            lambda r: (r["UUID"], r["TOTAL_CONCEPTO"]) in used_cfdi_keys,
            axis=1,
        )
    ].copy()

    # Crear identificador único para cada factura disponible
    available_cfdi = available_cfdi.reset_index(drop=True)
    available_cfdi["CFDI_ID"] = available_cfdi.index

    # Regenerar candidatos para incluir CFDI_ID
    candidates = unmatched_edicom.merge(
        available_cfdi,
        on="UUID",
        suffixes=("_left", "_right"),
    )

    candidates["diff"] = (
        candidates["TOTAL CONCEPTO"] - candidates["TOTAL_CONCEPTO"]
    ).abs()

    candidates = candidates[candidates["diff"] <= 1].copy()

    # Mejor match primero
    candidates = candidates.sort_values("diff")

    used_conceptos = set()
    used_facturas = set()
    selected_rows = []

    for _, row in candidates.iterrows():

        concepto_id = row["CONCEPTO_ID"]
        factura_id = row["CFDI_ID"]

        if concepto_id in used_conceptos:
            continue

        if factura_id in used_facturas:
            continue

        selected_rows.append(row)

        used_conceptos.add(concepto_id)
        used_facturas.add(factura_id)

    matched_diff = pd.DataFrame(selected_rows)

    matched_keys = set(zip(matched_diff["UUID"], matched_diff["TOTAL CONCEPTO"]))

    unmatched_diff = unmatched_edicom[
        ~unmatched_edicom.apply(
            lambda r: (r["UUID"], r["TOTAL CONCEPTO"]) in matched_keys, axis=1
        )
    ].copy()

    print(f"Matches por tolerancia: {len(matched_diff)}")

    # =====================================================
    # 3. Phase 3: Only by UUID
    # =====================================================

    # CFDIs usados en la fase de tolerancia
    used_uuids_diff = set(matched_diff["UUID"])

    # CFDIs todavía disponibles
    remaining_cfdi = available_cfdi[
        ~available_cfdi["UUID"].isin(used_uuids_diff)
    ].copy()

    # UUIDs que tienen exactamente 1 registro disponible
    unique_uuid_cfdi = remaining_cfdi.groupby("UUID").filter(lambda x: len(x) == 1)

    # Match solo por UUID
    uuid_only_matches = unmatched_diff.merge(
        unique_uuid_cfdi,
        on="UUID",
        how="inner",
        suffixes=("_left", "_right"),
    )

    print(f"Matches solo UUID: {len(uuid_only_matches)}")

    # No conciliados definitivos
    unmatched_definitive = unmatched_diff[
        ~unmatched_diff["UUID"].isin(uuid_only_matches["UUID"])
    ].copy()

    print(f"No conciliados definitivos: {len(unmatched_definitive)}")

    # =====================================================
    # 4. Final DataFrame
    # =====================================================

    final_df = pd.concat(
        [
            matched_exact.drop(columns=["_merge", "_seq", "_row_id"]),
            matched_diff.drop(columns=["diff"]),
            uuid_only_matches,
            unmatched_definitive,
        ],
        ignore_index=True,
    )
    return final_df
