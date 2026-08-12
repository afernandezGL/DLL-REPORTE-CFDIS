"""Orchestration helpers for the CFDI reporting pipeline."""

from __future__ import annotations

import logging

import pandas as pd

from scr.export import export_to_client_format, export_to_winba_format, save_log
from scr.integration import (
    get_differences,
    get_summary,
    integrate_data,
    join_dfs,
)
from scr.loader import (
    get_cfdi_info,
    get_edicom_info,
    get_edicom_logs,
    get_full_cfdi_info,
    get_metadata_info,
)
from scr.models import (
    DifferencesReportResult,
    DifferencesResult,
    RawResult,
    ReportResult,
    TransformedResult,
)
from scr.transformer import (
    filter_metadata_info,
    normalize_concepts,
    transform_cfdi_info,
    transform_edicom_info,
    transform_metadata_info,
)

logger = logging.getLogger(__name__)


def load_data(
    date_: str,
) -> tuple[pd.DataFrame, RawResult]:
    """Load raw metadata, Edicom, CFDI, and log data for the requested period.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A tuple containing the raw metadata, Edicom, CFDI, and Edicom log DataFrames.
    """
    logger.info("Loading raw data for date", extra={"date": date_})

    raw_metadata_info_df = get_metadata_info(date_)
    raw_edicom_info_df = get_edicom_info(date_)
    rfc_emisor_list = raw_metadata_info_df["RfcEmisor"].dropna().unique().tolist()
    raw_cfdi_info_df = get_cfdi_info(date_, rfc_emisor_list)
    transform_edicom_log = get_edicom_logs(date_)
    return (
        transform_edicom_log,
        RawResult(
            edicom=raw_edicom_info_df,
            metadata=raw_metadata_info_df,
            factura=raw_cfdi_info_df,
        ),
    )


def transform_data(
    raw_df_results: RawResult,
    transform_edicom_log: pd.DataFrame,
    date_: str,
) -> TransformedResult:
    """Transform the raw source datasets into normalized structures for integration.

    Args:
        raw_df_results: RawResult object containing raw metadata, Edicom, and CFDI rows.
        transform_edicom_log: Historical Edicom log rows for the current year.
        date_: Period identifier in the YYYY_MM format.

    Returns:
        TransformedResult object containing the filtered metadata, transformed Edicom, transformed metadata, and transformed CFDI DataFrames.
    """
    logger.info("Transforming raw dataframes")
    transformed_edicom_info_df = transform_edicom_info(raw_df_results.edicom)
    normalize_transformed_edicom_info_df = normalize_concepts(
        transformed_edicom_info_df
    )
    year_transformed_edicom_info_df = pd.concat(
        [transform_edicom_log, normalize_transformed_edicom_info_df], ignore_index=True
    )
    filtered_metadata_info_df = filter_metadata_info(raw_df_results.metadata, date_)
    transformed_metadata_info_df = transform_metadata_info(
        filtered_metadata_info_df, date_
    )
    filtered_metadata_info_df = filtered_metadata_info_df.sort_values(
        by=["RfcEmisor", "FechaEmision"], ascending=[True, True]
    )
    transformed_cfdi_info_df = transform_cfdi_info(raw_df_results.factura, date_)
    logger.info(
        "Transformation completed",
        extra={
            "edicom_rows": int(year_transformed_edicom_info_df.shape[0]),
            "metadata_rows": int(transformed_metadata_info_df.shape[0]),
            "cfdi_rows": int(transformed_cfdi_info_df.shape[0]),
        },
    )
    return TransformedResult(
        edicom=year_transformed_edicom_info_df,
        metadata=transformed_metadata_info_df,
        factura=transformed_cfdi_info_df,
        filtered_metadata=filtered_metadata_info_df,
        normalize_edicom=normalize_transformed_edicom_info_df,
    )


def consolidate_info(
    transformed_df_results: TransformedResult,
) -> pd.DataFrame:
    """Merge and reconcile the transformed source datasets into a single report-ready DataFrame.

    Args:
        transformed_df_results: TransformedResult object containing the transformed Edicom, metadata, and CFDI DataFrames.

    Returns:
        A consolidated DataFrame containing the integrated business view.
    """
    logger.info("Consolidating dataframes")
    consolidated_df = join_dfs(transformed_df_results)

    consolidated_df = integrate_data(consolidated_df)
    logger.info(
        "Consolidation completed",
        extra={"rows": int(consolidated_df.shape[0])},
    )
    return consolidated_df


def reload_differences(
    transformed_df_results: TransformedResult,
    differences_result: DifferencesResult,
    date_: str,
) -> DifferencesReportResult:
    """Build the report-ready difference datasets for the current period.

    The function reconstructs the UUID and subtotal comparison slices using the
    original filtered metadata and the full CFDI rows for the affected UUIDs.

    Args:
        transformed_df_results: Normalized source data for the current period.
        differences_result: Difference summary produced from the consolidated view.
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A structured result object containing the consolidated and source-specific
        difference tables for export.
    """
    rfc_emisor_list = (
        transformed_df_results.factura["RFC_EMISOR"].dropna().unique().tolist()
    )
    subtotal_differences_uuids_list = (
        differences_result.relevant_subtotal["UUID"].dropna().unique().tolist()
    )
    all_facturas_differences_uuid = list(
        set(subtotal_differences_uuids_list)
        | set(differences_result.relevant_uuid.facturas)
    )

    uuid_metadata_differences_df = filter_by_uuid(
        transformed_df_results.filtered_metadata,
        differences_result.relevant_uuid.metadata,
        uuid_column="Uuid",
    )
    subtotal_metadata_differences_df = filter_by_uuid(
        transformed_df_results.filtered_metadata,
        subtotal_differences_uuids_list,
        uuid_column="Uuid",
    )

    uuid_edicom_differences_df = filter_by_uuid(
        transformed_df_results.edicom,
        differences_result.relevant_uuid.edicom,
        uuid_column="UUID",
    )

    subtotal_edicom_differences_df = filter_by_uuid(
        transformed_df_results.edicom,
        subtotal_differences_uuids_list,
        uuid_column="UUID",
    )

    raw_full_cfdi_info_df = get_full_cfdi_info(
        date_,
        rfc_emisor_list=rfc_emisor_list,
        uuid_list=all_facturas_differences_uuid,
    )

    uuid_facturas_differences_df = filter_by_uuid(
        raw_full_cfdi_info_df,
        differences_result.relevant_uuid.facturas,
        uuid_column="UUID",
    )

    subtotal_facturas_differences_df = filter_by_uuid(
        raw_full_cfdi_info_df,
        subtotal_differences_uuids_list,
        uuid_column="UUID",
    )

    sorted_uuid_metadata_differences_df = uuid_metadata_differences_df.sort_values(
        by=["RfcEmisor", "FechaEmision"], ascending=[True, True]
    )
    sorted_subtotal_metadata_differences_df = (
        subtotal_metadata_differences_df.sort_values(
            by=["RfcEmisor", "FechaEmision"], ascending=[True, True]
        )
    )
    sorted_uuid_facturas_differences_df = uuid_facturas_differences_df.sort_values(
        by=["RFC_EMISOR", "FECHA"], ascending=[True, True]
    )
    sorted_subtotal_facturas_differences_df = (
        subtotal_facturas_differences_df.sort_values(
            by=["RFC_EMISOR", "FECHA"], ascending=[True, True]
        )
    )
    sorted_uuid_edicom_differences_df = uuid_edicom_differences_df.sort_values(
        by=["FECHAREAL"], ascending=[True]
    )
    sorted_subtotal_edicom_differences_df = subtotal_edicom_differences_df.sort_values(
        by=["FECHAREAL"], ascending=[True]
    )

    return DifferencesReportResult(
        consolidated=differences_result.uuid,
        comparative_subtotals=differences_result.subtotal,
        relevant_comparative_subtotals=differences_result.relevant_subtotal,
        uuid=ReportResult(
            edicom=sorted_uuid_edicom_differences_df,
            metadata=sorted_uuid_metadata_differences_df,
            factura=sorted_uuid_facturas_differences_df,
        ),
        subtotal=ReportResult(
            edicom=sorted_subtotal_edicom_differences_df,
            metadata=sorted_subtotal_metadata_differences_df,
            factura=sorted_subtotal_facturas_differences_df,
        ),
    )


def filter_by_uuid(
    df: pd.DataFrame,
    uuids: list[str],
    uuid_column: str = "UUID",
) -> pd.DataFrame:
    """Return the rows whose UUID column matches a provided list of identifiers.

    Args:
        df: Source dataframe to filter.
        uuids: UUID values to keep in the result.
        uuid_column: Column name that stores the UUID values.

    Returns:
        A dataframe containing only the rows whose identifier is in ``uuids``.
    """
    return df[df[uuid_column].isin(uuids)]


def build_report(date_: str, format_: str) -> bool:
    """Run the full report pipeline for a single period.

    This function coordinates loading, transformation, consolidation, and summarization
    into a single entry point that can be reused by the CLI or tests.

    Args:
        date_: Period identifier in the YYYY_MM format.
        format_: The output format for the report, either "cliente" or "winba".

    Returns:
        True if the report was successfully built and exported, False otherwise.
    """
    logger.info("Building report", extra={"date": date_})
    accumulated_edicom_info_df, raw_df_results = load_data(date_)

    transformed_df_results = transform_data(
        raw_df_results,
        accumulated_edicom_info_df,
        date_,
    )
    if save_log(transformed_df_results.normalize_edicom, date_):
        logger.info("Create log correctly")
    consolidated_df = consolidate_info(transformed_df_results)
    summary_df_results = get_summary(
        consolidated_df, transformed_df_results.metadata, transformed_df_results.factura
    )
    differences_result = get_differences(consolidated_df, transformed_df_results)
    differences_report_result = reload_differences(
        transformed_df_results,
        differences_result,
        date_,
    )
    if format_ == "cliente":
        export_to_client_format(
            consolidated_df,
            summary_df_results,
            differences_report_result,
            date_,
        )
    elif format_ == "winba":
        export_to_winba_format(
            consolidated_df,
            transformed_df_results.filtered_metadata,
            summary_df_results,
            differences_report_result,
            date_,
        )
    return True
