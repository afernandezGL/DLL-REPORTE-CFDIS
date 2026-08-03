"""Entry point for the CFDI reporting pipeline."""

import logging
from datetime import datetime
import argparse
from argparse import Namespace
from scr.orchestrator import build_report

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
        raise ValueError("La fecha debe estar en formato YYYY_MM.")
    return date_str


def main():
    """Execute the full reporting pipeline from data loading to Excel export."""
    args = parse_args()
    date_ = validate_args(args.date)
    logger.info("Pipeline started", extra={"date": date_})
    success = build_report(date_, args.format)
    if success:
        logger.info("Export completed", extra={"date": date_})
        print("Se creo correctamente el archivo")
    else:
        logger.error("Export failed", extra={"date": date_})
        print("Error al crear el archivo")


if __name__ == "__main__":
    main()
