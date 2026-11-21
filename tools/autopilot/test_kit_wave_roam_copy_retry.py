"""FLOW-OPS-1000: a slow or failing snapshot copy drops the host for the stage, never ends the kit attempt"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave_roam as ROAM  # noqa: E402


def test_timeout_raised_by_the_runner_drops_the_host():
    def sh(host, cmd, timeout=600):
        if "flock" in cmd:
            raise subprocess.TimeoutExpired(cmd, timeout)
        if cmd.startswith("du "):
            return 0, "5"
        return (1, "") if "test -f" in cmd else (0, "")
    r = ROAM.Roamer(ROAM.Ops(sh), "/w", "epyc10", ["epyc10", "epyc7"])
    r.snaps, r.snap_verify = ["/srv/opentallas-scratch2/kit-store/snaps/ab"], (lambda sd: "true")
    assert r.before("pipeline") == ["epyc10"]
    assert any("epyc7 dropped (sync rc 125" in x and "timed out" in x for x in r.log), r.log


def test_snapshot_copy_resumes_and_waits_bounded():
    seen = []

    def sh(host, cmd, timeout=600):
        seen.append((cmd, timeout))
        return (1, "") if cmd.startswith("test -f") else (0, "")
    ROAM.Ops(sh).ensure_snap("epyc10", "epyc7", "/s/ab", lambda sd: "verify")
    cmd, to = seen[-1]
    assert f"flock -w {ROAM.SNAP_LOCK_WAIT_S}" in cmd and cmd.count("rsync -a --partial") == ROAM.COPY_TRIES
    assert to >= ROAM.SNAP_LOCK_WAIT_S + ROAM.COPY_TIMEOUT_S
