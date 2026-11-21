"""FLOW-FIX-0100: the hub pushes rt/current's NOPROG pair, never its own stale lib copy."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noprog_stage as NS  # noqa: E402


def test_push_src_prefers_rt_current(tmp_path, monkeypatch):
    for fn in ("noprog_watchdog.py", "noprog_stage.py"):
        (tmp_path / fn).write_text("x")
    monkeypatch.setattr(NS, "RT_CURRENT", str(tmp_path))
    assert NS.push_src_dir() == str(tmp_path)
    (tmp_path / "noprog_stage.py").unlink()
    assert NS.push_src_dir() == NS.HERE
    monkeypatch.setattr(NS, "RT_CURRENT", str(tmp_path / "missing"))
    assert NS.push_src_dir() == NS.HERE
