"""relay_mid.tcl OT_RELAY_POLY (FIX-RELAYPOLY, FABLE-REVIEW-COL R-COL-4): the polyline helper procs, run under plain tclsh
on a mock macro wall.  python3 -m pytest -q tools/die_plan/test_relay_poly.py"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

MOCK = """
set rm_dbu 1000
set rm_x0 0; set rm_y0 0; set rm_x1 1400000; set rm_y1 1200000
set rm_gd 8000
set rm_pr [list {300000 300000 700000 900000} {800000 100000 1000000 1100000}]
set rm_wpmap {}
source /w/procs.tcl
set p [rm_polyline g 100000 600000 1300000 600000]
puts "PATH $p"
puts "CLEAR [rm_polyline g 100000 100000 200000 200000]"
set tot [lindex $p end]
foreach j {1 2 3 4 5} { puts "ST [rm_along $p [expr {$tot * $j / 6.0}]]" }
set rm_wpmap [dict create gx {660 1190 1335 1190}]
puts "WP [rm_polyline gx 663000 1120000 1335000 1024000]"
"""


def _run():
    src = (HERE / "relay_mid.tcl").read_text()
    procs = src[src.index("proc rm_blocked"):src.index("# chains: head")]
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "procs.tcl").write_text(procs)
        (Path(d) / "t.tcl").write_text(MOCK.replace("/w/", d + "/"))
        return subprocess.run(["tclsh", str(Path(d) / "t.tcl")], capture_output=True, text=True, timeout=120).stdout


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_polyline_avoids_macros_and_even_stations():
    out = _run()
    path = [int(v) for v in out.split("PATH ")[1].splitlines()[0].split()]
    assert path[0:2] == [100000, 600000] and path[-3:-1] == [1300000, 600000]
    rects = [(300000, 300000, 700000, 900000), (800000, 100000, 1000000, 1100000)]
    xy = list(zip(path[0:-1:2], path[1:-1:2]))
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):          # every leg is axis-parallel and clear of both macros
        assert x0 == x1 or y0 == y1
        for t in range(41):
            x, y = x0 + (x1 - x0) * t / 40, y0 + (y1 - y0) * t / 40
            assert not any(a < x < c and b < y < d for a, b, c, d in rects), (x, y)
    st = [tuple(map(int, l.split()[1:])) for l in out.splitlines() if l.startswith("ST ")]
    assert len(st) == 5 and len(set(st)) == 5
    assert "CLEAR \n" in out or "CLEAR" in out.splitlines()[1]    # straight line clear -> old behaviour (empty result)
    assert out.split("CLEAR ")[1].splitlines()[0].strip() == ""


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_plan_waypoints_override():
    out = _run()
    wp = [int(v) for v in out.split("WP ")[1].splitlines()[0].split()]
    assert wp[:2] == [663000, 1120000] and wp[2:6] == [660000, 1190000, 1335000, 1190000] and wp[-3:-1] == [1335000, 1024000]
