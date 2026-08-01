import logging

import numpy as np
import pandas as pd
import pytest

from scr.integration import integrate_data, normalize_concepts


def build_row(
    concepto="servicio genérico",
    iva="16%",
    serie="",
    contrato="",
    moneda="MXN",
    determinacion_tc="20",
    concepto_column="CONCEPTO1",
    estatus_edicom="VIGENTE",
    estatus_metadata="VIGENTE",
    total_concepto=100,
    codigo_producto="01010101",
    observaciones="nota",
):
    row = {
        "UUID": "u1",
        "ESTATUS_EDICOM": estatus_edicom,
        "ESTATUS_METADATA": estatus_metadata,
        "MONEDA": moneda,
        "DETERMINACION_TC": determinacion_tc,
        "% DE IVA POR CONCEPTO": iva,
        "IVA": 10,
        "CONTRATO": contrato,
        "SERIE": serie,
        "OBSERVACIONES": observaciones,
        concepto_column: concepto,
        "TOTALCONCEPTO1": total_concepto,
        "CLAVEPRODSERVCONCEPTO1": codigo_producto,
    }
    return pd.DataFrame([row])


@pytest.fixture
def default_row():
    return build_row()


@pytest.mark.parametrize(
    "concepto,iva,serie,contrato,expected_prefix",
    [
        ("renta anticipada servicio", "16%", "", "", "REN ANT"),
        ("renta anticipada servicio", "0%", "", "", "REN ANT 0%"),
        ("renta mensual", "16%", "", "", "REN"),
        ("renta mensual", "0%", "", "", "REN 0%"),
        ("venta de equipo", "16%", "", "", "VEN"),
        ("venta de equipo", "0%", "", "", "VEN 0%"),
        ("seguro de vida cobertura", "16%", "", "", "SEG VIDA"),
        ("seguro equipo terrestre", "16%", "", "", "SEG"),
        ("subsidio institucional", "16%", "", "", "SUB"),
        ("comisión mercantil especial", "16%", "", "", "SUB"),
        ("gastos de administración mensual", "16%", "", "", "GAS"),
        ("opción a compra inmediata", "16%", "", "", "OPC"),
        ("osprey de servicio", "16%", "", "", "OSPREY"),
        ("prima seguros salud", "16%", "", "", "PRI"),
        ("reembolso parcial", "16%", "", "", "REEMBOLSO"),
        ("arrendamiento financiero largo", "16%", "", "", "ARR"),
        ("comisión por apertura primera", "16%", "", "", "COM"),
        ("otros servicios", "16%", "DE", "", "DE"),
        ("otros servicios", "16%", "", "contrato factoraje", "Factoraje"),
        ("otros servicios", "16%", "", "arrendamiento instalaciones", "SUBARR"),
        ("otros servicios", "16%", "", "UDI", "UDI"),
        ("desconocido", "10%", "", "", "OTH"),
    ],
)
def test_prefix_assignment_per_rule(concepto, iva, serie, contrato, expected_prefix):
    """Verify each prefix rule is assigned according to concept, IVA, serie, and contrato."""
    df = build_row(concepto=concepto, iva=iva, serie=serie, contrato=contrato)
    result = integrate_data(df)
    assert result.shape[0] == 1
    assert result["PREFIJO"].iloc[0] == expected_prefix


def test_concept1_alternative_column_name_is_supported():
    """Validate normalize_concepts accepts CONCEPT11 when CONCEPTO1 is absent."""
    row = {
        "UUID": "u1",
        "ESTATUS_EDICOM": "VIGENTE",
        "ESTATUS_METADATA": "VIGENTE",
        "MONEDA": "MXN",
        "DETERMINACION_TC": "20",
        "% DE IVA POR CONCEPTO": "16%",
        "IVA": 10,
        "CONTRATO": "",
        "SERIE": "",
        "OBSERVACIONES": "nota",
        "CONCEPT11": "venta industrial",
        "TOTALCONCEPTO1": 150,
        "CLAVEPRODSERVCONCEPTO1": "02020202",
    }
    normalized = normalize_concepts(pd.DataFrame([row]))
    assert normalized.shape[0] == 1
    assert normalized["CONCEPTO"].iloc[0] == "venta industrial"
    assert normalized["TOTAL CONCEPTO"].iloc[0] == 150
    assert normalized["CÓDIGO PRODUCTO"].iloc[0] == "02020202"


def test_normalize_concepts_returns_empty_when_no_concept_columns():
    """Ensure normalize_concepts returns an empty DataFrame when no concept columns exist."""
    empty_df = pd.DataFrame({"UUID": ["u1"], "MONEDA": ["MXN"]})
    normalized = normalize_concepts(empty_df)
    assert normalized.empty


def test_integration_handles_blank_concept_and_missing_optional_fields():
    """Verify blank concept strings and missing contract/serie result in OTH without failing."""
    df = build_row(concepto="", iva="16%", serie="", contrato="", observaciones="")
    result = integrate_data(df)
    assert result["PREFIJO"].iloc[0] == "OTH"
    assert result["Tipo de cambio"].iloc[0] == 1


def test_total_concept_mxn_remains_zero_given_rename_logic():
    """Capture current logic: TOTAL CONCEPTO MXN remains zero because ESTATUS_METADATA is renamed before calculation."""
    df = build_row(
        concepto="venta de equipo",
        iva="16%",
        moneda="USD",
        determinacion_tc="25",
        total_concepto=50,
    )
    result = integrate_data(df)
    assert result["TOTAL CONCEPTO MXN"].iloc[0] == 0
    assert "ESTATUS" in result.columns
    assert "ESTATUS_METADATA" not in result.columns


def test_integrate_data_raises_key_error_when_required_columns_missing(default_row):
    """Ensure integrate_data fails fast if a required status column is absent."""
    df = default_row.drop(columns=["ESTATUS_EDICOM"])
    with pytest.raises(KeyError):
        integrate_data(df)


def test_integrate_data_logs_error_when_status_metadata_column_missing(default_row, caplog):
    """Check current behavior when ESTATUS_METADATA is missing: error is logged and exception is raised."""
    caplog.set_level(logging.ERROR)
    df = default_row.drop(columns=["ESTATUS_METADATA"])
    with pytest.raises(KeyError):
        integrate_data(df)
    assert any(
        "Error computing ESTATUS REPORTE INTERNO VS METADATA" in record.message
        for record in caplog.records
    )
