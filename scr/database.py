"""Database connection helpers for the SQLAlchemy engine used by the pipeline."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config.config import (
    DB_DATABASE,
    DB_PASSWORD,
    DB_PORT,
    DB_SERVER,
    DB_USER,
)

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    """Create a SQLAlchemy engine for the configured database connection.

    Returns:
        A SQLAlchemy Engine instance ready for executing SQL queries.

    Raises:
        ValueError: If any required database configuration value is missing.
    """

    logger.info(
        "Creating DB engine",
        extra={
            "server": DB_SERVER,
            "database": DB_DATABASE,
            "user": DB_USER,
            "port": DB_PORT,
        },
    )
    if not all([DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD, DB_PORT]):
        logger.error("Missing DB configuration parameters")
        raise ValueError(
            "Hace falta uno o más parámetros de configuración de la base de datos. Por favor, verifica el archivo .env."
        )

    # Avoid logging sensitive values like DB_PASSWORD
    connection_string = (
        f"mssql+pymssql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DATABASE}"
    )

    try:
        engine = create_engine(connection_string, pool_pre_ping=True)
        logger.debug("DB engine created successfully")
        return engine
    except Exception as e:
        logger.exception("Failed to create DB engine", exc_info=e)
        raise


def close_engine(engine: Engine) -> None:
    """Dispose of a SQLAlchemy engine and release its connection resources.

    Args:
        engine: The engine instance to dispose.
    """
    if engine:
        try:
            engine.dispose()
            logger.debug("DB engine disposed")
        except Exception as e:
            logger.exception("Error disposing DB engine", exc_info=e)
