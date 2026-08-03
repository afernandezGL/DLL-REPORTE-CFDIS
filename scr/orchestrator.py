"""Orchestration helpers for the CFDI reporting pipeline."""

from __future__ import annotations

import logging

import pandas as pd

from scr.export import export_to_client_format, save_log
from scr.integration import get_summary, integrate_data, join_dfs
from scr.loader import get_cfdi_info, get_edicom_info, get_edicom_logs, get_metadata_info
from scr.transformer import normalize_concepts, transform_cfdi_info, transform_edicom_info, transform_metadata_info

logger = logging.getLogger(__name__)

def load_data(
    date_: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw metadata, Edicom, CFDI, and log data for the requested period.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A tuple containing the raw metadata, Edicom, CFDI, and Edicom log DataFrames.
    """
    logger.info("Loading raw data for date", extra={"date": date_})

    raw_metadata_info_df = get_metadata_info(date_)
    raw_edicom_info_df = get_edicom_info(date_)
    raw_cfdi_info_df = get_cfdi_info(date_)
    transform_edicom_log = get_edicom_logs(date_)
    return (
        raw_metadata_info_df,
        raw_edicom_info_df,
        raw_cfdi_info_df,
        transform_edicom_log,
    )


def transform_data(
    raw_metadata_info_df: pd.DataFrame,
    raw_edicom_info_df: pd.DataFrame,
    raw_cfdi_info_df: pd.DataFrame,
    transform_edicom_log: pd.DataFrame,
    date_: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Transform the raw source datasets into normalized structures for integration.

    Args:
        raw_metadata_info_df: Raw metadata rows loaded from disk.
        raw_edicom_info_df: Raw Edicom rows loaded from the workbook.
        raw_cfdi_info_df: Raw CFDI rows retrieved from the database.
        transform_edicom_log: Historical Edicom log rows for the current year.
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A tuple with the transformed Edicom, metadata, and CFDI DataFrames.
    """
    logger.info("Transforming raw dataframes")
    transformed_edicom_info_df = transform_edicom_info(raw_edicom_info_df)
    normalize_transformed_edicom_info_df = normalize_concepts(
        transformed_edicom_info_df
    )
    if save_log(normalize_transformed_edicom_info_df, date_):
        logger.info("Create log correctly")
    year_transformed_edicom_info_df = pd.concat(
        [transform_edicom_log, normalize_transformed_edicom_info_df], ignore_index=True
    )
    transformed_metadata_info_df = transform_metadata_info(raw_metadata_info_df)
    transformed_cfdi_info_df = transform_cfdi_info(raw_cfdi_info_df)
    logger.info(
        "Transformation completed",
        extra={
            "edicom_rows": int(year_transformed_edicom_info_df.shape[0]),
            "metadata_rows": int(transformed_metadata_info_df.shape[0]),
            "cfdi_rows": int(transformed_cfdi_info_df.shape[0]),
        },
    )
    return (
        year_transformed_edicom_info_df,
        transformed_metadata_info_df,
        transformed_cfdi_info_df,
    )


def consolidate_info(
    transformed_edicom_info_df: pd.DataFrame,
    transformed_metadata_info_df: pd.DataFrame,
    transformed_cfdi_info_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge and reconcile the transformed source datasets into a single report-ready DataFrame.

    Args:
        transformed_edicom_info_df: Transformed Edicom rows.
        transformed_metadata_info_df: Transformed metadata rows.
        transformed_cfdi_info_df: Transformed CFDI rows.

    Returns:
        A consolidated DataFrame containing the integrated business view.
    """
    logger.info("Consolidating dataframes")
    consolidated_df = join_dfs(
        transformed_edicom_info_df,
        transformed_metadata_info_df,
        transformed_cfdi_info_df,
    )

    consolidated_df = integrate_data(consolidated_df)
    logger.info(
        "Consolidation completed", extra={"rows": int(consolidated_df.shape[0])}
    )
    return consolidated_df


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
    raw_metadata_info_df, raw_edicom_info_df, raw_cfdi_info_df, transform_edicom_log = load_data(date_)
    transformed_edicom_info_df, transformed_metadata_info_df, transformed_cfdi_info_df = transform_data(
        raw_metadata_info_df,
        raw_edicom_info_df,
        raw_cfdi_info_df,
        transform_edicom_log,
        date_,
    )
    consolidated_df = consolidate_info(
        transformed_edicom_info_df,
        transformed_metadata_info_df,
        transformed_cfdi_info_df,
    )
    edicom_resumen, metadata_resumen, factura_resumen = get_summary(consolidated_df)

    if format_ == "cliente":
        export_to_client_format(
            consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_
        )
    elif format_ == "winba":
        # TODO Change this to export_to_winba_format when implemented
        export_to_client_format(
            consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_
        )
    return True
