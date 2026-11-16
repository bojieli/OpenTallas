"""FLOW-HEALTH-1 11-15: the ingest fails fast without the AGIdock key (was a JSONDecodeError after a 7-minute scan, hourly, for three days)"""
import importlib.util
import os
import pathlib

spec = importlib.util.spec_from_file_location("ssi", str(pathlib.Path(__file__).resolve().parents[1] / "signed_store_ingest.py"))
ssi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssi)


def test_missing_key_exits_2_with_a_clear_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ssi, "AGI_KEY", str(tmp_path / "no-such-key"))
    monkeypatch.setattr(ssi, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(ssi, "LAST", tmp_path / "last.json")
    monkeypatch.setattr(ssi.sys, "argv", ["ingest"])
    called = []
    monkeypatch.setattr(ssi.rtp, "scan_host", lambda h: called.append(h) or [])
    assert ssi.main() == 2
    assert "AGIdock key missing on this host" in capsys.readouterr().out
    assert called == []                                   # no scan was started
    assert "AGIdock key missing" in (tmp_path / "last.json").read_text()


def test_dry_run_does_not_need_the_key(tmp_path, monkeypatch):
    monkeypatch.setattr(ssi, "AGI_KEY", str(tmp_path / "no-such-key"))
    monkeypatch.setattr(ssi, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(ssi, "LAST", tmp_path / "last.json")
    monkeypatch.setattr(ssi.sys, "argv", ["ingest", "--dry"])
    monkeypatch.setattr(ssi, "ORDER", ("h1",))
    monkeypatch.setattr(ssi.rtp, "scan_host", lambda h: [])
    monkeypatch.setattr(ssi, "marker_sweep", lambda f: [])
    monkeypatch.setattr(ssi.ss, "load_records", lambda *a, **k: ([], {}))
    monkeypatch.setattr(ssi.ss, "read_manifest", lambda *a, **k: [])
    assert ssi.main() in (0, 1)
