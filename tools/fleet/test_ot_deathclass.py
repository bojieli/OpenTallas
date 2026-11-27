import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_deathclass as dc
import ot_status


def cls(rc, tail="", cmd=""):
    return dc.classify(rc, cmd, tail)[0]


def test_classes():
    assert cls(78, "SSH probe exit 255: ssh: Could not resolve hostname intel2") == "SSH-DROP"
    assert cls(137, "bash: line 6: 11 Killed openroad -exit x.tcl") == "OOM"
    assert cls(143, "ot-run: RAN on epyc8: exit 143") == "CANCEL"
    assert cls(1, "ot-run: stopped by ot-guard: disk floor 100 GB") == "RAIL-KILL"
    assert cls(127, "bash: /x/regen2.sh: No such file or directory") == "SETUP"
    assert cls(10, "FAIL_PREFLOOR kit_preflight") == "SETUP"
    assert cls(14, "kit is not a kit-wave attempt (hand-built kit?)") == "SETUP"
    assert cls(2, "FAILED t.py::test_x - AssertionError\nTESTS FAILED rc=2", "ot-push-main") == "TEST-FAIL"
    assert cls(1, "Traceback (most recent call last):\n  File x\nValueError: boom") == "TOOL-TRACEBACK"
    assert cls(11, "G0 errors 35 inherited 30 new 5") == "DESIGN-FAIL"
    assert cls(1, "ot-run: DRAIN: epyc8 DRAINING (75 of 9999 GB scratch free)") == "RAIL-KILL"
    assert dc.classify(1, "", "", 3)[0] == "SETUP"
    assert dc.classify(1, "", "", 300)[0] == "NO-LOG-RC1"
    assert dc.classify(2, "", "", 300)[0] == "NO-LOG-RC2"
    assert dc.classify(5, "", "", 300)[0] == "NO-PATTERN"
    assert cls(139, "") == "CRASH-SEGV" and cls(124, "") == "TIMEOUT" and cls(137, "") == "OOM"
    assert cls(1, "ROW-GATE NOT-READY row x") == "STATE-NOT-DEATH"
    assert cls(1, "WAIT-PLAN-VISUAL") == "STATE-NOT-DEATH"
    assert cls(1, "T2_PREP_DONE") == "CHECKER-RC"
    assert cls(5, "all fine\nbye") == "NO-PATTERN"


def test_advisory_drain_does_not_hide_later_execution_failure():
    stage = ("ot-run: DRAIN: localhost DRAINING (155 of 9999 GB scratch free): "
             "--dir /srv/kit already holds data there, the job may run there")
    denied_host = ("ot-run: DRAIN: epyc8 DRAINING: not used for this job (new job dir)")
    cancelled = "ot-run: RAN on epyc2 (unit oth-ubuntu-3113290-1795402371): exit 143"
    assert cls(143, stage + "\n" + denied_host + "\n" + cancelled) == "CANCEL"
    assert cls(1, denied_host + "\not-run: NOT-RUN no host qualifies (scratch disk under floor)") == "RAIL-KILL"


def test_drt_watchdog_kill_is_a_route_failure():
    marker = (
        "OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS: iteration 20 has "
        "24261 violations > 10000; stopping the stage (FAILFAST-1)"
    )
    killed = '/work/grt183_make.sh: line 297: 6571 Killed setsid "$@"'
    report = dc.classify(21, "", marker + "\n" + killed)
    assert report[0] == "ROUTE-FAIL"
    assert report[1].startswith("OT_DRT_NO_PROGRESS stage=route")
    assert cls(137, "watch for " + marker + "\n" + killed) == "OOM"


def test_cause_is_one_line_and_bounded():
    c, cause = dc.classify(1, "", "Traceback (most recent call last):\nValueError: " + "x" * 500)
    assert c == "TOOL-TRACEBACK" and "\n" not in cause and len(cause) <= 120


def test_label_reads_log_and_survives_missing():
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("a\nKilled\n")
    try:
        assert dc.label(137, "", f.name).startswith(" | class=OOM cause=")
    finally:
        os.unlink(f.name)
    assert dc.label(1, "", "/nonexistent/x.log", 300).startswith(" | class=NO-LOG-RC1")
    assert dc.label(1, "", "none", 300).startswith(" | class=NO-LOG-RC1")


def test_post_text_died_has_class_done_does_not():
    rec = dict(kind="run", name="ot", unit="u1", host="h", lane="L", rc=143, t_start=0, t_end=5, cmd="x", log=None)
    assert " | class=CANCEL cause=" in ot_status.post_text(rec)
    rec["rc"] = 0
    assert "class=" not in ot_status.post_text(rec)


def test_recorded_preflight_refusal_survives_without_a_log():
    rec = {
        "kind": "run", "lane": "EVENT-ENV-PREFLIGHT", "unit": "", "name": "test-run",
        "host": "test-host", "cmd": "--event-env c9.env -- true", "rc": 78,
        "t_start": 10, "t_end": 11, "refusal": "PREFLIGHT (event c9): missing bind input",
    }
    assert "| class=NOT-RUN cause=NOT-RUN PREFLIGHT (event c9): missing bind input" in ot_status.post_text(rec)
    assert cls(78, "NOT-RUN no host qualifies (epyc9 unreachable)") == "SSH-DROP"


def test_mid_run_filenotfound_is_runtime_input_missing_not_setup():
    import ot_deathclass as d
    tail = "Traceback (most recent call last):\n  File \"<stdin>\", line 2, in <module>\nFileNotFoundError: [Errno 2] No such file or directory: '/x/latcheck_v11s.json'\n"
    r = d.classify(1, "bash bind.sh", tail, 1089)
    assert (r[0] if isinstance(r, tuple) else r.get("class")) == "RUNTIME-INPUT-MISSING"
    r2 = d.classify(1, "bash bind.sh", tail, 4)
    assert (r2[0] if isinstance(r2, tuple) else r2.get("class")) == "SETUP"
