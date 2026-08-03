"""Entry point for the CFDI reporting pipeline."""

import pandas as pd
import logging
from datetime import datetime
from sqlalchemy import create_engine
import argparse
from argparse import Namespace
from scr.loader import (
    get_edicom_logs,
    get_cfdi_info,
    get_metadata_info,
    get_edicom_info,
)
from scr.transformer import (
    transform_cfdi_info,
    transform_edicom_info,
    transform_metadata_info,
    normalize_concepts,
)
from scr.integration import integrate_data, get_summary, join_dfs
from scr.export import export_to_client_format, save_log

logger = logging.getLogger(__name__)


def parse_args() -> Namespace:
    """Parse command-line arguments for the reporting pipeline.

    Returns:
        A Namespace object containing the validated CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="Procesar datos de CFDI, Edicom y Metadata."
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Fecha en formato YYYY_MM para procesar los datos.",
    )

    parser.add_argument(
        "--format",
        choices=["cliente", "winba"],
        required=False,
        default="cliente",
    )
    return parser.parse_args()


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


def validate_args(date_str: str) -> str:
    """Validate that the supplied period follows the expected YYYY_MM format.

    Args:
        date_str: The period passed from the command line.

    Returns:
        The validated period string.

    Raises:
        ValueError: If the date string is not in the expected format.
    """
    try:
        datetime.strptime(date_str, "%Y_%m")
    except ValueError:
        logger.error("Invalid date format", extra={"date_str": date_str})
        raise ValueError("La fecha debe estar en formato YYYY-MM.")
    return date_str


def main():
    """Execute the full reporting pipeline from data loading to Excel export."""
    args = parse_args()
    date_ = validate_args(args.date)
    logger.info("Pipeline started", extra={"date": date_})
    raw_metadata_info_df, raw_edicom_info_df, raw_cfdi_info_df, transform_edicom_log = (
        load_data(date_)
    )
    (
        transformed_edicom_info_df,
        transformed_metadata_info_df,
        transformed_cfdi_info_df,
    ) = transform_data(
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

    if args.format == "cliente":
        export_to_client_format(
            consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_
        )
    elif args.format == "winba":
        # TODO Change this to export_to_winba_format when implemented
        export_to_client_format(
            consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_
        )

    logger.info("Export completed", extra={"date": date_})
    print("Se creo correctamente el archivo")


if __name__ == "__main__":
    main()
