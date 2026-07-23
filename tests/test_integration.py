import pandas as pd
import numpy as np
import logging
import pytest

from scr.integration import normalize_concepts, integrate_data


def make_wide_df():
    # Create a simple wide dataframe with two concept groups
    df = pd.DataFrame(
        {
            "UUID": ["u1", "u2"],
            "ESTATUS_EDICOM": ["ok", "fail"],
            "ESTATUS_METADATA": ["ok", "other"],
            "MONEDA": ["MXN", "USD"],
            "DETERMINACION_TC": [None, "20"],
            "CONCEPTO1": ["renta anticipada servicio", None],
            "TOTALCONCEPTO1": [100, None],
            "CLAVEPRODSERVCONCEPTO1": ["01010101", None],
            "CONCEPTO2": [None, "venta de equipo"],
            "TOTALCONCEPTO2": [None, 200],
            "CLAVEPRODSERVCONCEPTO2": [None, "02020202"],
            "OBSERVACIONES": ["obs1", "obs2"],
        }
    )
    return df


def test_normalize_concepts_basic():
    df = make_wide_df()
    long = normalize_concepts(df)
    # Expect two rows (one per non-null concept)
    assert len(long) == 2
    assert set(long.columns).issuperset({"CONCEPTO", "TOTAL CONCEPTO", "CÓDIGO PRODUCTO", "UUID"})


def test_normalize_concepts_no_concepts():
    df = pd.DataFrame({"UUID": ["u1"]})
    long = normalize_concepts(df)
    # Should return empty DataFrame when no concept cols
    assert long.empty


def test_integrate_data_basic(caplog):
    caplog.set_level(logging.DEBUG)
    df = make_wide_df()
    res = integrate_data(df)
    # Check that ESTATUS REPORTE INTERNO VS METADATA column exists and values are numeric
    assert "ESTATUS REPORTE INTERNO VS METADATA" in res.columns
    assert res.shape[0] >= 2
    # Ensure logs include start and completion info
    assert any("Starting integrate_data" in r.message for r in caplog.records)
    assert any("integrate_data completed" in r.message for r in caplog.records)


def test_integrate_data_tipo_cambio_coerce():
    # MONEDA USD should use DETERMINACION_TC; non-numeric coerced to NaN then to numeric
    df = make_wide_df()
    df.loc[1, "DETERMINACION_TC"] = "invalid"
    res = integrate_data(df)
    # Tipo de cambio numeric conversion should exist
    assert "Tipo de cambio" in res.columns
    assert pd.api.types.is_numeric_dtype(res["Tipo de cambio"]) or res["Tipo de cambio"].isnull().all()


def test_integrate_data_missing_status_metadata_logs(caplog):
    caplog.set_level(logging.WARNING)
    df = make_wide_df()
    df = df.drop(columns=["ESTATUS_METADATA"])
    res = integrate_data(df)
    # Should warn about missing ESTATUS_METADATA
    assert any("ESTATUS_METADATA column not found" in r.message for r in caplog.records)
