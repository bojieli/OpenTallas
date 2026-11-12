"""KW-FIX-45 11-11 ROW-SLIVER class: free row segments narrower than OT_ROW_SLIVER_UM get a placement blockage (opt-in)."""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL = HERE / "row_sliver_block.tcl"


def run(rows, fixed, minw):
    script = ("source %s\nputs [rs_slivers {%s} {%s} %d]\n" % (
        TCL, " ".join("{%s}" % " ".join(map(str, r)) for r in rows),
        " ".join("{%s}" % " ".join(map(str, f)) for f in fixed), minw))
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True).stdout.strip()
    return [tuple(int(v) for v in m.split()) for m in re.findall(r"\{([^{}]*)\}", out)]


def test_sliver_between_endcap_and_macro_is_blocked_other_rows_unchanged():
    rows = [(0, 0, 10000, 270), (0, 270, 10000, 540)]
    fixed = [(0, 0, 100, 540), (2000, 0, 6000, 270), (9900, 0, 10000, 540)]   # endcaps + a macro on row 0 only
    fixed += [(2400, 270, 2500, 540)]                                      # a tapcell on row 1
    # row 0: free (100,2000) wide, (6000,9900) wide: nothing narrow.  Narrow the left gap:
    fixed[1] = (1900 + 0, 0, 6000, 270)
    got = run(rows, fixed, 400)
    assert got == []                                                  # 1800 and 3900 wide are fine
    fixed2 = [(0, 0, 100, 540), (350, 0, 6000, 270), (9900, 0, 10000, 540)]
    got2 = run(rows, fixed2, 400)
    assert got2 == [(100, 0, 350, 270)]                               # the 250-wide sliver of row 0 only


def test_threshold_is_strict_and_full_row_is_not_a_sliver():
    assert run([(0, 0, 300, 270)], [], 400) == [(0, 270 * 0, 300, 270)]   # a whole row narrower than W is a sliver
    assert run([(0, 0, 400, 270)], [], 400) == []                           # exactly W is kept
    assert run([(0, 0, 10000, 270)], [(0, 0, 10000, 270)], 400) == []       # fully covered row: nothing free


def test_obstacle_not_overlapping_the_row_is_ignored_and_overlaps_merge():
    rows = [(0, 270, 5000, 540)]
    assert run(rows, [(100, 0, 4900, 270)], 400) == []                      # below the row: no effect
    fx = [(0, 270, 1000, 540), (900, 270, 1150, 540), (1300, 270, 5000, 540)]
    assert run(rows, fx, 400) == [(1150, 270, 1300, 540)]                   # merged overlap, 150-wide gap


def test_generator_wiring_is_opt_in():
    gp = (HERE / "gen_phys.py").read_text()
    ff = (HERE / "face_flops.tcl").read_text()
    assert "def _row_sliver_um(budgets)" in gp and "export OT_ROW_SLIVER_UM" in gp
    assert "if _row_sliver_um(P.budgets):" in gp and "row_sliver_block.tcl" in gp
    assert "[info exists ::env(OT_ROW_SLIVER_UM)]" in ff and "source /work/row_sliver_block.tcl" in ff
