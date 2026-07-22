from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config.config import (
    DB_PORT,
    DB_SERVER,
    DB_DATABASE,
    DB_USER,
    DB_PASSWORD
)


def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine for connecting to the database using the provided configuration.

    Returns:
        Engine: A SQLAlchemy engine object for database connection.

    Raises:
        ValueError: If any of the required database configuration parameters are missing.
    """

    if not all([DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD, DB_PORT]):
        raise ValueError("Hace falta uno o más parámetros de configuración de la base de datos. Por favor, verifica el archivo .env.")

    connection_string = (
        f"mssql+pymssql://"
        f"{DB_USER}:{DB_PASSWORD}"
        f"@{DB_SERVER}:{DB_PORT}/"
        f"{DB_DATABASE}"
    )

    engine = create_engine(
        connection_string,
        pool_pre_ping=True
    )

    return engine

def close_engine(engine: Engine) -> None:
    """
    Close the SQLAlchemy engine to release database resources.

    Args:
        engine (Engine): The SQLAlchemy engine to be closed.
    """
    if engine:
        engine.dispose()