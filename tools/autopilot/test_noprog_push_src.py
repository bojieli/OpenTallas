"""FLOW-FIX-0100: the hub pushes rt/current's NOPROG pair, never its own stale lib copy."""
import subprocess
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



def test_approved_stage_deploy_refreshes_only_an_existing_action_watchdog(tmp_path, monkeypatch):
    src = tmp_path / "published"
    src.mkdir()
    for name in ("noprog_stage.py", "noprog_watchdog.py"):
        (src / name).write_text("# approved\n")
    action = tmp_path / "ot-noprog-watchdog"
    monkeypatch.setattr(NS, "RT_CURRENT", str(src))
    monkeypatch.setattr(NS, "LIB", str(tmp_path / "lib"))
    monkeypatch.setattr(NS, "ACTION_WATCHDOG", str(action))

    def run_host(host, cmd, inp=None, timeout=0):
        if cmd.endswith(" scan"):
            return subprocess.CompletedProcess(cmd, 0, "[]", "")
        return subprocess.run(["bash", "-c", cmd], input=inp, capture_output=True, text=True, timeout=timeout)

    monkeypatch.setattr(NS, "run_host", run_host)
    assert NS.push_and_scan("epyc7") == ("epyc7", [])
    assert not action.exists()
    action.write_text("# stale\n")
    action.chmod(0o755)
    assert NS.push_and_scan("epyc7") == ("epyc7", [])
    assert action.read_text() == "# approved\n"
    old_inode = action.stat().st_ino
    assert NS.push_and_scan("epyc7") == ("epyc7", [])
    assert action.stat().st_ino == old_inode

    # A local-lib fallback can still feed the advisory scan, but it cannot refresh the action timer.
    monkeypatch.setattr(NS, "RT_CURRENT", str(tmp_path / "absent"))
    monkeypatch.setattr(NS, "HERE", str(src))
    (src / "noprog_watchdog.py").write_text("# local fallback\n")
    assert NS.push_and_scan("epyc7") == ("epyc7", [])
    assert action.read_text() == "# approved\n"
