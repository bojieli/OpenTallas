"""FLOW-OPS-0900 (COORD 11-21): ot-delete and ot-auto-retire leave a per-file manifest of every tree they delete; a record, never a refusal."""
import gzip
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import delete_manifest as DM      # noqa: E402


def _tree(tmp):
    t = tmp / "lane" / "fable-pd-head-clk"
    (t / "ca2").mkdir(parents=True)
    (t / "ca2" / "ring_declared.json").write_text('{"ring": 1}\n')
    (t / "big.odb").write_bytes(b"x" * 3000)
    os.symlink("/nonexistent/target", t / "lnk")
    return t


def _read(m):
    with gzip.open(m, "rt") as fh:
        return [json.loads(x) for x in fh]


def test_manifest_lists_files_sizes_hashes_and_links(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", str(tmp_path / "mf"))
    t = _tree(tmp_path)
    m = DM.write(str(t), "ot-delete", sha_max_mb=0.002)              # 2 KiB: big.odb is "large"
    rows = _read(m)
    assert rows[0]["tree"] == str(t) and rows[0]["tool"] == "ot-delete" and rows[-1]["end"] and rows[-1]["files"] == 2
    by = {r["p"]: r for r in rows[1:-1]}
    assert by["ca2/ring_declared.json"]["sha256"] == hashlib.sha256(b'{"ring": 1}\n').hexdigest()
    assert by["big.odb"]["size"] == 3000 and by["big.odb"]["sha256"] is None and by["big.odb"]["why"] == "large"
    assert by["lnk"]["link"] == "/nonexistent/target"
    hits = DM.find("ca2/ring_declared.json")
    assert hits and hits[0][1] == str(t)


def test_budget_and_failure_never_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", str(tmp_path / "mf"))
    t = _tree(tmp_path)
    rows = _read(DM.write(str(t), "x", budget_s=-1))
    assert rows[-1]["truncated"] and all(r.get("sha256") is None for r in rows[1:-1] if "size" in r)
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", "/proc/forbidden/mf")
    assert DM.write(str(t), "x") is None                              # cannot write: None, no exception


def test_not_recorded_outside_srv_without_override(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_DELETE_MANIFEST_DIR", raising=False)
    assert DM.write("/tmp/ot-delete-manifest-not-srv", "x") is None          # a test temp dir outside /srv is never recorded


def test_ot_delete_writes_manifest_before_removing(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", str(tmp_path / "mf"))
    l = importlib.machinery.SourceFileLoader("ot_delete_mf", str(H / "ot-delete"))
    OD = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(OD)
    t = _tree(tmp_path)
    seen = []

    class G:
        @staticmethod
        def refuse(p, *a):
            return ""
    rc = OD.main([str(t)], guard=G, rmtree=lambda p: seen.append(list((tmp_path / "mf").rglob("*.jsonl.gz"))))
    assert rc == 0 and seen and seen[0]                                 # the manifest existed when rm ran


def test_auto_retire_strip_records_only_what_goes(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", str(tmp_path / "mf"))
    import auto_retire as AR
    t = _tree(tmp_path)
    (t / "reports").mkdir()
    (t / "reports" / "r.rpt").write_text("kept")
    AR.strip_keep_reports(str(t))
    assert (t / "reports" / "r.rpt").exists() and not (t / "ca2").exists()
    rows = _read(next((tmp_path / "mf").rglob("*.jsonl.gz")))
    ps = {r.get("p") for r in rows}
    assert "ca2/ring_declared.json" in ps and not any(p and p.startswith("reports") for p in ps)
