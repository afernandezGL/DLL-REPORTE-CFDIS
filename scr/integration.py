"""Business-rule integration logic for consolidating source datasets and producing summaries."""

import logging

import numpy as np
import pandas as pd

from scr.models import (
    MONTHS,
    DifferencesResult,
    DifferencesUUIDResult,
    SummaryResult,
    TransformedResult,
)

# Module logger
logger = logging.getLogger(__name__)
from scr.models import (
    normalized_edicom_column_names,
    normalized_metadata_column_names,
    prefixes,
    raw_edicom_column_names,
    raw_metadata_column_names,
)


def build_prefix_conditions(consolidated_df: pd.DataFrame) -> list:
    """Build the prefix-matching conditions used to classify each invoice row.

    Args:
        consolidated_df: Integrated dataframe that contains the fields needed for
            prefix detection, such as concept text, contract, series, and IVA.

    Returns:
        A list of boolean masks describing each prefix rule.
    """
    receptor_name = (
        consolidated_df["RECEPTOR NOMBRE"].fillna("").astype(str).str.strip()
    )

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
        contrato.str.contains(
            r"arrendamiento instalaciones|renta mobiliario", na=False
        ),
        # REN ANT
        concepto.str.contains(
            r"\brenta anticipada\b|\brentas anticipadas\b", regex=True, na=False
        )
        & iva_16,
        # REN ANT 0%
        concepto.str.contains(
            r"\brenta anticipada\b|\brentas anticipadas\b", regex=True, na=False
        )
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
            r"subsidio|comisión mercantil|comision mercantil",
            regex=True,
            na=False,
        ),
        # GAS
        concepto.str.contains(
            r"gastos de administración|gastos de administracion", regex=True, na=False
        ),
        # OPC
        concepto.str.contains(
            r"opción a compra|opcion a compra|opción de compra|opcion de compra",
            regex=True,
            na=False,
        ),
        # OSPREY
        concepto.str.contains(r"osprey", na=False),
        # SEG
        concepto.str.contains(
            r"seguro equipo|seguro resp civil|seguro de equipo", regex=True, na=False
        ),
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
        receptor_name.str.contains(
            r"GE SISTEMAS MEDICOS DE MEXICO", regex=True, na=False
        )
        & concepto.str.contains(
            r"comisiã³n mercantil",
            regex=True,
            na=False,
        ),
    ]
    return condiciones


def build_conciliation_conditions(consolidated_df: pd.DataFrame) -> tuple[list, list]:
    """Build the status conditions that describe how the sources reconcile.

    Args:
        consolidated_df: Integrated dataframe containing UUID, metadata, RFC, and
            concept totals from the comparison sources.

    Returns:
        A tuple with the conditions and their corresponding labels.
    """
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
    """Apply integration rules and enrich the consolidated DataFrame."""

    logger.info(
        "Starting integrate_data",
        extra={"rows": int(consolidated_df.shape[0])},
    )

    consolidated_df = integrate_status(consolidated_df)
    consolidated_df = calculate_currency_fields(consolidated_df)
    consolidated_df = assign_prefix(consolidated_df)
    consolidated_df = assign_conciliation(consolidated_df)
    consolidated_df = finalize_dataframe(consolidated_df)

    logger.info(
        "integrate_data completed",
        extra={"final_rows": int(consolidated_df.shape[0])},
    )

    return consolidated_df


def integrate_status(
    consolidated_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare Edicom and metadata status values and normalize the result column.

    Args:
        consolidated_df: Dataframe containing the status values to compare.

    Returns:
        The same dataframe with an internal report status column and a normalized
        ESTATUS column.
    """

    try:
        consolidated_df["ESTATUS REPORTE INTERNO VS METADATA"] = np.where(
            consolidated_df["ESTATUS_EDICOM"].str.upper()
            == consolidated_df["ESTATUS_METADATA"].str.upper(),
            1,
            0,
        )
    except Exception:
        logger.exception("Error computing ESTATUS REPORTE INTERNO VS METADATA")
        raise

    if "ESTATUS_METADATA" in consolidated_df.columns:
        consolidated_df = consolidated_df.rename(
            columns={"ESTATUS_METADATA": "ESTATUS"}
        )
        logger.debug("Renamed ESTATUS_METADATA to ESTATUS")
    else:
        logger.warning("ESTATUS_METADATA column not found; ESTATUS rename skipped")

    return consolidated_df


def calculate_currency_fields(
    consolidated_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate the converted monetary values for the consolidated records.

    Args:
        consolidated_df: Integrated dataframe that includes amounts and the FX rate.

    Returns:
        The dataframe enriched with the MXN-equivalent cash fields.
    """

    consolidated_df["Tipo de cambio"] = pd.to_numeric(
        consolidated_df["TIPO_CAMBIO"],
        errors="coerce",
    )

    logger.debug(
        "Converted Tipo de cambio to numeric",
        extra={"unique_tc_values": consolidated_df["TIPO_CAMBIO"].unique().tolist()},
    )

    try:
        consolidated_df["TOTAL CONCEPTO MXN"] = np.where(
            consolidated_df.get("ESTATUS METADATA", 0) == 1,
            consolidated_df["TOTAL CONCEPTO"] * consolidated_df["Tipo de cambio"],
            0,
        )

        consolidated_df["TOTAL_EDICOM_MXN"] = (
            consolidated_df["TOTAL"] * consolidated_df["Tipo de cambio"]
        )

        consolidated_df["SUBTOTAL_EDICOM_MXN"] = (
            consolidated_df["SUBTOTAL"] * consolidated_df["Tipo de cambio"]
        )

    except Exception:
        logger.exception("Error computing currency amounts")
        raise

    return consolidated_df


def assign_prefix(
    consolidated_df: pd.DataFrame,
) -> pd.DataFrame:
    """Assign the prefix category for each concept based on business rules.

    Args:
        consolidated_df: Integrated dataframe containing invoice concepts and IVA.

    Returns:
        The dataframe with a PREFIJO column assigned using the prefix masks.
    """

    consolidated_df["IVA"] = consolidated_df["IVA"].fillna("-")

    prefix_conditions = build_prefix_conditions(consolidated_df)

    try:
        consolidated_df["PREFIJO"] = np.select(
            prefix_conditions,
            prefixes,
            default="OTH",
        )

        logger.debug(
            "Prefijo assigned",
            extra={"prefixes_used": list(set(consolidated_df["PREFIJO"].tolist()))},
        )

    except Exception:
        logger.exception("Error assigning PREFIJO")
        raise

    return consolidated_df


def assign_conciliation(
    consolidated_df: pd.DataFrame,
) -> pd.DataFrame:
    """Assign the reconciliation label that explains source coverage.

    Args:
        consolidated_df: Integrated dataframe to evaluate against the reconciliation
            conditions.

    Returns:
        The dataframe with the IDENTIFICADO column populated.
    """

    (
        conciliation_conditions,
        conciliation_values,
    ) = build_conciliation_conditions(consolidated_df)

    consolidated_df["IDENTIFICADO"] = np.select(
        conciliation_conditions,
        conciliation_values,
        default="",
    )

    return consolidated_df


def finalize_dataframe(
    consolidated_df: pd.DataFrame,
) -> pd.DataFrame:
    """Sort and rename the consolidated dataframe into its final export shape.

    Args:
        consolidated_df: Integrated dataframe before final column naming.

    Returns:
        The dataframe sorted by RFC, month, day, UUID and renamed to the final
        column schema.
    """

    if "UUID" in consolidated_df.columns:
        consolidated_df["priority"] = (consolidated_df["OBSERVACIONES"] == "-").astype(
            int
        )

        df_sorted = consolidated_df.sort_values(
            [
                "RFC_EMISOR",
                "Mes",
                "Día",
                "UUID",
                "priority",
            ]
        ).drop(columns="priority")

    else:
        logger.warning("UUID column not present; skipping sort")
        df_sorted = consolidated_df

    edicom_column_names = dict(
        zip(
            raw_edicom_column_names,
            normalized_edicom_column_names,
        )
    )

    metadata_column_names = dict(
        zip(
            raw_metadata_column_names,
            normalized_metadata_column_names,
        )
    )

    edicom_column_names.pop("ESTATUS", None)

    normalized_column_names = edicom_column_names | metadata_column_names

    df_sorted = df_sorted.rename(columns=normalized_column_names)

    return df_sorted


def get_subtotal_differences(
    consolidated_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Identify rows where the subtotal values differ between Edicom and metadata sources.

    Args:
        consolidated_df: The integrated DataFrame containing both Edicom and metadata data.

    Returns:
        A tuple containing:
        - subtotal_differences: DataFrame with all rows and their subtotal differences.
        - relevant_subtotal_differences: DataFrame with rows where the differences exceed the threshold.
    """
    subtotal_differences = consolidated_df.copy()
    subtotal_differences = subtotal_differences.drop_duplicates(
        subset=["UUID"],
        keep="first",
    )
    subtotal_differences["diferencia MXN"] = (
        (
            subtotal_differences["SUBTOTAL_EDICOM_MXN"].fillna(0)
            - subtotal_differences["SUBTOTAL_FACTURA_MXN"].fillna(0)
        )
        .abs()
        .round(2)
    )
    subtotal_differences["diferencia ORIGEN"] = (
        (
            subtotal_differences["TOTAL"].fillna(0)
            - subtotal_differences["TOTAL_FACTURA"].fillna(0)
        )
        .abs()
        .round(2)
    )
    subtotal_differences = subtotal_differences[
        [
            "UUID",
            "SUBTOTAL",
            "TOTAL",
            "ESTATUS_EDICOM",
            "TOTAL METADATA",
            "ESTATUS",
            "SUBTOTAL_FACTURA",
            "TOTAL_FACTURA",
            "TIPO_ESTATUS",
            "diferencia ORIGEN",
            "SUBTOTAL_EDICOM_MXN",
            "SUBTOTAL_FACTURA_MXN",
            "diferencia MXN",
        ]
    ]
    relevant_subtotal_differences = subtotal_differences[
        (subtotal_differences["diferencia MXN"] > 1)
        | (subtotal_differences["diferencia ORIGEN"] > 1)
    ]
    return subtotal_differences, relevant_subtotal_differences


def get_summary(
    normalized_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> SummaryResult:
    """Create the summary object for the three reporting sources.

    Args:
        normalized_df: Consolidated Edicom dataframe.
        transformed_metadata_info_df: Transformed metadata dataframe.
        transformed_cfdi_info_df: Transformed CFDI dataframe.

    Returns:
        A SummaryResult containing the Edicom, metadata, and CFDI summaries.
    """

    column_order = [
        "RFC_EMISOR",
        "PERIODO",
        "FACTURAS_VIGENTES",
        "TOTAL_VIGENTES",
        "FACTURAS_CANCELADAS",
        "TOTAL_CANCELADAS",
    ]

    edicom_resumen = build_edicom_summary(normalized_df)[column_order]

    metadata_resumen = build_metadata_summary(transformed_metadata_info_df)[
        column_order
    ]

    factura_resumen = build_factura_summary(transformed_cfdi_info_df)[column_order]

    return SummaryResult(
        edicom=edicom_resumen,
        metadata=metadata_resumen,
        factura=factura_resumen,
    )


def build_edicom_summary(
    normalized_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize Edicom status totals by issuer and month.

    Args:
        normalized_df: Consolidated dataframe with Edicom records.

    Returns:
        A dataframe with counts and totals for current and canceled invoices.
    """

    edicom_base = normalized_df.groupby(
        ["Periodo", "UUID"],
        as_index=False,
    ).agg(
        RFC_EMISOR=("RFC_EMISOR", "first"),
        EDICOM_TOTAL=("TOTAL", "first"),
        ESTATUS_EDICOM=("ESTATUS_EDICOM", "first"),
    )

    resumen = (
        edicom_base.groupby(["Periodo", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": (x["ESTATUS_EDICOM"].eq("Vigente").sum()),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_EDICOM"].eq("Vigente"),
                        "EDICOM_TOTAL",
                    ].sum(),
                    "FACTURAS_CANCELADAS": (x["ESTATUS_EDICOM"].eq("Cancelado").sum()),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_EDICOM"].eq("Cancelado"),
                        "EDICOM_TOTAL",
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    resumen["Periodo"] = pd.Categorical(
        resumen["Periodo"],
        categories=MONTHS,
        ordered=True,
    )

    resumen = resumen.sort_values(["RFC_EMISOR", "Periodo"]).reset_index(drop=True)

    return finalize_summary(resumen)


def build_metadata_summary(
    transformed_metadata_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize metadata totals by issuer and month.

    Args:
        transformed_metadata_info_df: Metadata dataframe after transformation.

    Returns:
        A dataframe with metadata counts and totals by status.
    """

    metadata_base = transformed_metadata_info_df.groupby(
        ["Periodo", "Uuid"],
        as_index=False,
    ).agg(
        RFC_EMISOR=("RfcEmisor", "first"),
        METADATA_TOTAL=("Monto", "first"),
        ESTATUS_METADATA=("FechaCancelacion", "first"),
    )

    resumen = (
        metadata_base.groupby(["Periodo", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": (x["ESTATUS_METADATA"].isna().sum()),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_METADATA"].isna(),
                        "METADATA_TOTAL",
                    ].sum(),
                    "FACTURAS_CANCELADAS": (x["ESTATUS_METADATA"].notna().sum()),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_METADATA"].notna(),
                        "METADATA_TOTAL",
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    resumen["Periodo"] = pd.Categorical(
        resumen["Periodo"],
        categories=MONTHS,
        ordered=True,
    )

    resumen = resumen.sort_values(["RFC_EMISOR", "Periodo"]).reset_index(drop=True)

    return finalize_summary(resumen)


def build_factura_summary(
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize CFDI status totals by issuer and month.

    Args:
        transformed_cfdi_info_df: CFDI dataframe after transformation.

    Returns:
        A dataframe with invoice counts and totals segmented by status.
    """

    cfdi_base = transformed_cfdi_info_df.groupby(
        ["FECHA_PERIODO", "UUID"],
        as_index=False,
    ).agg(
        RFC_EMISOR=("RFC_EMISOR", "first"),
        FACTURA_TOTAL=("TOTAL_FACTURA", "first"),
        ESTATUS_FACTURA=("TIPO_ESTATUS", "first"),
    )

    resumen = (
        cfdi_base.groupby(["FECHA_PERIODO", "RFC_EMISOR"])
        .apply(
            lambda x: pd.Series(
                {
                    "FACTURAS_VIGENTES": (x["ESTATUS_FACTURA"].eq("Vigente").sum()),
                    "TOTAL_VIGENTES": x.loc[
                        x["ESTATUS_FACTURA"].eq("Vigente"),
                        "FACTURA_TOTAL",
                    ].sum(),
                    "FACTURAS_CANCELADAS": (
                        x["ESTATUS_FACTURA"].eq("Cancelados").sum()
                    ),
                    "TOTAL_CANCELADAS": x.loc[
                        x["ESTATUS_FACTURA"].eq("Cancelados"),
                        "FACTURA_TOTAL",
                    ].sum(),
                }
            )
        )
        .reset_index()
    )

    resumen["FECHA_PERIODO"] = pd.Categorical(
        resumen["FECHA_PERIODO"],
        categories=MONTHS,
        ordered=True,
    )

    resumen = resumen.sort_values(["RFC_EMISOR", "FECHA_PERIODO"]).reset_index(
        drop=True
    )

    resumen = resumen.rename(columns={"FECHA_PERIODO": "Periodo"})

    return finalize_summary(resumen)


def finalize_summary(
    resumen: pd.DataFrame,
) -> pd.DataFrame:
    """Finalize summary totals by converting values and adding the overall total row.

    Args:
        resumen: Summary dataframe before the final aggregation row is added.

    Returns:
        The summary dataframe with integer totals and a TOTAL row.
    """

    resumen["TOTAL_VIGENTES"] = resumen["TOTAL_VIGENTES"].round(0).astype(int)

    resumen["TOTAL_CANCELADAS"] = resumen["TOTAL_CANCELADAS"].round(0).astype(int)

    resumen["FACTURAS_CANCELADAS"] = resumen["FACTURAS_CANCELADAS"].round(0).astype(int)

    resumen["FACTURAS_VIGENTES"] = resumen["FACTURAS_VIGENTES"].round(0).astype(int)

    resumen.loc[len(resumen)] = {
        "Periodo": "TOTAL",
        "FACTURAS_VIGENTES": resumen["FACTURAS_VIGENTES"].sum(),
        "TOTAL_VIGENTES": resumen["TOTAL_VIGENTES"].sum(),
        "FACTURAS_CANCELADAS": resumen["FACTURAS_CANCELADAS"].sum(),
        "TOTAL_CANCELADAS": resumen["TOTAL_CANCELADAS"].sum(),
    }

    resumen = resumen.rename(columns={"Periodo": "PERIODO"})

    return resumen


def get_missing_systems(row):
    """Return the source systems missing for a given comparison row.

    Args:
        row: A row from a comparison dataframe.

    Returns:
        A comma-separated list of source systems that are absent.
    """
    missing = []

    if not row["FACTURAS"]:
        missing.append("FACTURAS")

    if not row["EDICOM"]:
        missing.append("EDICOM")

    if not row["METADATA"]:
        missing.append("METADATA")

    return ", ".join(missing)


def get_present_systems(row):
    """Return the source systems that are present for a given comparison row.

    Args:
        row: A row from a comparison dataframe.

    Returns:
        A comma-separated list of source systems that are present.
    """
    present = []

    if row["FACTURAS"]:
        present.append("FACTURAS")

    if row["EDICOM"]:
        present.append("EDICOM")

    if row["METADATA"]:
        present.append("METADATA")

    return ", ".join(present)


def get_differences(
    consolidated_df: pd.DataFrame, transformed_results: TransformedResult
) -> DifferencesResult:
    """Identify differences between the consolidated DataFrame and the source datasets.

    Args:
        consolidated_df: The consolidated DataFrame.
        transformed_results: TransformedResult containing filtered metadata and CFDI rows.

    Returns:
        A tuple of DataFrames highlighting the differences:
        (differences, edicom_df, metadata_df, facturas_df, subtotal_differences)
    """
    uuid_differences = build_uuid_differences(
        consolidated_df,
        transformed_results.filtered_metadata,
        transformed_results.factura,
    )
    uuid_differences_result = DifferencesUUIDResult(
        edicom=uuid_differences.loc[uuid_differences["EDICOM"], "UUID"].tolist(),
        metadata=uuid_differences.loc[uuid_differences["METADATA"], "UUID"].tolist(),
        facturas=uuid_differences.loc[uuid_differences["FACTURAS"], "UUID"].tolist(),
    )
    metadata_missings = build_metadata_missings(
        consolidated_df,
        uuid_differences_result.metadata,
        transformed_results.filtered_metadata,
        transformed_results.factura,
    )

    subtotal_differences, relevant_subtotal_differences = get_subtotal_differences(
        metadata_missings
    )
    return DifferencesResult(
        uuid=uuid_differences,
        subtotal=subtotal_differences,
        relevant_uuid=uuid_differences_result,
        relevant_subtotal=relevant_subtotal_differences,
    )


def build_uuid_differences(
    consolidated_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Identify the UUIDs that are missing from one or more source systems.

    Args:
        consolidated_df: Consolidated dataframe with Edicom rows.
        transformed_metadata_info_df: Metadata rows for the current period.
        transformed_cfdi_info_df: CFDI rows for the current period.

    Returns:
        A dataframe that flags which systems include each UUID.
    """
    cfdis_uuids = set(transformed_cfdi_info_df["UUID"].dropna())
    edicom_uuids = set(consolidated_df["UUID"].dropna())
    metadata_uuids = set(transformed_metadata_info_df["Uuid"].dropna())

    all_uuids = cfdis_uuids | edicom_uuids | metadata_uuids

    differences = pd.DataFrame({"UUID": list(all_uuids)})

    differences["FACTURAS"] = differences["UUID"].isin(cfdis_uuids)
    differences["EDICOM"] = differences["UUID"].isin(edicom_uuids)
    differences["METADATA"] = differences["UUID"].isin(metadata_uuids)

    differences["TOTAL_PRESENTE"] = (
        differences["FACTURAS"].astype(int)
        + differences["EDICOM"].astype(int)
        + differences["METADATA"].astype(int)
    )

    # Me quedo solamente con los que NO están en los 3
    differences = differences[differences["TOTAL_PRESENTE"] < 3].copy()

    differences = differences[
        [
            "UUID",
            "EDICOM",
            "METADATA",
            "FACTURAS",
        ]
    ].sort_values(["UUID"])
    return differences


def build_metadata_missings(
    consolidated_df: pd.DataFrame,
    metadata_uuids: list[str],
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge metadata records with the CFDI dataframe for subtree comparison.

    Args:
        consolidated_df: Consolidated dataset used as the baseline.
        metadata_uuids: UUIDs that are missing from the metadata source.
        transformed_metadata_info_df: Metadata rows after transformation.
        transformed_cfdi_info_df: CFDI rows after transformation.

    Returns:
        A dataframe that combines the consolidated data with the metadata rows in
        need of comparison.
    """
    metadata_missings_df = transformed_metadata_info_df[
        transformed_metadata_info_df["Uuid"].isin(metadata_uuids)
    ]
    consolidated_metadata_df = pd.merge(
        metadata_missings_df,
        transformed_cfdi_info_df,
        left_on="Uuid",
        right_on="UUID",
        how="left",
        suffixes=("_EDICOM", "_METADATA"),
    )
    consolidated_metadata_df = consolidated_metadata_df.rename(
        columns={
            "Monto": "TOTAL METADATA",
            "Estatus": "ESTATUS",
        }
    )
    consolidated_metadata_df["ESTATUS"] = np.where(
        consolidated_metadata_df["ESTATUS"] == 1, "Vigente", "Cancelado"
    )
    final_consolidated_df = pd.concat(
        [consolidated_df, consolidated_metadata_df],
        ignore_index=True,
    )
    return final_consolidated_df


def join_dfs(
    transformed_df_results: TransformedResult,
) -> pd.DataFrame:
    """Assemble the merged dataset using exact, tolerance, and UUID match stages.

    Args:
        transformed_df_results: Transformed data from Edicom, metadata, and CFDI.

    Returns:
        The final consolidated dataframe after all matching steps.
    """

    consolidated_df = merge_metadata(transformed_df_results)

    matched_exact, unmatched_edicom = exact_match(
        consolidated_df,
        transformed_df_results.factura,
    )

    matched_diff, unmatched_diff, available_cfdi = tolerance_match(
        matched_exact,
        unmatched_edicom,
        transformed_df_results.factura,
    )

    uuid_only_matches, unmatched_definitive = uuid_match(
        unmatched_diff,
        available_cfdi,
        matched_diff,
    )

    return build_final_df(
        matched_exact,
        matched_diff,
        uuid_only_matches,
        unmatched_definitive,
    )


def merge_metadata(
    transformed_df_results: TransformedResult,
) -> pd.DataFrame:
    """Merge Edicom rows to the unique metadata values by UUID.

    Args:
        transformed_df_results: Transformed source data for the current period.

    Returns:
        A DataFrame with Edicom rows enriched by metadata columns when available.
    """

    metadata_unique = transformed_df_results.metadata.drop_duplicates(
        subset=["Uuid"], keep="first"
    )

    return pd.merge(
        transformed_df_results.edicom,
        metadata_unique,
        left_on="UUID",
        right_on="Uuid",
        how="left",
        suffixes=("_EDICOM", "_METADATA"),
    )


def exact_match(
    consolidated_df: pd.DataFrame,
    factura_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match Edicom rows to CFDI rows using an exact UUID and total key.

    Args:
        consolidated_df: Merged Edicom and metadata dataframe.
        factura_df: CFDI dataframe to match against.

    Returns:
        A tuple with the exact matches and the unmatched Edicom rows.
    """

    left = consolidated_df.copy()
    right = factura_df.copy()

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

    unmatched_edicom = exact_matches[exact_matches["_merge"] == "left_only"].copy()

    return matched_exact, unmatched_edicom


def select_best_matches(
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Select the best one-to-one candidate rows without reusing the same concept.

    Args:
        candidates: Candidate matches between source rows.

    Returns:
        A dataframe with a non-duplicated set of selected matches.
    """

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

    return pd.DataFrame(selected_rows)


def tolerance_match(
    matched_exact: pd.DataFrame,
    unmatched_edicom: pd.DataFrame,
    factura_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Match remaining Edicom rows to CFDI rows by UUID and near-equal total.

    Args:
        matched_exact: Rows already matched by exact rules.
        unmatched_edicom: Remaining Edicom rows not yet matched.
        factura_df: CFDI dataframe available for matching.

    Returns:
        The matched rows, the still-unmatched rows, and the available CFDI rows.
    """

    unmatched_edicom = unmatched_edicom.loc[
        :,
        ~(
            unmatched_edicom.columns.isin(
                [c for c in factura_df.columns if c != "UUID"]
            )
            | unmatched_edicom.columns.isin(["_seq", "_row_id", "_merge"])
        ),
    ]

    used_cfdi_keys = set(
        zip(
            matched_exact["UUID"],
            matched_exact["TOTAL_CONCEPTO"],
        )
    )

    available_cfdi = factura_df[
        ~factura_df.apply(
            lambda r: (
                (
                    r["UUID"],
                    r["TOTAL_CONCEPTO"],
                )
                in used_cfdi_keys
            ),
            axis=1,
        )
    ].copy()

    available_cfdi = available_cfdi.reset_index(drop=True)
    available_cfdi["CFDI_ID"] = available_cfdi.index

    candidates = unmatched_edicom.merge(
        available_cfdi,
        on="UUID",
        suffixes=("_left", "_right"),
    )

    candidates["diff"] = (
        candidates["TOTAL CONCEPTO"] - candidates["TOTAL_CONCEPTO"]
    ).abs()

    candidates = candidates[candidates["diff"] <= 1].copy()

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

    matched_keys = set(
        zip(
            matched_diff["UUID"],
            matched_diff["TOTAL CONCEPTO"],
        )
    )

    unmatched_diff = unmatched_edicom[
        ~unmatched_edicom.apply(
            lambda r: (
                (
                    r["UUID"],
                    r["TOTAL CONCEPTO"],
                )
                in matched_keys
            ),
            axis=1,
        )
    ].copy()

    logger.info(
        "Tolerance matching completed",
        extra={
            "matches": len(matched_diff),
            "remaining": len(unmatched_diff),
        },
    )

    return (
        matched_diff,
        unmatched_diff,
        available_cfdi,
    )


def uuid_match(
    unmatched_diff: pd.DataFrame,
    available_cfdi: pd.DataFrame,
    matched_diff: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match the remaining rows when the UUID is unique within the available CFDI set.

    Args:
        unmatched_diff: Rows still unmatched after the tolerance pass.
        available_cfdi: CFDI rows still available for matching.
        matched_diff: Rows already matched in the tolerance pass.

    Returns:
        The UUID-only matches and the final rows that remain unmatched.
    """

    used_uuids_diff = set(matched_diff["UUID"])

    remaining_cfdi = available_cfdi[
        ~available_cfdi["UUID"].isin(used_uuids_diff)
    ].copy()

    unique_uuid_cfdi = remaining_cfdi.groupby("UUID").filter(lambda x: len(x) == 1)

    uuid_only_matches = unmatched_diff.merge(
        unique_uuid_cfdi,
        on="UUID",
        how="inner",
        suffixes=("_left", "_right"),
    )

    unmatched_definitive = unmatched_diff[
        ~unmatched_diff["UUID"].isin(uuid_only_matches["UUID"])
    ].copy()

    logger.info(
        "UUID matching completed",
        extra={
            "uuid_matches": len(uuid_only_matches),
            "unmatched": len(unmatched_definitive),
        },
    )

    return (
        uuid_only_matches,
        unmatched_definitive,
    )


def build_final_df(
    matched_exact: pd.DataFrame,
    matched_diff: pd.DataFrame,
    uuid_only_matches: pd.DataFrame,
    unmatched_definitive: pd.DataFrame,
) -> pd.DataFrame:
    """Concatenate the exact, tolerance, UUID-only, and unmatched match outputs.

    Args:
        matched_exact: Rows matched by exact equality.
        matched_diff: Rows matched by tolerance logic.
        uuid_only_matches: Rows matched via unique UUID availability.
        unmatched_definitive: Rows still without a match.

    Returns:
        A final combined dataframe preserving the existing matching pipeline order.
    """

    return pd.concat(
        [
            matched_exact.drop(columns=["_merge", "_seq", "_row_id"]),
            matched_diff.drop(columns=["diff"]),
            uuid_only_matches,
            unmatched_definitive,
        ],
        ignore_index=True,
    )
