from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent

METADATA_FOLDER_NAME = BASE_DIR / "data" / "metadata"
EDICOM_FOLDER_NAME = BASE_DIR / "data" / "edicom"
EDICOM_LOG_FOLDER_NAME = EDICOM_FOLDER_NAME / "logs"
OUTPUT_FOLDER = BASE_DIR / "data" / "output"

load_dotenv(BASE_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")
