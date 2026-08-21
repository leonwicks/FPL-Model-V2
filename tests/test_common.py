import ssl
from pathlib import Path

import pandas as pd

from football_data.common import http
from football_data.common.http import HttpPayload
from football_data.common.io import RawStore, upsert_parquet
from football_data.common.schemas import SchemaRegistry


def test_raw_files_are_immutable_and_checksummed(tmp_path: Path):
    store = RawStore(tmp_path)
    payload = HttpPayload(
        "https://x", b"abc", 200, "text/plain", "2025-01-01T12:00:00Z", 1
    )
    one = store.write("source", "2024-25", "file.txt", payload)
    two = store.write("source", "2024-25", "file.txt", payload)
    assert one.path != two.path
    assert one.sha256 == two.sha256


def test_parquet_upsert_is_idempotent(tmp_path: Path):
    path = tmp_path / "table.parquet"
    incoming = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})
    upsert_parquet(incoming, path, ["id"])
    result = upsert_parquet(incoming, path, ["id"])
    assert len(result) == 2


def test_schema_drift_tracks_new_and_missing_columns(tmp_path: Path):
    registry = SchemaRegistry(tmp_path)
    registry.compare("sample", {"id": "int64", "old": "object"}, critical=["id"])
    drift = registry.compare(
        "sample", {"id": "int64", "new": "float64"}, critical=["id"]
    )
    assert drift.new_columns == ["new"]
    assert drift.missing_columns == ["old"]


def test_windows_tls_uses_system_store_without_disabling_verification(monkeypatch):
    monkeypatch.setattr(http.sys, "platform", "win32")
    context = http._tls_verify()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT
