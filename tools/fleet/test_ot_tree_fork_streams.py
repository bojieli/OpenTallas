"""OPS-SUPPORT-R1 11-23: ot-tree-fork starts all fetch streams at once and uses more streams for a far (high RTT) source."""
import importlib.machinery, importlib.util, os, pathlib, stat, time
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_tree_fork_streams", str(H / "ot-tree-fork"))
TF = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_tree_fork_streams", l)); l.exec_module(TF)


def test_streams_for_far_source_and_explicit_override(monkeypatch):
    monkeypatch.delenv("OT_TREE_FORK_STREAMS", raising=False)
    assert TF.streams_for("far", rtt=lambda h: 120.0) == max(TF.STREAMS, TF.STREAMS_FAR) == 2
    assert TF.streams_for("near", rtt=lambda h: 0.4) == TF.STREAMS
    assert TF.streams_for("unknown", rtt=lambda h: None) == TF.STREAMS
    monkeypatch.setenv("OT_TREE_FORK_STREAMS", "2")
    assert TF.streams_for("far", rtt=lambda h: 120.0) == TF.STREAMS


def test_fetch_parallel_starts_every_stream_before_the_first_one_reads(tmp_path, monkeypatch):
    src = tmp_path / "src"; dst = tmp_path / "dst"; src.mkdir(); dst.mkdir()
    for i in range(40):
        (src / f"f{i}").write_bytes(b"x" * (1000 + i))
    # fake ssh: "ssh <options> HOST CMD" -> run CMD locally, but sleep 1 s before reading the file list, like a slow far link
    fake = tmp_path / "fakessh"
    fake.write_text("#!/bin/bash\nwhile [[ $1 == -* ]]; do shift; done\nshift\nsleep 1\nexec bash -c \"$*\"\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(TF, "SSH", [str(fake)])
    big = [(10_000_000, f"pad{i}") for i in range(0)]
    t0 = time.time()
    TF.fetch_parallel("h", str(src), str(dst), 4, out=lambda *_: None)
    took = time.time() - t0
    assert sorted(os.listdir(dst)) == sorted(os.listdir(src))
    assert took < 3.5, took      # four serial 1 s start-ups would take >= 4 s


def test_defaults_are_two_streams_and_settings_reach_a_remote_fork(monkeypatch):
    """E11-IO-STALL-1124 (FAM-S81-COL-H9R0): ot-tree-fork --host ran the remote side with its own 12-stream default"""
    assert (TF.STREAMS, TF.STREAMS_FAR) == (2, 2) or "OT_TREE_FORK_STREAMS" in __import__("os").environ
    cmd = TF.remote_cmd(["/a", "/b", "--jobs", "2"], {"OT_TREE_FORK_STREAMS": "2", "OT_TREE_FORK_MAX_JOBS": "2", "OT_LANE": "L X", "HOME": "/h"})
    assert cmd == "OT_LANE='L X' OT_TREE_FORK_STREAMS=2 OT_TREE_FORK_MAX_JOBS=2 python3 -I - /a /b --jobs 2"
    assert TF.remote_cmd(["/a", "/b"], {}) == "python3 -I - /a /b"
    seen = {}
    monkeypatch.setattr(TF.subprocess, "run", lambda args, **k: seen.setdefault("args", args) and type("R", (), {"returncode": 0})())
    monkeypatch.setenv("OT_TREE_FORK_STREAMS", "1")
    assert TF.main(["/a", "/b", "--host", "hostq", "--jobs", "1"]) == 0
    assert seen["args"][-2] == "hostq" and seen["args"][-1].startswith("OT_TREE_FORK_STREAMS=1 ") and seen["args"][-1].endswith("/a /b --jobs 1")
