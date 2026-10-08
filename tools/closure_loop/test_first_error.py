"""CRASH-TRIAGE 2026-10-08: a crashed route's verdict names its first real error, never "ok-check failed: ;"."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl  # noqa: E402


def run(d):
    return subprocess.run([sys.executable, "-", str(d)], input=cl.FIRST_ERROR_PY, capture_output=True, text=True).stdout.strip()


def test_yosys_assert_beats_sta_traceback():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "lab"; d.mkdir()
        (d / "flow.log").write_text("FAILED: FlowError: yosys synthesis failed with exit 1:\n = 1\n"
                                    "ERROR: Assert `modules_.count(module->name) == 0' failed in rtlil.cc:1231.\n")
        (d / "sta.log").write_text("Traceback (most recent call last):\n  File x\nFileNotFoundError: no 6_final.sdc\n")
        assert "Assert `modules_.count" in run(d)


def test_make_step_and_openroad_error():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "lab"; d.mkdir()
        (d / "run.log").write_text("[INFO PPL-0001] x\n[ERROR ODB-0239] Pin c_ready[0] is assigned to multiple constraints.\n"
                                   "make[1]: *** [Makefile:450: do-2_1_floorplan] Error 1\n")
        out = run(d)
        assert "ODB-0239" in out and "do-2_1_floorplan" in out


def test_bare_refusal_when_flow_failed_and_traceback_last():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "lab"; d.mkdir()
        (d / "flow.log").write_text("OT_ORFS_CORNER=TC\n--memory-macro is a place-and-route option: run --stages pnr\n")
        (d / "status").write_text("flow_rc=1\n")
        (d / "sta.log").write_text("Traceback (most recent call last):\nFileNotFoundError: w18_extra.sdc\n")
        assert "--stages pnr" in run(d)
        (d / "status").write_text("flow_rc=0\n")
        assert "FileNotFoundError" in run(d)


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
    print("first_error tests PASS")
