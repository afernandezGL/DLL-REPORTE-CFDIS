import logging
from turtle import color
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from config.config import OUTPUT_FOLDER, EDICOM_LOG_FOLDER_NAME
from scr.models import MONTH_MAP, edicom_log_column_names
from scr.stryles import BLUE, COLUMN_COLORS

logger = logging.getLogger(__name__)


def export_to_excel(
    consolidated_df: pd.DataFrame,
    edicom_resumen: pd.DataFrame,
    metadata_resumen: pd.DataFrame,
    factura_resumen: pd.DataFrame,
    date_: str,
) -> bool:
    """
    Exporta el DataFrame final y los resúmenes a un archivo Excel.

    Args:
        consolidated_df (pd.DataFrame): DataFrame final con los datos procesados.
        edicom_resumen (pd.DataFrame): Resumen de Edicom.
        metadata_resumen (pd.DataFrame): Resumen de metadata.
        factura_resumen (pd.DataFrame): Resumen de facturas.
        date_ (str): Fecha para nombrar el archivo de salida.
    Returns:
        bool: True si la exportación fue exitosa.
    """
    columns_to_export = [
        "RFC_EMISOR",
        "IDENTIFICADO",
        "ESTATUS_EDICOM",
        "TIPO DE COMPROBANTE",
        "SERIE",
        "FOLIO",
        "FECHA REAL",
        "FECHA DOCUMENTO",
        "UUID",
        "SUBTOTAL",
        "IVA",
        "TOTAL",
        "RECEPTOR RFC",
        "RECEPTOR NOMBRE",
        "METODO DE PAGO",
        "MONEDA",
        "CONTRATO",
        "OBSERVACIONES",
        "CONCEPTO",
        "TOTAL CONCEPTO",
        "CÓDIGO PRODUCTO",
        "Periodo",
        "Día",
        "Mes",
        "Fecha",
        "Tipo de cambio",
        "UUID METADADA",
        "TOTAL METADATA",
        "FECHA EMISIÓN METADATA",
        "PERIODO",
        "ESTATUS METADATA",
        "ESTATUS",
        "TOTAL CONCEPTO MXN",
        "ESTATUS REPORTE INTERNO VS METADATA",
        "FECHA DE CANCELACIÓN",
        "CONTRATO (CLAVE)",
        "PREFIJO",
        "% DE IVA",
        "% DE IVA POR CONCEPTO",
        "USO CFDI",
        "Contrato MID",
    ]

    output_dir = OUTPUT_FOLDER / date_
    year = date_.split("_")[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"Sofom - Amarre de facturación Invoicing con MTD SAT {date_}.xlsx"
    output_path = output_dir / file_name

    missing = [c for c in columns_to_export if c not in consolidated_df.columns]
    if missing:
        logger.warning(
            "Some columns to export are missing", extra={"missing_columns": missing}
        )

    cols_present = [c for c in columns_to_export if c in consolidated_df.columns]
    # consolidated_df[cols_present].to_excel(output_path, index=False)

    # Crear workbook
    wb = Workbook()

    # =====================================================
    # Sheet 1 - Salida
    # =====================================================

    ws_salida = wb.active
    ws_salida.title = "Salida"

    for row in dataframe_to_rows(
        consolidated_df[cols_present], index=False, header=True
    ):
        ws_salida.append(row)

    thin = Side(style="thin", color="000000")

    for cell in ws_salida[1]:
        color = COLUMN_COLORS.get(str(cell.value).strip())

        if color:
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor=color,
            )

        cell.font = Font(
            bold=True,
            color="000000",
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

        cell.border = Border(
            left=thin,
            right=thin,
            top=thin,
            bottom=thin,
        )

    # Filtros
    ws_salida.auto_filter.ref = ws_salida.dimensions

    # Congelar encabezado
    ws_salida.freeze_panes = "A2"

    # Altura encabezado
    ws_salida.row_dimensions[1].height = 45

    for column in ws_salida.columns:
        max_length = 0

        for cell in column:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        ws_salida.column_dimensions[get_column_letter(column[0].column)].width = min(
            max_length + 3, 40
        )

    # =====================================================
    # Sheet 2 - Resumen
    # =====================================================

    ws_resumen = wb.create_sheet("Resumen")

    edicom_color = COLUMN_COLORS["ESTATUS_EDICOM"]
    metadata_color = COLUMN_COLORS["ESTATUS METADATA"]
    factura_color = COLUMN_COLORS["USO CFDI"]

    # Título principal
    ws_resumen["A1"] = year
    ws_resumen["A1"].font = Font(size=16, bold=True)

    current_row = 3

    # =====================================================
    # EDICOM
    # =====================================================

    edicom_title_row = current_row

    ws_resumen.cell(current_row, 1, "EDICOM")
    ws_resumen.cell(current_row, 1).font = Font(size=12, bold=True)

    header_row = edicom_title_row + 1
    current_row += 1

    for row in dataframe_to_rows(edicom_resumen, index=False, header=True):
        ws_resumen.append(row)

    # Título EDICOM
    ws_resumen.cell(edicom_title_row, 1).fill = PatternFill(
        fill_type="solid",
        fgColor=edicom_color,
    )
    ws_resumen.cell(edicom_title_row, 1).font = Font(
        bold=True,
        size=12,
    )

    # Encabezados de la tabla EDICOM (fila 4)
    for cell in ws_resumen[header_row]:
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor=edicom_color,
        )
        cell.font = Font(bold=True)
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    current_row = ws_resumen.max_row + 2
    metadata_title_row = current_row

    # =====================================================
    # METADATA
    # =====================================================

    ws_resumen.cell(metadata_title_row, 1, "METADATA")
    ws_resumen.cell(metadata_title_row, 1).font = Font(size=12, bold=True)

    header_row = metadata_title_row + 1
    current_row += 1

    for row in dataframe_to_rows(metadata_resumen, index=False, header=True):
        ws_resumen.append(row)

    # Título METADATA
    ws_resumen.cell(metadata_title_row, 1).fill = PatternFill(
        fill_type="solid",
        fgColor=metadata_color,
    )
    ws_resumen.cell(metadata_title_row, 1).font = Font(
        bold=True,
    )

    # Encabezados de la tabla METADATA
    for cell in ws_resumen[header_row]:
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor=metadata_color,
        )

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    current_row = ws_resumen.max_row + 2
    factura_title_row = current_row

    # =====================================================
    # FACTURA
    # =====================================================

    ws_resumen.cell(factura_title_row, 1, "FACTURA")
    ws_resumen.cell(factura_title_row, 1).font = Font(size=12, bold=True)

    header_row = factura_title_row + 1
    current_row += 1

    for row in dataframe_to_rows(factura_resumen, index=False, header=True):
        ws_resumen.append(row)

    # Título FACTURA
    ws_resumen.cell(factura_title_row, 1).fill = PatternFill(
        fill_type="solid",
        fgColor=factura_color,
    )
    ws_resumen.cell(factura_title_row, 1).font = Font(
        bold=True,
        size=12,
    )

    # Encabezados de la tabla FACTURA
    for cell in ws_resumen[header_row]:
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor=factura_color,
        )

        cell.font = Font(
            bold=True,
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for column in ws_resumen.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)

        for cell in column:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))

        ws_resumen.column_dimensions[column_letter].width = max_length + 3

    # Format numeric columns
    for row in ws_resumen.iter_rows(min_row=1):
        for cell in row:

            # B and D -> counts
            if cell.column in [2,3,4,5]:
                cell.number_format = '#,##0'

    # =====================================================
    # Guardar archivo
    # =====================================================

    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"Sofom - Amarre de facturación Invoicing con MTD SAT {date_}.xlsx"

    wb.save(file_path)

    logger.info(
        "Exported consolidated dataframe to Excel",
        extra={"output_path": str(file_path), "rows": int(consolidated_df.shape[0])},
    )
    return True


def save_log(normalize_transformed_edicom_info_df: pd.DataFrame, date_: str) -> bool:
    """
    Exporta el DataFrame final a un archivo Excel.

    Args:
        consolidated_df (pd.DataFrame): DataFrame final con los datos procesados.
        date_ (str): Fecha para nombrar el archivo de salida.
    """
    year = date_.split("_")[0]
    month = date_.split("_")[1]
    month = MONTH_MAP[int(month)]
    output_dir = EDICOM_LOG_FOLDER_NAME / year
    file_name = f"Log_{month}.xlsx"
    output_path = output_dir / file_name

    normalize_transformed_edicom_info_df[edicom_log_column_names].to_excel(
        output_path, index=False
    )
    logger.info(
        "Exported log dataframe to Excel",
        extra={
            "output_path": str(output_path),
            "rows": int(normalize_transformed_edicom_info_df.shape[0]),
        },
    )
    return True
