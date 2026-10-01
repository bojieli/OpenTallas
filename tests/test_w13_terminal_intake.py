import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import w13_terminal_intake as intake


def fixture(tmp_path):
    root = tmp_path / "producer"
    root.mkdir()
    source = root / "rtl/top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n")
    log = tmp_path / "wrapper.log"
    log.write_text("worker finished rc=1\n")
    job = {"root": str(root), "block": "ot_gpu_tc16", "handle": {"pid": 5, "start_ticks": "old"},
           "source_commit": "pinned", "source_sha256": {"rtl/top.sv": intake.digest(source)},
           "wrapper_log": str(log), "initial_artifact_sha256": {}}
    return root, job


def test_failure_copied_byte_identically_without_qualification(tmp_path):
    root, job = fixture(tmp_path)
    corner = root / intake.CHIP / "corners/ot_gpu_tc16.json"
    corner.parent.mkdir(parents=True)
    corner.write_text('{"closed_signoff": false, "corners": {"SS": {"setup_wns_ps": -92.4}}}\n')
    original = corner.read_bytes()
    dest = tmp_path / "archive"
    row = intake.archive(job, dest, "configpin")
    assert row["fresh_corner_record"]
    assert row["producer_claimed_closed_signoff"] is False
    assert row["source_pin_mismatches"] == []
    assert (dest / corner.relative_to(root)).read_bytes() == original == corner.read_bytes()
    with pytest.raises(FileExistsError):
        intake.archive(job, dest, "configpin")


def test_inherited_record_is_not_new_terminal_evidence(tmp_path):
    root, job = fixture(tmp_path)
    corner = root / intake.CHIP / "corners/ot_gpu_tc16.json"
    corner.parent.mkdir(parents=True)
    corner.write_text(json.dumps({"closed_signoff": True}))
    job["initial_artifact_sha256"][str(corner.relative_to(root))] = intake.digest(corner)
    row = intake.archive(job, tmp_path / "archive", "configpin")
    assert not row["fresh_corner_record"]
    assert row["status"] == "producer_ended_without_new_corner_record"


def test_missing_record_and_source_drift_are_retained(tmp_path):
    root, job = fixture(tmp_path)
    (root / "rtl/top.sv").write_text("changed")
    row = intake.archive(job, tmp_path / "archive", "configpin")
    assert row["producer_claimed_closed_signoff"] is None
    assert row["source_pin_mismatches"] == ["rtl/top.sv"]


def test_reused_pid_is_not_original_live_wrapper(monkeypatch):
    monkeypatch.setattr(intake, "identity", lambda pid: {"pid": pid, "start_ticks": "new", "state": "S"})
    assert not intake.handle_live({"pid": 5, "start_ticks": "old"})
    assert intake.handle_live({"pid": 5, "start_ticks": "new"})


def test_collector_commits_only_new_archive_paths(tmp_path, monkeypatch):
    _, job = fixture(tmp_path)
    stream = tmp_path / "stream"
    stream.mkdir()
    subprocess.run(["git", "init", "-q", str(stream)], check=True)
    subprocess.run(["git", "config", "user.name", "Intake test"], cwd=stream, check=True)
    subprocess.run(["git", "config", "user.email", "intake@example.invalid"], cwd=stream, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "baseline"], cwd=stream, check=True)
    (stream / "unrelated.txt").write_text("must remain unstaged")
    config = {"tool_sha256": intake.digest(Path(intake.__file__)), "lock": str(tmp_path / "lock"),
              "output": str(stream / "archive"), "stream_worktree": str(stream),
              "events": str(tmp_path / "events"), "jobs": [job]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(intake, "handle_live", lambda handle: False)
    monkeypatch.setattr(sys, "argv", [intake.__file__, str(path)])
    intake.main()
    files = subprocess.check_output(["git", "show", "--format=", "--name-only", "HEAD"], cwd=stream, text=True).splitlines()
    assert files and all(name.startswith("archive/ot_gpu_tc16/") for name in files)
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=stream, text=True) == "?? unrelated.txt\n"
