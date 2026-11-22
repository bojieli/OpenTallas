"""FLOW-FLEET-R2 S1: an invalid UTF-8 byte in a coord file never makes read_coord raise (it skipped hold recompile, tree switch, UNBLOCK, LOOP-GAPS for ~1 h)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP      # noqa: E402

BAD = b"- 2026-11-22 02:55 ok\n- caf\x94 bad byte\n- tail\n"


def test_coord_files_dir_bad_byte_is_replaced_and_warned_once(tmp_path, monkeypatch):
    (tmp_path / "lanes" / "posts").mkdir(parents=True)
    (tmp_path / "lanes" / "posts" / "COORD.md").write_bytes(BAD)
    logs = []
    monkeypatch.setattr(AP, "COORD_FILES", str(tmp_path))
    monkeypatch.setattr(AP, "log", logs.append)
    monkeypatch.setattr(AP, "_COORD_BAD_UTF8", set())
    t = AP.read_coord("lanes/posts/COORD.md")
    assert "tail" in t and "\ufffd" in t and t.startswith("- 2026-11-22")
    AP.read_coord("lanes/posts/COORD.md")
    assert len(logs) == 1 and "WARN" in logs[0] and "0x94" in logs[0] and "offset" in logs[0]


def test_git_show_path_bad_byte_does_not_raise(monkeypatch):
    monkeypatch.setattr(AP, "COORD_FILES", "")
    monkeypatch.setattr(AP, "log", lambda m: None)
    monkeypatch.setattr(AP, "_COORD_BAD_UTF8", set())
    monkeypatch.setattr(AP.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 0, BAD, b""))
    assert "tail" in AP.read_coord("lanes/COORD-REVIEW-QUEUE.md")
    monkeypatch.setattr(AP.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 128, b"", b"missing"))
    assert AP.read_coord("lanes/x.md") == ""
