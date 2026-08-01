import os
import io
import zipfile
import logging
import pandas as pd
from pathlib import Path
from config.config import METADATA_FOLDER_NAME, EDICOM_FOLDER_NAME, EDICOM_LOG_FOLDER_NAME
from scr.database import close_engine, get_engine
from scr.models import MONTHS, edicom_log_column_names
from data.sql.cfdi import cfdi_query
import csv

logger = logging.getLogger(__name__)

def get_metadata_info(date_: str) -> pd.DataFrame:
    """
    Get metadata information from a ZIP file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw metadata information.

    Raises:
        FileNotFoundError: If no .zip file is found in the specified folder.
        ValueError: If multiple .zip files are found in the specified folder.
        ValueError: If the ZIP file does not contain any .csv or .txt files.
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
    """
    Get Edicom information from a Excel file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw Edicom information.
    
    Raises:
        FileNotFoundError: If the specified Excel file is not found.
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

def get_edicom_logs(date_: str) -> pd.DataFrame | None:
    """
    Get Edicom log from a Excel file in the specified folder, and save the transformed data into a pandas DataFrame.

    Input:
        str: Date str with format YYYY

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw Edicom log.
    
    Raises:
        FileNotFoundError: If the specified Excel file is not found.
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
    for month_name in MONTHS[int(month)-1]:
        import pdb; pdb.set_trace()
        file_path = year_folder / f"log_{month_name}.txt"

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
    """
    Get CFDI information from a Excel file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw CFDI information.

    Raises:
        Exception: If there is an error during the extraction of CFDI information from the database.
    
    """
    engine = None
    try:
        logger.info("Fetching CFDI info from DB", extra={"date": date_})
        engine = get_engine()
        cfdi_raw_info_df = pd.read_sql(cfdi_query, engine)
        logger.info("Fetched cfdi dataframe", extra={"rows": int(cfdi_raw_info_df.shape[0])})
    except Exception as e:
        logger.exception("Error durante la extracción de CFDI", exc_info=e)
        raise
    finally:
        if engine:
            close_engine(engine)
    return cfdi_raw_info_df
