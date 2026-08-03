import pandas as pd

from scr import orchestrator


def test_build_report_exports_report_for_client_format(monkeypatch):
    def fake_load_data(date_):
        return (
            pd.DataFrame({"a": [1]}),
            pd.DataFrame({"b": [2]}),
            pd.DataFrame({"c": [3]}),
            pd.DataFrame({"d": [4]}),
        )

    def fake_transform_data(raw_metadata, raw_edicom, raw_cfdi, edicom_log, date_):
        return (
            pd.DataFrame({"e": [5]}),
            pd.DataFrame({"f": [6]}),
            pd.DataFrame({"g": [7]}),
        )

    def fake_consolidate_info(transformed_edicom, transformed_metadata, transformed_cfdi):
        return pd.DataFrame({"h": [8]})

    def fake_get_summary(consolidated_df):
        return (
            pd.DataFrame({"summary": ["edicom"]}),
            pd.DataFrame({"summary": ["metadata"]}),
            pd.DataFrame({"summary": ["factura"]}),
        )

    export_calls = []

    def fake_export(consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_):
        export_calls.append((consolidated_df, edicom_resumen, metadata_resumen, factura_resumen, date_))
        return True

    monkeypatch.setattr(orchestrator, "load_data", fake_load_data)
    monkeypatch.setattr(orchestrator, "transform_data", fake_transform_data)
    monkeypatch.setattr(orchestrator, "consolidate_info", fake_consolidate_info)
    monkeypatch.setattr(orchestrator, "get_summary", fake_get_summary)
    monkeypatch.setattr(orchestrator, "export_to_client_format", fake_export)

    result = orchestrator.build_report("2026_01", "cliente")

    assert result is True
    assert len(export_calls) == 1
    assert export_calls[0][4] == "2026_01"
