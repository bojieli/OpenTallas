"""WF-1 11-14: a kit carrying a dead proof's pid / owner / identity restarts the proof instead of exiting 11."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SH = (HERE / "lec_async.sh").read_text()


def stale(tmp_path, files, identity_now="NOW"):
    k = tmp_path / "kit"
    k.mkdir()
    for n, v in files.items():
        (k / n).write_text(v)
    start = SH.index("stale_state() {")
    end = SH.index("\nbootstrap() {")
    fn = SH[start:end]
    script = f'identity() {{ echo {identity_now}; }}\n{fn}\nstale_state "{k}" docker-none\necho "rc=$?"\n'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    return p, k


def test_dead_pid_and_owner_are_cleared_not_exit_11(tmp_path):
    p, k = stale(tmp_path, {"lec_async.ready": "1\ncmd", "lec_async.pid": "999999", "lec_async.owner": "old", "lec_async.on": ""})
    assert "rc=0" in p.stdout and "stale proof state" in p.stderr
    assert not (k / "lec_async.ready").exists() and not (k / "lec_async.pid").exists() and not (k / "lec_async.owner").exists()


def test_live_watcher_pid_keeps_the_state(tmp_path):
    import os
    p, k = stale(tmp_path, {"lec_async.ready": "1\ncmd", "lec_async.pid": str(os.getpid())})
    assert (k / "lec_async.ready").exists() and "stale" not in p.stderr


def test_finished_proof_of_the_same_inputs_is_reused(tmp_path):
    p, k = stale(tmp_path, {"lec_async.ready": "1\ncmd", "lec_async.pid": "999999", "lec_async.done": "", "lec_async.identity": "NOW"})
    assert (k / "lec_async.ready").exists() and "stale" not in p.stderr


def test_finished_proof_of_other_inputs_is_cleared(tmp_path):
    p, k = stale(tmp_path, {"lec_async.ready": "1\ncmd", "lec_async.pid": "999999", "lec_async.done": "", "lec_async.identity": "OLD"})
    assert not (k / "lec_async.ready").exists() and not (k / "lec_async.identity").exists()


def test_moved_kit_is_stale_even_with_a_live_pid(tmp_path):
    import os
    p, k = stale(tmp_path, {"lec_async.ready": "1\ncmd", "lec_async.pid": str(os.getpid()), "lec_async.kit_path": "/elsewhere/kit"})
    assert not (k / "lec_async.ready").exists() and "moved from /elsewhere/kit" in p.stderr


def test_no_ready_file_is_a_no_op(tmp_path):
    p, k = stale(tmp_path, {"lec_async.pid": "999999"})
    assert "rc=0" in p.stdout and (k / "lec_async.pid").exists()


def _wait_returns(markers, pid=None, timeout=20):
    """run `lec_async.sh wait K` on a kit dir with on+ready and the given extra markers; True when it returns before the timeout (FABLE-FLOW-2355 B)"""
    import subprocess, tempfile, os
    from pathlib import Path
    script = Path(__file__).resolve().parent / "lec_async.sh"
    with tempfile.TemporaryDirectory() as k:
        for m in ("on", "ready") + tuple(markers):
            Path(k, "lec_async." + m).write_text("1\n")
        if pid is not None:
            Path(k, "lec_async.pid").write_text(str(pid))
        try:
            subprocess.run(["bash", str(script), "wait", k], env=dict(os.environ, OT_LEC_ASYNC_POLL="0.2"), timeout=timeout, capture_output=True, stdin=subprocess.DEVNULL)
            return True
        except subprocess.TimeoutExpired:
            return False


def test_wait_ends_on_any_terminal_marker():
    for m in ("rc", "abort", "done"):
        assert _wait_returns((m,), timeout=15), m


def test_wait_ends_when_the_watcher_pid_is_dead():
    import subprocess
    p = subprocess.Popen(["true"]); p.wait()
    assert _wait_returns((), pid=p.pid, timeout=15)


def test_wait_keeps_waiting_for_a_live_watcher():
    import subprocess
    live = subprocess.Popen(["sleep", "30"])
    try:
        assert not _wait_returns((), pid=live.pid, timeout=3)
    finally:
        live.kill()
