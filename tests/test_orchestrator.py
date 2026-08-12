import pandas as pd

from scr import orchestrator
from scr.models import RawResult, TransformedResult


def test_build_report_exports_report_for_client_format(monkeypatch):
    empty = pd.DataFrame()
    raw_result = RawResult(empty, empty, empty)
    transformed_result = TransformedResult(empty, empty, empty, empty, empty)
    summary_result = object()
    differences_result = object()
    export_calls = []

    monkeypatch.setattr(
        orchestrator,
        "load_data",
        lambda date_: (empty, raw_result),
    )
    monkeypatch.setattr(
        orchestrator,
        "transform_data",
        lambda raw, edicom_log, date_: transformed_result,
    )
    monkeypatch.setattr(
        orchestrator,
        "consolidate_info",
        lambda transformed: empty,
    )
    monkeypatch.setattr(
        orchestrator,
        "get_summary",
        lambda consolidated, metadata, factura: summary_result,
    )
    monkeypatch.setattr(
        orchestrator,
        "get_differences",
        lambda consolidated, transformed: differences_result,
    )
    monkeypatch.setattr(
        orchestrator,
        "reload_differences",
        lambda transformed, differences, date_: differences_result,
    )
    monkeypatch.setattr(orchestrator, "save_log", lambda dataframe, date_: True)

    def fake_export(consolidated_df, summaries, differences, date_):
        export_calls.append((consolidated_df, summaries, differences, date_))
        return True

    monkeypatch.setattr(orchestrator, "export_to_client_format", fake_export)

    result = orchestrator.build_report("2026_01", "cliente")

    assert result is True
    assert len(export_calls) == 1
    assert export_calls[0][3] == "2026_01"
    assert export_calls[0][1] is summary_result
    assert export_calls[0][2] is differences_result
