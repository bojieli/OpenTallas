"""S81-ENGRR-B5 11-06: OT_RT_MACRO_CUT / OT_RT_MGRP_MAXUM in the shared legacy regional_taps.tcl are opt-in.
(1) rt_cut with no macro walls (OT_RT_MACRO_CUT unset/0 -> rt_mbox empty) returns the old median-clamped cut exactly;
(2) with a wall spanning the box it snaps to the wall edge nearest the median inside the middle half;
(3) both knobs are read with default off and every new branch is guarded by them.
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_regional_taps_optin.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RT = Path(__file__).resolve().parent / "rt/regional_taps.tcl"
SRC = RT.read_text()


def _proc(name):
    m = re.search(r"^proc %s \{.*?^\}\n" % name, SRC, re.S | re.M)
    assert m, name
    return m.group(0)


def _cut(pts, mbox, box, byx, split="count"):
    tcl = shutil.which("tclsh")
    if not tcl:
        pytest.skip("no tclsh")
    lst = lambda xs: "{" + " ".join("{" + " ".join(str(v) for v in x) + "}" for x in xs) + "}"
    script = (f"set rt_split {split}\nset rt_pts {lst(pts)}\nset rt_mbox {lst(mbox)}\n" + _proc("rt_cut")
              + f"puts [rt_cut {' '.join(str(v) for v in box)} {int(byx)}]\n")
    out = subprocess.run([tcl], input=script, capture_output=True, text=True, check=True).stdout.split()
    return float(out[-1])


def _old(pts, box, byx):
    a, b, c, d = box
    lo, hi = (a, b) if byx else (c, d)
    v = sorted((x if byx else y) for x, y in pts if a <= x <= b and c <= y <= d)
    if len(v) < 2:
        return (lo + hi) / 2.0
    q = (hi - lo) / 4.0
    return min(max(v[len(v) // 2], lo + q), hi - q)


PTS = [(x * 7.3 % 200, x * 3.1 % 100) for x in range(1, 400)] + [(20.0 + i, 10.0) for i in range(60)]


@pytest.mark.parametrize("byx", [True, False])
@pytest.mark.parametrize("box", [(0, 200, 0, 100), (0, 100, 0, 50), (50, 200, 25, 100)])
def test_default_off_is_old_cut(box, byx):
    assert _cut(PTS, [], box, byx) == pytest.approx(_old(PTS, box, byx), abs=1e-9)
    assert _cut(PTS, [], box, byx, split="geom") == ((box[0] + box[1]) if byx else (box[2] + box[3])) / 2.0


def test_macro_wall_snaps_cut():
    box = (0, 200, 0, 100)
    r = _old(PTS, box, True)
    wall = (110.0, 140.0, -5.0, 95.0)       # spans 95% of the box height across an x cut
    assert _cut(PTS, [wall], box, True) == 110.0 != r
    short = (110.0, 140.0, 0.0, 30.0)        # 30% span: not a wall, cut unchanged
    assert _cut(PTS, [short], box, True) == pytest.approx(r)
    outside = (5.0, 30.0, 0.0, 100.0)        # both edges outside the middle half: cut unchanged
    assert _cut(PTS, [outside], box, True) == pytest.approx(r)


def test_knobs_default_off_and_guarded():
    assert re.search(r"set rt_mbox \{\}\nif \{\[info exists ::env\(OT_RT_MACRO_CUT\)\] && \$::env\(OT_RT_MACRO_CUT\)\} \{", SRC)
    assert "if {[llength $rt_mbox]} {" in _proc("rt_cut")
    assert re.search(r"set rt_mgmax \[expr \{\[info exists ::env\(OT_RT_MGRP_MAXUM\)\] \? double\(\$::env\(OT_RT_MGRP_MAXUM\)\) : 0\.0\}\]", SRC)
    assert "if {$rt_mgmax > 0 && [dict exists $ingrp $nm]} {" in SRC
    assert 'if {$rt_mgmax > 0} { puts "OT_RT_MGRP_MAXUM' in SRC
    # macro-group membership is decided only by ingrp when the far flag is never set
    assert "if {[dict exists $ingrp $nm] && !$rt_far} {" in SRC
