"""Admission waiters share one lock inode and honor bounded lock attempts."""
import fcntl
from pathlib import Path
import subprocess
import time

OT = Path(__file__).with_name("ot-heavy")


def run_lock(directory, max_wait=10, wait=1):
    script = OT.read_text()
    start = script.index("ot_heavy_admit_lock() {")
    end = script.index("\n}\n", start) + 3
    return subprocess.Popen(
        [
            "bash", "-c",
            'D=$1 MAXWAIT=$2 OT_HEAVY_LOCK_WAIT_S=$3 T0=$(date +%s)\n'
            + script[start:end]
            + '\not_heavy_admit_lock && echo GOT\n',
            "test", str(directory), str(max_wait), str(wait),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_free_lock_is_taken(tmp_path):
    waiter = run_lock(tmp_path)
    output, error = waiter.communicate(timeout=5)
    assert waiter.returncode == 0 and output.strip() == b"GOT", error


def test_live_lock_times_out_without_replacing_the_inode(tmp_path):
    path = tmp_path / "admit.lock"
    with path.open("a") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)
        inode = path.stat().st_ino
        waiter = run_lock(tmp_path, max_wait=1, wait=30)
        output, _ = waiter.communicate(timeout=5)
        assert waiter.returncode == 1 and b"GOT" not in output
        assert path.stat().st_ino == inode


def test_waiter_refuses_a_retired_inode(tmp_path):
    path = tmp_path / "admit.lock"
    with path.open("a") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)
        waiter = run_lock(tmp_path, wait=10)
        fd = Path(f"/proc/{waiter.pid}/fd/8")
        for _ in range(250):
            if fd.exists() and fd.samefile(path):
                break
            time.sleep(0.01)
        else:
            waiter.kill()
            waiter.communicate(timeout=5)
            raise AssertionError("waiter never opened the original inode")
        path.rename(tmp_path / "retired.lock")
        path.touch()
        fcntl.flock(holder, fcntl.LOCK_UN)
        output, _ = waiter.communicate(timeout=5)
        assert waiter.returncode == 1 and b"GOT" not in output
    next_waiter = run_lock(tmp_path)
    output, error = next_waiter.communicate(timeout=5)
    assert next_waiter.returncode == 0 and output.strip() == b"GOT", error
