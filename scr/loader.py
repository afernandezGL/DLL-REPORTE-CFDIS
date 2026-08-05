"""Helpers for loading source data from metadata archives, Edicom files, and the CFDI database."""

import os
import io
import zipfile
import logging
import pandas as pd
from pathlib import Path

from sqlalchemy import text, text
from config.config import METADATA_FOLDER_NAME, EDICOM_FOLDER_NAME, EDICOM_LOG_FOLDER_NAME
from scr.database import close_engine, get_engine
from scr.models import MONTHS, edicom_log_column_names
from data.sql.cfdi import cfdi_query
import csv

logger = logging.getLogger(__name__)

def get_metadata_info(date_: str) -> pd.DataFrame:
    """Load raw metadata rows from the ZIP archive for a given period.

    The function scans the metadata directory for the requested period, reads every
    CSV or TXT file contained in the single ZIP archive, and returns the combined
    content as a single pandas DataFrame.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A DataFrame containing the raw metadata rows extracted from the archive.

    Raises:
        FileNotFoundError: If no ZIP archive is found for the requested period.
        ValueError: If multiple ZIP archives are present or the archive contains no
            readable CSV/TXT content.
    """
    metadata_folder = os.path.join(METADATA_FOLDER_NAME, date_)
    logger.info("Loading metadata info", extra={"metadata_folder": metadata_folder})

    zip_files = [f for f in os.listdir(metadata_folder) if f.endswith(".zip")]

    if not zip_files:
        logger.error("No .zip files found in metadata folder", extra={"folder": metadata_folder})
        raise FileNotFoundError("No se encontro ningun archivo .zip en el directorio.")
    elif len(zip_files) > 1:
        logger.error("Multiple zip files found", extra={"zip_files": zip_files})
        raise ValueError(
            f"Se encontraron múltiples archivos .zip: {zip_files}. Solo se permite un archivo ZIP."
        )

    zip_path = os.path.join(METADATA_FOLDER_NAME, date_, zip_files[0])
    raw_dfs = []

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        logger.debug("Opened metadata zip", extra={"zip_path": zip_path, "namelist": zip_ref.namelist()})
        for name in zip_ref.namelist():
            if name.endswith((".csv", ".txt")):
                logger.debug("Reading file from zip", extra={"file": name})
                with zip_ref.open(name) as file:
                    file_data = io.BytesIO(file.read())
                    df = pd.read_csv(file_data, sep="~", engine="python", quoting=csv.QUOTE_NONE)
                    raw_dfs.append(df)

    if not raw_dfs:
        logger.error("ZIP does not contain CSV/TXT files", extra={"zip_path": zip_path})
        raise ValueError("El archivo ZIP no contiene ningún archivo .csv o .txt.")
    raw_metadata_df = pd.concat(raw_dfs, ignore_index=True)
    logger.info("Loaded metadata dataframe", extra={"rows": int(raw_metadata_df.shape[0])})
    return raw_metadata_df

def get_edicom_info(date_) -> pd.DataFrame:
    """Load raw Edicom data from the workbook stored for the requested period.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A DataFrame containing the raw Edicom content from the Excel workbook.

    Raises:
        FileNotFoundError: If no XLSX workbook is found for the requested period.
        ValueError: If multiple workbook files are present in the target folder.
    """

    folder = os.path.join(EDICOM_FOLDER_NAME, date_)
    logger.info("Loading Edicom info", extra={"folder": folder})
    xlsx_files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]

    if not xlsx_files:
        logger.error("No .xlsx files found in edicom folder", extra={"folder": folder})
        raise FileNotFoundError(f"No se encontró ningún archivo .xlsx en el directorio: {EDICOM_FOLDER_NAME}")
    elif len(xlsx_files) > 1:
        logger.error("Multiple xlsx files found", extra={"xlsx_files": xlsx_files})
        raise ValueError(
            f"Se encontraron múltiples archivos .xlsx: {xlsx_files}. Solo se permite un archivo XLSX."
        )

    xlsx_path = os.path.join(EDICOM_FOLDER_NAME, date_, xlsx_files[0])
    raw_edicom_df = pd.read_excel(xlsx_path)
    logger.info("Loaded edicom dataframe", extra={"rows": int(raw_edicom_df.shape[0])})
    return raw_edicom_df

def get_edicom_logs(date_: str) -> pd.DataFrame:
    """Load prior Edicom log files for the same year to build historical context.

    For months after January, the function collects the log workbooks from the
    previous months in the same year and returns them as a single DataFrame.
    January returns an empty structure to seed the historical log.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A DataFrame containing the historical Edicom log rows for the requested year.

    Raises:
        FileNotFoundError: If a required monthly log workbook is missing.
        ValueError: If the workbook columns do not match the expected log schema.
    """
    year = date_.split('_')[0]
    month = date_.split('_')[1]
    if month == "01":
        return pd.DataFrame(columns=edicom_log_column_names)
    folder = os.path.join(EDICOM_LOG_FOLDER_NAME, year)
    year_folder = Path(folder)
    # Search folder ending with YYYY

    if not year_folder.exists():
        year_folder = Path(folder)
        year_folder.mkdir(parents=True, exist_ok=True)

    log_dfs = []
    # Months before the requested month
    for m in range(int(month) - 2, -1, -1):
        file_path = year_folder / f"log_{MONTHS[m]}.xlsx"

        if not file_path.exists():
            raise FileNotFoundError(
                f"No se encintro el archivo {file_path}"
            )

        temp_df = pd.read_excel(file_path)

        if list(temp_df.columns) != edicom_log_column_names:
            raise ValueError(
                f"Las Columnas no mechean en el archivo {file_path}"
            )

        log_dfs.append(temp_df)

    return pd.concat(log_dfs, ignore_index=True)

    
    return raw_edicom_df

def get_cfdi_info(date_: str) -> pd.DataFrame:
    """Fetch raw CFDI rows from the configured database for the requested period.

    Args:
        date_: Period identifier in the YYYY_MM format.

    Returns:
        A DataFrame containing the raw CFDI rows retrieved from the database.

    Raises:
        Exception: If the query execution or connection handling fails.
    """
    engine = None
    year = int(date_.split("_")[0])
    try:
        filter_cfdi_query = cfdi_query.format(year=year)
        logger.info("Fetching CFDI info from DB", extra={"date": date_})
        engine = get_engine()
        cfdi_raw_info_df = pd.read_sql(filter_cfdi_query, engine)
        logger.info("Fetched cfdi dataframe", extra={"rows": int(cfdi_raw_info_df.shape[0])})
    except Exception as e:
        logger.exception("Error durante la extracción de CFDI", exc_info=e)
        raise
    finally:
        if engine:
            close_engine(engine)
    return cfdi_raw_info_df
