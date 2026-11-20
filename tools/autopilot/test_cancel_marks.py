#!/usr/bin/env python3
"""CANCELMARK-1400: a job stopped by the no-progress watchdog or HUNG-WATCH is CANCELLED, never infra-oom (make Error 241 / exit 143 after a SIGTERM that was not earlyoom)."""
import sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402


def job(path="/srv/x/items/a/gen/a", started=1000.0):
    return {"path": path, "started": started}


def test_hung_watch_mark_makes_the_job_cancelled():
    with tempfile.TemporaryDirectory() as d:
        m = Path(d) / "marks.tsv"
        m.write_text("1500\t/srv/x/items/a\tHUNG-WATCH\tno stage-log output for 130 min\n")
        r = AP.marked_cancel(job(), now=1600.0, marks=m, actions=Path(d) / "none")
        assert r and "HUNG-WATCH" in r and "not an OOM kill" in r


def test_noprog_action_line_makes_the_job_cancelled():
    with tempfile.TemporaryDirectory() as d:
        t = time.mktime(time.strptime("2026-11-20 12:35:00", "%Y-%m-%d %H:%M:%S"))
        a = Path(d) / "a.tsv"
        a.write_text("2026-11-20 12:35:00\tepyc2\tslw_fw_v1\t5_2_route\tmetric\t/srv/x/items/a/gen/a\tdpkit-a-1\tdrt_violations < 2 % in 6 h\t41\n")
        r = AP.marked_cancel(job(started=t - 3600), now=t + 60, marks=Path(d) / "none", actions=a)
        assert r and "no-progress watchdog" in r and "drt_violations" in r


def test_older_or_other_job_is_not_cancelled():
    with tempfile.TemporaryDirectory() as d:
        m = Path(d) / "marks.tsv"
        m.write_text("500\t/srv/x/items/a\tHUNG-WATCH\told attempt\n1500\t/srv/x/items/b\tHUNG-WATCH\tother item\n")
        assert AP.marked_cancel(job(), now=1600.0, marks=m, actions=Path(d) / "none") is None      # first is before the attempt started, second is another dir


def test_no_files_no_mark():
    assert AP.marked_cancel(job(), now=2000.0, marks=Path("/nonexistent/m"), actions=Path("/nonexistent/a")) is None
    assert AP.marked_cancel({"started": 1.0}, now=2000.0) is None


def test_hung_watch_cancel_writes_the_mark_autopilot_reads(monkeypatch):
    monkeypatch.setenv("KW_PROBE_INLINE", "1")      # no detached probe-bg process, no cache
    import kit_wave as KW
    import test_kit_wave_hung_watch as T
    with tempfile.TemporaryDirectory() as d:
        class A(T.AP):
            AP_DIR = d
        st = {"items": {"a": T.silent_rec(d, 400)}}
        now = time.time()
        KW.reap_dead(A(cpu=500.0), T.CFG, st, {}, now=now)
        assert KW.reap_dead(A(cpu=520.0), T.CFG, st, {}, now=now + 130 * 60) == 1
        txt = (Path(d) / "cancel_marks.tsv").read_text()
        assert "\tHUNG-WATCH\t" in txt and st["items"]["a"]["status"] == "RETRY-INFRA"
        j = {"path": T.ROOT, "started": now - 3600}
        got = AP.marked_cancel(j, now=now + 131 * 60, marks=Path(d) / "cancel_marks.tsv", actions=Path(d) / "none")
        assert got and "HUNG-WATCH" in got
