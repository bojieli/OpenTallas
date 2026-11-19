"""COPY-DEDUPE-1119: N kits needing the same snapshot on the same destination run ONE rsync; the others wait on the lock and find it verified."""
import os, stat, subprocess, sys, threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave_roam as R


def stubs(tmp):
    b = tmp / "bin"; b.mkdir()
    (b / "ssh").write_text('#!/bin/bash\nwhile [ "$1" = -o ]; do shift 2; done\nshift\nexec bash -c "$*"\n')
    (b / "rsync").write_text('#!/bin/bash\nsleep 0.6\necho copy >> "$COPYLOG"\nsrc="${@: -2:1}"; dst="${@: -1}"; dst="${dst#*:}"\nmkdir -p "$dst"; cp -a "$src"/. "$dst"/ 2>/dev/null; exit 0\n')
    for f in ("ssh", "rsync"):
        os.chmod(b / f, os.stat(b / f).st_mode | stat.S_IEXEC)
    return b


def test_six_concurrent_kits_run_one_copy_and_one_verify(tmp_path, monkeypatch):
    b = stubs(tmp_path)
    sd = tmp_path / "snap" / ("a" * 40)
    sd.mkdir(parents=True); (sd / "f").write_text("x")
    log = tmp_path / "copy.log"; vlog = tmp_path / "verify.log"
    monkeypatch.setenv("PATH", f"{b}:{os.environ['PATH']}"); monkeypatch.setenv("COPYLOG", str(log))

    def sh(host, cmd):
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    ops = R.Ops(sh)
    dst_sd = str(sd)           # the stubs make "dst" the same machine, same path: .verified absent until verify runs
    out = []
    verify = lambda d: f"echo v >> {vlog}; touch {d}/.verified"
    ts = [threading.Thread(target=lambda: out.append(ops.ensure_snap("hubA", "epyc7", dst_sd, verify))) for _ in range(6)]
    [t.start() for t in ts]; [t.join(60) for t in ts]
    assert [o[0] for o in out] == [0] * 6
    assert log.read_text().count("copy") == 1, log.read_text()                 # ONE rsync, not six
    assert vlog.read_text().count("v") == 1                                    # ONE verify


def test_the_lock_is_per_snapshot_and_destination_and_on_the_source_host():
    calls = []
    ops = R.Ops(lambda h, c: (calls.append((h, c)), (1 if "test -f" in c and "flock" not in c else 0, ""))[1])
    ops.ensure_snap("epyc10", "epyc7", "/s/snaps/" + "b" * 40, lambda d: "true")
    host, cmd = calls[-1]
    assert host == "epyc10" and "flock -w 7200" in cmd and ".push-epyc7.lock" in cmd and "rsync -a --exclude .verified" in cmd



def test_copy_runs_under_a_timeout_that_kills_its_process_group():
    calls = []
    ops = R.Ops(lambda h, c: (calls.append(c), (1 if "test -f" in c and "flock" not in c else 0, ""))[1])
    ops.ensure_snap("epyc10", "epyc7", "/s/snaps/" + "c" * 40, lambda d: "true")
    assert f"timeout -k 30 {R.COPY_TIMEOUT_S} bash -c" in calls[-1] and R.COPY_TIMEOUT_S <= 3600


def test_a_timed_out_snapshot_copy_is_an_infra_retry_not_a_design_fail():
    import kit_wave as KW
    for txt in ("KIT-SNAP FETCH failed; partial retained at /x: rsync error: timeout in data send/receive (code 30)",
                "rsync error: unexplained error (code 255) at io.c(226)"):
        assert KW.classify("place", txt)[0] in ("INFRA", "INFRA-SSH"), txt
