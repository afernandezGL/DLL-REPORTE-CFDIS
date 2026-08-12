from dataclasses import dataclass

import pandas as pd


@dataclass
class ReportResult:
    """Container for the source data grouped by system in a report section.

    Attributes:
        edicom: Edicom rows associated with the report slice.
        metadata: Metadata rows associated with the report slice.
        factura: CFDI rows associated with the report slice.
    """

    edicom: pd.DataFrame
    metadata: pd.DataFrame
    factura: pd.DataFrame


@dataclass
class SummaryResult(ReportResult):
    """Summary data for the three source systems.

    This dataclass mirrors the base report structure but carries the aggregated
    statistics produced for each system.
    """


@dataclass
class RawResult(ReportResult):
    """Raw data extracted from the source systems before transformation."""


@dataclass
class TransformedResult(ReportResult):
    """Normalized source datasets after transformation and filtering.

    Attributes:
        filtered_metadata: Metadata rows filtered by the requested period.
        normalize_edicom: Edicom rows normalized into a long concept format.
    """

    filtered_metadata: pd.DataFrame
    normalize_edicom: pd.DataFrame


@dataclass
class ConsolidationResult:
    """Container for the consolidated report dataframe."""

    consolidated: pd.DataFrame


@dataclass
class DifferencesUUIDResult:
    """Identifier lists that describe which UUIDs differ per source system.

    Attributes:
        edicom: UUIDs present only in Edicom or missing in the other systems.
        metadata: UUIDs present only in metadata or missing in the other systems.
        facturas: UUIDs present only in CFDI data or missing in the other systems.
    """

    edicom: list[str]
    metadata: list[str]
    facturas: list[str]


@dataclass
class DifferencesResult:
    """Result set for the UUID and subtotal comparison pass.

    Attributes:
        uuid: DataFrame with the UUID-level comparison across source systems.
        subtotal: DataFrame with all subtotal comparisons.
        relevant_uuid: Structured UUID differences by source system.
        relevant_subtotal: Relevant subtotal differences for report display.
    """

    uuid: pd.DataFrame
    subtotal: pd.DataFrame
    relevant_uuid: DifferencesUUIDResult
    relevant_subtotal: pd.DataFrame


@dataclass
class DifferencesReportResult:
    """Structured collection of difference tables used in Excel exports.

    Attributes:
        consolidated: Full UUID difference table for the consolidated dataset.
        comparative_subtotals: Subtotal comparison table for all rows.
        relevant_comparative_subtotals: Relevant subtotal differences.
        uuid: Report slices for uuid differences by source system.
        subtotal: Report slices for subtotal differences by source system.
    """

    consolidated: pd.DataFrame
    comparative_subtotals: pd.DataFrame
    relevant_comparative_subtotals: pd.DataFrame
    uuid: ReportResult
    subtotal: ReportResult


raw_edicom_column_names = [
    "ESTATUS",
    "TIPODECOMPROBANTE",
    "SERIE",
    "FOLIO",
    "FECHAREAL",
    "FECHADOCUMENTO",
    "UUID",
    "SUBTOTAL",
    "IVA",
    "TOTAL",
    "RECEPTORRFC",
    "RECEPTOR NOMBRE",
    "METODOPAGO",
    "MONEDA",
    "CONTRATO",
    "OBSERVACIONES",
    # "CONCEPTO1",
    # "TOTALCONCEPTO1",
    # "CLAVEPRODSERVCONCEPTO1",
]

patterns_raw_edicom_column_names = [
    "CONCEPTO",  # Careful with this pattern, it can match other columns that contain the word "CONCEPT"
    "CONCEPT",
    "TOTALCONCEPTO",
    "CLAVEPRODSERVCONCEPTO",
]

normalized_edicom_column_names = [
    "ESTATUS",
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
    # "CONCEPTO",
    # "TOTAL CONCEPTO",
    # "CÓDIGO PRODUCTO",
]

patterns_normalized_edicom_column_names = [
    "CONCEPTO",
    "CONCEPTO",
    "TOTAL CONCEPTO",
    "CÓDIGO PRODUCTO",
]

edicom_log_column_names = [
    "ESTATUS",
    "TIPODECOMPROBANTE",
    "SERIE",
    "FOLIO",
    "FECHAREAL",
    "FECHADOCUMENTO",
    "UUID",
    "SUBTOTAL",
    "IVA",
    "TOTAL",
    "RECEPTORRFC",
    "RECEPTOR NOMBRE",
    "METODOPAGO",
    "MONEDA",
    "CONTRATO",
    "OBSERVACIONES",
    "CONTRATO (CLAVE)",
    "% DE IVA",
    "Contrato MID",
    "CONCEPTO",
    "TOTAL CONCEPTO",
    "CÓDIGO PRODUCTO",
]

edicom_id = "UUID"
metadata_id = "Uuid"
cfdi_id = "UUID"

MONTH_MAP = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

raw_metadata_column_names = [
    "RfcEmisor",
    "Uuid",
    "Monto",
    "FechaEmision",
    "Estatus",
    "FechaCancelacion",
]

normalized_metadata_column_names = [
    "RfcEmisor",
    "UUID METADATA",
    "TOTAL METADATA",
    "FECHA EMISIÓN METADATA",
    "Estatus",
    "FECHA DE CANCELACIÓN",
]

CFDI_USE_MAP = {
    "G01": "Adquisición de mercancías",
    "G02": "Devoluciones, descuentos o bonificaciones",
    "G03": "Gastos en general",
    "I01": "Construcciones",
    "I02": "Mobiliario y equipo de oficina por inversiones",
    "I03": "Equipo de transporte",
    "I04": "Equipo de cómputo y accesorios",
    "I05": "Dados, troqueles, moldes, matrices y herramental",
    "I06": "Comunicaciones telefónicas",
    "I07": "Comunicaciones satelitales",
    "I08": "Otra maquinaria y equipo",
    "D01": "Honorarios médicos, dentales y gastos hospitalarios",
    "D02": "Gastos médicos por incapacidad o discapacidad",
    "D03": "Gastos funerales",
    "D04": "Donativos",
    "D05": "Intereses reales efectivamente pagados por créditos hipotecarios",
    "D06": "Aportaciones voluntarias al SAR",
    "D07": "Primas por seguros de gastos médicos",
    "D08": "Gastos de transportación escolar obligatoria",
    "D09": "Depósitos en cuentas para el ahorro",
    "D10": "Pagos por servicios educativos (colegiaturas)",
    "S01": "Sin efectos fiscales",
    "CP01": "Pagos",
    "CN01": "Nómina",
}

prefixes = [
    "SUBARR",
    "REN ANT",
    "REN ANT 0%",
    "REN",
    "REN 0%",
    "DE",
    "UDI",
    "VEN",
    "VEN 0%",
    "SEG VIDA",
    "PRI",
    "SUB",
    "GAS",
    "OPC",
    "OSPREY",
    "SEG",
    "REEMBOLSO",
    "ARR",
    "COM",
    "Factoraje",
    "INT MOR",
    "INT",
    "INT ARR FIN",
    "INT 0%",
    "INT EXE",
    "SUB",
]

MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

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
    "UUID METADATA",
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
