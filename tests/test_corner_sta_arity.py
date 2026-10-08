"""corner_sta.run must keep working with sign-off wrappers that replace script() with the older signature."""
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/w18"))
import corner_sta as C  # noqa: E402


def _orfs(tmp_path, sdc="6_final.sdc"):
    base = tmp_path / "results/asap7/x/base"
    base.mkdir(parents=True)
    for n in ("6_final.odb", "6_final.spef", sdc):
        (base / n).write_text("x")
    return tmp_path


def _run(tmp_path, wrapper, **kw):
    seen = []
    def w(*a):
        seen.append(len(a))
        return wrapper(*a)
    with mock.patch.object(C, "script", w), \
         mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "OT_WS 1e-12\n", "")):
        C.run(_orfs(tmp_path, kw.get("sdc_name", "6_final.sdc")), "ss", [], **kw)
    return seen


def test_three_and_four_arg_wrappers(tmp_path):
    assert _run(tmp_path / "a", lambda corner, base, macros: "exit\n") == [3]
    assert _run(tmp_path / "b", lambda corner, base, macros, post_sdc=(): "exit\n", post_sdc=["p.sdc"]) == [4]


def test_explicit_sdc_name_is_passed(tmp_path):
    got = []
    def full(corner, base, macros, post_sdc=(), sdc_name="6_final.sdc"):
        got.append(sdc_name)
        return "exit\n"
    _run(tmp_path, full, sdc_name="7_signoff.sdc")
    assert got == ["7_signoff.sdc"]
