"""OT_TXL_MID hook (tools/die_plan/txl_mid.tcl): station geometry, tclsh only."""
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).resolve().parent / "txl_mid.tcl"
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def run(tmp_path, body, env_on=False):
    t = tmp_path / "t.tcl"
    head = 'set ::env(OT_TXL_MID) 1\n' if env_on else 'array unset ::env OT_TXL_MID\n'
    t.write_text(head + f"source {TCL}\n" + body)
    return subprocess.run(["tclsh", str(t)], capture_output=True, text=True)


def nums(s):
    return [float(x) for x in s.split()]


def test_targets_even(tmp_path):
    r = run(tmp_path, "puts [join [join [ot_txl_mid::targets 0 0 500 1000 4]]]")
    assert r.returncode == 0, r.stderr
    assert nums(r.stdout) == [100, 200, 200, 400, 300, 600, 400, 800]


CORE = "{0 0 1000 1000}"


def test_free_target_stays(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 50 50 {{{{200 200 300 300}}}} {CORE} 5 400]")
    assert nums(r.stdout) == [50, 50]


def test_target_in_macro_moves_to_nearest_free(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 50 50 {{{{45 45 55 55}}}} {CORE} 5 400]")
    x, y = nums(r.stdout)
    assert not (45 <= x <= 55 and 45 <= y <= 55) and abs(x - 50) + abs(y - 50) <= 10


def test_prefers_small_y_move(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 500 500 {{{{480 440 520 560}}}} {CORE} 5 400]")
    x, y = nums(r.stdout)
    assert not (480 <= x <= 520 and 440 <= y <= 560) and y == 500


def test_core_limits_search(tmp_path):
    r = run(tmp_path, f'puts "<[ot_txl_mid::nearest_free 50 50 {{{{-10 -10 1010 1010}}}} {CORE} 5 400]>"')
    assert r.stdout.strip() == "<>"


def test_off_needs_no_openroad(tmp_path):
    r = run(tmp_path, 'puts ok')
    assert r.returncode == 0 and r.stdout.strip() == "ok"


def test_on_without_openroad_fails_loudly(tmp_path):
    r = run(tmp_path, 'puts never', env_on=True)
    assert r.returncode != 0
