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
    assert dc.classify(1, "", "", 300)[0] == "UNCLASSIFIED"
    assert cls(1, "T2_PREP_DONE") == "CHECKER-RC"
    assert cls(5, "all fine\nbye") == "UNCLASSIFIED"


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
    assert dc.label(1, "", "/nonexistent/x.log", 300).startswith(" | class=UNCLASSIFIED")
    assert dc.label(1, "", "none", 300).startswith(" | class=UNCLASSIFIED")


def test_post_text_died_has_class_done_does_not():
    rec = dict(kind="run", name="ot", unit="u1", host="h", lane="L", rc=143, t_start=0, t_end=5, cmd="x", log=None)
    assert " | class=CANCEL cause=" in ot_status.post_text(rec)
    rec["rc"] = 0
    assert "class=" not in ot_status.post_text(rec)
