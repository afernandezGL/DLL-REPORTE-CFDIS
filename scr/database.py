import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config.config import (
    DB_PORT,
    DB_SERVER,
    DB_DATABASE,
    DB_USER,
    DB_PASSWORD,
)

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine for connecting to the database using the provided configuration.

    Returns:
        Engine: A SQLAlchemy engine object for database connection.

    Raises:
        ValueError: If any of the required database configuration parameters are missing.
    """

    logger.info("Creating DB engine", extra={"server": DB_SERVER, "database": DB_DATABASE, "user": DB_USER, "port": DB_PORT})
    if not all([DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD, DB_PORT]):
        logger.error("Missing DB configuration parameters")
        raise ValueError(
            "Hace falta uno o más parámetros de configuración de la base de datos. Por favor, verifica el archivo .env."
        )

    # Avoid logging sensitive values like DB_PASSWORD
    connection_string = (
        f"mssql+pymssql://"
        f"{DB_USER}:{DB_PASSWORD}"
        f"@{DB_SERVER}:{DB_PORT}/"
        f"{DB_DATABASE}"
    )

    try:
        engine = create_engine(connection_string, pool_pre_ping=True)
        logger.debug("DB engine created successfully")
        return engine
    except Exception as e:
        logger.exception("Failed to create DB engine", exc_info=e)
        raise

def close_engine(engine: Engine) -> None:
    """
    Close the SQLAlchemy engine to release database resources.

    Args:
        engine (Engine): The SQLAlchemy engine to be closed.
    """
    if engine:
        try:
            engine.dispose()
            logger.debug("DB engine disposed")
        except Exception as e:
            logger.exception("Error disposing DB engine", exc_info=e)