import os
import io
import zipfile
import pandas as pd
from config.config import METADATA_FOLDER_NAME, EDICOM_FOLDER_NAME
from scr.database import close_engine, get_engine
from data.sql.cfdi import cfdi_query
from data.sql.banxico import banxico_query

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

    zip_files = [
        f
        for f in os.listdir(metadata_folder)
        if f.endswith(".zip")
    ]

    if not zip_files:
        raise FileNotFoundError("No se encontro ningun archivo .zip en el directorio.")
    elif len(zip_files) > 1:
        raise ValueError(
            f"Se encontraron múltiples archivos .zip: {zip_files}. Solo se permite un archivo ZIP."
        )

    zip_path = os.path.join(METADATA_FOLDER_NAME, date_, zip_files[0])
    raw_dfs = []

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for name in zip_ref.namelist():
            if name.endswith((".csv", ".txt")):
                with zip_ref.open(name) as file:
                    file_data = io.BytesIO(file.read())
                    df = pd.read_csv(file_data, sep="~", engine="python")
                    raw_dfs.append(df)

    if not raw_dfs:
        raise ValueError("El archivo ZIP no contiene ningún archivo .csv o .txt.")
    raw_metadata_df = pd.concat(raw_dfs, ignore_index=True)
    print(raw_metadata_df.info())
    return raw_metadata_df

def get_edicom_info(date_) -> pd.DataFrame:
    """
    Get Edicom information from a Excel file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw Edicom information.
    
    Raises:
        FileNotFoundError: If the specified Excel file is not found.
    """

    xlsx_files = [f for f in os.listdir(os.path.join(EDICOM_FOLDER_NAME, date_)) if f.endswith(".xlsx")]

    if not xlsx_files:
        raise FileNotFoundError(f"No se encontró ningún archivo .xlsx en el directorio: {EDICOM_FOLDER_NAME}")
    elif len(xlsx_files) > 1:
        raise ValueError(
            f"Se encontraron múltiples archivos .xlsx: {xlsx_files}. Solo se permite un archivo XLSX."
        )

    xlsx_path = os.path.join(EDICOM_FOLDER_NAME, date_, xlsx_files[0])
    raw_edicom_df = pd.read_excel(xlsx_path)
    print(raw_edicom_df.info())
    return raw_edicom_df

def get_cfdi_info(date_: str) -> pd.DataFrame:
    """
    Get CFDI information from a Excel file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw CFDI information.

    Raises:
        Exception: If there is an error during the extraction of CFDI information from the database.
    
    """
    try:
        engine = get_engine()
        cfdi_raw_info_df = pd.read_sql(
            cfdi_query,
            engine,
            # params={"period": date_.replace("_", "-")}
            )
        print(cfdi_raw_info_df.info())
    except Exception as e:
        print(f"Error durante la extracción de CFDI: {e}")
    finally:
        close_engine(engine)
    return cfdi_raw_info_df

def get_banxico_info() -> pd.DataFrame:
    """
    Get Banxico information from a Excel file in the specified folder, and save the extracted data into a pandas DataFrame.

    Returns:
        DataFrame: A pandas DataFrame containing the extracted raw Banxico information.

    Raises:
        Exception: If there is an error during the extraction of Banxico information from the database.
    
    """
    try:
        engine = get_engine()
        banxico_raw_info_df = pd.read_sql(
            banxico_query,
            engine
            )
        print(banxico_raw_info_df.info())
    except Exception as e:
        print(f"Error durante la extracción de Banxico: {e}")
    finally:
        close_engine(engine)
    return banxico_raw_info_df
