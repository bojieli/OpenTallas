"""poll_stage: an empty rc file (host reset mid-write) is LOST, not an IndexError loop (ROOT 2026-10-15)."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as cl  # noqa: E402


def _poll(out, rc=0):
    j = {"stage_tag": "t.a1", "run": "/r", "host": "h"}
    with patch.object(cl, "ssh", lambda *a, **k: SimpleNamespace(returncode=rc, stdout=out)), \
            patch.object(cl, "note_host", lambda *a: None):
        return cl.poll_stage(j)


def test_rc_values():
    assert _poll("RC 0\n") == ("RC", 0)
    assert _poll("RC 137\n") == ("RC", 137)
    assert _poll("RC\n") == ("LOST", None)
    assert _poll("RC garbage\n") == ("LOST", None)
    assert _poll("RUNNING\n") == ("RUNNING", None)
    assert _poll("", rc=255) == ("UNREACHABLE", None)


def test_bench_scratch_dirs_and_crash_rc():
    cmd = "bash tools/x/run.sh clock_mutant dsfd 1029 {RUN}/bench_c && cp {RUN}/bench_c/x {RUN}/cl/y {RUN}/src/z {RUN}/bench_src_a1/q"
    assert cl.bench_scratch_dirs(cmd) == ["bench_c"]
    assert cl.bench_crashed({"expect": "fail"}, 126, "Vtb: Permission denied")
    assert not cl.bench_crashed({"expect": "fail"}, 1, "STATION FAIL")
