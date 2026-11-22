#!/usr/bin/env python3
"""CANCELMARK-1400: a job stopped by the no-progress watchdog or HUNG-WATCH is CANCELLED, never infra-oom (make Error 241 / exit 143 after a SIGTERM that was not earlyoom)."""
import copy
import os
import sys, tempfile, time

import pytest
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


@pytest.mark.parametrize(("variant", "code"), [
    ("exact", 143), ("exact", 137), ("other_exit", 21), ("old_receipt", 143),
    ("other_path", 143), ("other_host", 143), ("old_client", 143),
    ("no_current_ran", 143), ("running", 143), ("earlyoom", 137),
])
def test_late_noprog_rejudge_exact_terminal_attempt(tmp_path, monkeypatch, variant, code):
    monkeypatch.setattr(AP, "AP_DIR", tmp_path)
    monkeypatch.setattr(AP, "DRY", False)
    monkeypatch.setattr(AP, "log", lambda message: None)
    actions = tmp_path / "actions.tsv"
    monkeypatch.setattr(AP, "NOPROG_ACTIONS", actions)
    client = tmp_path / "jobs" / "489da562f86c" / "a2.log"
    client.parent.mkdir(parents=True)
    start = 1795219804
    stopped = 1795308302
    path = "/srv/scratch/claude/wave/items/a/attempt_2/gen/a"
    unit = "ap-489da562f86c-a2"
    ran = f"ot-run: RAN on epyc7 (unit oth-ubuntu-2814195-1795219815): exit {code}\n"
    log_unit = "ap-489da562f86c-a1" if variant == "old_client" else unit
    if variant == "no_current_ran":
        client.write_text(ran + f"AP_START {start} {log_unit}\nAP_RC={code}\n")
    else:
        client.write_text(f"AP_START {start} {log_unit}\n{ran}AP_RC={code}\n")
    os.utime(client, (stopped + 3, stopped + 3))
    receipt = time.strftime("%F %T", time.localtime(start - 100 if variant == "old_receipt" else stopped))
    action_path = path + "/run" if variant == "other_path" else path
    action_host = "epyc8" if variant == "other_host" else "epyc7"
    actions.write_text(f"{receipt}\t{action_host}\ta\t5_2_route\tdrt_violations best 13126 last 24036"
                       f"\t{action_path}\tdpkit-a-2852636\tdrt_violations best 13126 vs 13155 before window: < 2 % in 6 h\n")
    row = dict(id="489da562f86c", die="qwen_compute", goal="route", status="RUNNING" if variant == "running" else "DONE-CRASH",
               cls="CRASH", kind="infra-oom" if variant == "earlyoom" else "route-make-fail",
               reasons="old FAIL_route exit 21", ran_on="epyc7", path=path, client_log=str(client), unit=unit, attempts=2,
               started=start, finished=stopped + 40, updated=stopped + 45, history=[["old", "DONE-CRASH", "prior"]])
    state = {"jobs": {row["id"]: row}}
    previous = copy.deepcopy(row)
    AP.save_state(state)
    AP.rejudge_late_noprog(state)
    if variant != "exact":
        assert row == previous
        assert AP.load_state()["jobs"][row["id"]] == previous
        return
    assert (row["status"], row["kind"], row["finished"], row["updated"]) == (
        "DONE-STRUCTURAL", "drt-no-progress", previous["finished"], previous["updated"])
    assert row["history"][:1] == previous["history"]
    assert row["noprog_rejudge"]["previous"]["reasons"] == "old FAIL_route exit 21"
    assert AP.load_state()["jobs"][row["id"]] == row
    AP.rejudge_late_noprog(state)
    assert len(row["history"]) == 2
