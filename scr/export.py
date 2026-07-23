
import logging
import pandas as pd
from pathlib import Path
from config.config import OUTPUT_FOLDER

logger = logging.getLogger(__name__)

def export_to_excel(consolidated_df: pd.DataFrame, date_: str) -> bool:
    """
    Exporta el DataFrame final a un archivo Excel.

    Args:
        consolidated_df (pd.DataFrame): DataFrame final con los datos procesados.
        date_ (str): Fecha para nombrar el archivo de salida.
    """
    columns_to_export = [
        'ESTATUS_EDICOM', 'TIPO DE COMPROBANTE', 'SERIE', 'FOLIO', 'FECHA REAL',
        'FECHA DOCUMENTO', 'UUID', 'SUBTOTAL', 'IVA', 'TOTAL', 'RECEPTOR RFC',
        'RECEPTOR NOMBRE', 'METODO DE PAGO', 'MONEDA', 'CONTRATO',
        'OBSERVACIONES', 'CONCEPTO', 'TOTAL CONCEPTO', 'CÓDIGO PRODUCTO',
        'Periodo', 'Día', 'Mes', 'Fecha', 'Tipo de cambio', 'UUID METADADA', 'TOTAL METADATA', 
        'FECHA EMISIÓN METADATA', 'PERIODO',  'ESTATUS METADATA',
        'ESTATUS', 'TOTAL CONCEPTO MXN',
        'ESTATUS REPORTE INTERNO VS METADATA', 'FECHA DE CANCELACIÓN',
        'CONTRATO (CLAVE)', 'PREFIJO', '% DE IVA', '% DE IVA POR CONCEPTO', 
        'USO CFDI','Contrato MID'
    ]

    output_dir = OUTPUT_FOLDER / date_
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"Sofom - Amarre de facturación Invoicing con MTD SAT {date_}.xlsx"
    output_path = output_dir / file_name

    missing = [c for c in columns_to_export if c not in consolidated_df.columns]
    if missing:
        logger.warning("Some columns to export are missing", extra={"missing_columns": missing})

    cols_present = [c for c in columns_to_export if c in consolidated_df.columns]
    consolidated_df[cols_present].to_excel(output_path, index=False)
    logger.info("Exported consolidated dataframe to Excel", extra={"output_path": str(output_path), "rows": int(consolidated_df.shape[0])})
    return True