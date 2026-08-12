"""Entry point for the CFDI reporting pipeline."""

import argparse
import logging
from argparse import Namespace
from datetime import datetime

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
        type=validate_date_format,
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


def validate_date_format(date_str: str) -> str:
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


def main() -> None:
    """Execute the full reporting pipeline from data loading to Excel export."""
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    #     )
    args = parse_args()
    logger.info("Pipeline started", extra={"date": args.date})
    success = build_report(args.date, args.format)
    if success:
        logger.info("Export completed", extra={"date": args.date})
    else:
        logger.error("Export failed", extra={"date": args.date})


if __name__ == "__main__":
    main()
