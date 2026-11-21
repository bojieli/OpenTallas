"""FLOW-OBS-GCELL-1121: GRT capacity 0 on sliver gcells a routing obstruction leaves partly free (obs_gcell_cap.tcl planner, pure Tcl)
and its wiring (grt_pre.tcl hook before PG-track-truth, kit tool list).  Reference cases: HEAD hd_host_e net21446 (M6) and hd_serdes sdr2c (M4)."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TOOL = HERE / "obs_gcell_cap.tcl"
TCLSH = shutil.which("tclsh")
needs_tcl = pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
GC = 570


def tracks(off, pitch, lo, hi):
    return [t for t in range(off + ((lo - off) // pitch) * pitch, hi, pitch) if t >= lo]


def plan(obs, trk, clr, pins=None, minfree=3):
    lst = lambda rs: " ".join("{" + " ".join(str(v) for v in r) + "}" for r in rs)
    d = lambda m: "[dict create " + " ".join(f"{k} [list {lst(v) if isinstance(v[0], (list, tuple)) else ' '.join(map(str, v))}]" for k, v in m.items()) + "]"
    cl = "[dict create " + " ".join(f"{k} {v}" for k, v in clr.items()) + "]"
    script = (f"source {{{TOOL}}}\n"
              f"set r [ot_obsgc_plan {d(obs)} {d(trk)} {d(pins) if pins else '[dict create]'} {cl} {GC} {minfree}]\n"
              "foreach g [lrange $r 0 end-1] {puts \"CUT $g\"}\nputs \"STAT [lindex $r end]\"\n")
    out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.splitlines()
    cuts = [tuple([l.split()[1]] + [int(v) for v in l.split()[2:]]) for l in out if l.startswith("CUT ")]
    stat = dict(zip(*[iter(next(l for l in out if l.startswith("STAT ")).split()[1:])] * 2))
    return cuts, {k: int(v) for k, v in stat.items()}


@needs_tcl
def test_host_e_m6_sliver_row_is_cut():
    # reserved clock-site obstruction (337.338,345.06)-(339.498,346.41): 2 M6 tracks (346.464, 346.528) left in row y 345.99-346.56
    obs = {"M6": [(337338, 345060, 339498, 346410)]}
    cuts, st = plan(obs, {"M6": tracks(32, 64, 340000, 350000)}, {"M6": 16 + 32})
    assert cuts == [("M6", 591, 607, 596, 608)]          # one region: gcell row 607, columns 591-595 (whole gcells)
    assert st["cut"] == 5 and st["candidates"] == 10      # the bottom-edge row 605 keeps 3 legal tracks: untouched


@needs_tcl
def test_sdr2c_m4_single_track_row_is_cut_and_wide_rows_stay():
    obs = {"M4": [(1990440, 34830, 1992600, 57780)]}       # one free M4 track 34.776 in row y 34.77-35.34
    cuts, st = plan(obs, {"M4": tracks(24, 48, 30000, 60000)}, {"M4": 12 + 24})
    assert cuts == [("M4", 3492, 61, 3496, 62)]
    assert st["candidates"] == 8 and st["cut"] == 4       # top edge row 101 keeps 7 tracks


@needs_tcl
def test_gcell_aligned_edges_and_pin_strips_are_never_cut():
    obs = {"M6": [(337338, 345990, 339498, 346560)]}       # on the gcell grid in y: no partly covered row
    cuts, st = plan(obs, {"M6": tracks(32, 64, 340000, 350000)}, {"M6": 48})
    assert cuts == [] and st["candidates"] == 0
    obs = {"M6": [(337338, 345060, 339498, 346410)]}
    cuts, st = plan(obs, {"M6": tracks(32, 64, 340000, 350000)}, {"M6": 48}, pins={"M6": [(338000, 346450, 338032, 346500)]})
    assert cuts == [] and st["exempt"] == 5               # a block pin in the sliver strip keeps its access


@needs_tcl
def test_threshold_counts_every_obstruction_on_the_layer():
    # two M7 (vertical: along y, across x) pieces leave a 2-track gap inside one gcell column: cut unless the gap holds a pin
    obs = {"M7": [(1000, 5700, 3000, 5900), (1000, 6060, 3000, 6270)]}
    trk = {"M7": tracks(32, 64, 5000, 7000)}
    cuts, _ = plan(obs, trk, {"M7": 48})
    assert ("M7", 1, 10, 6, 11) in cuts
    cuts, _ = plan(obs, trk, {"M7": 48}, minfree=1)
    assert cuts == []


def test_hook_is_wired_before_pg_track_truth_and_copied_into_kits():
    g = (HERE / "grt_pre.tcl").read_text()
    assert "ot_obsgc_add" in g and g.index("ot_obsgc_add") < g.index("ot_pgtt_add")
    assert '"obs_gcell_cap.tcl"' in (HERE / "gen_phys.py").read_text()
    t = TOOL.read_text()
    assert "OT_OBS_GCELL_CAP" in t and "set_global_routing_region_adjustment" in t
