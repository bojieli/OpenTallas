"""FLOW-OBS-GCELL-1121: GRT capacity 0 on sliver gcells a routing obstruction leaves with fewer than 3 DRT-legal tracks
(obs_gcell_cap.tcl planner, pure Tcl) and its wiring (grt_pre.tcl after PG-track-truth, grt_pg_replay.tcl, kit tool list).
Reference cases: HEAD hd_host_e net21446 (M6) and hd_serdes sdr2c (M4).  ASAP7 M2-M7 wide-metal spacing is 0.072 um: a
reserved obstruction (1.35 um tall) blocks the tracks within 16 + 72 nm of its edge although GRT counts them free."""
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


def _d(m):
    if not m:
        return "[dict create]"
    body = []
    for k, v in m.items():
        if v and isinstance(v[0], (list, tuple)):
            body.append(f"{k} [list " + " ".join("{" + " ".join(map(str, r)) + "}" for r in v) + "]")
        else:
            body.append(f"{k} [list {' '.join(map(str, v))}]")
    return "[dict create " + " ".join(body) + "]"


def plan(src, trk, clr, blk=None, pins=None, minfree=3):
    cl = "[dict create " + " ".join(f"{k} {v}" for k, v in clr.items()) + "]"
    script = (f"source {{{TOOL}}}\n"
              f"set r [ot_obsgc_plan {_d(src)} {_d(blk)} {_d(trk)} {_d(pins)} {cl} {GC} {minfree}]\n"
              "foreach g [lrange $r 0 end-1] {puts \"CUT $g\"}\nputs \"STAT [lindex $r end]\"\n")
    out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.splitlines()
    cuts = [tuple([l.split()[1]] + [int(v) for v in l.split()[2:]]) for l in out if l.startswith("CUT ")]
    stat = dict(zip(*[iter(next(l for l in out if l.startswith("STAT ")).split()[1:])] * 2))
    return cuts, {k: int(v) for k, v in stat.items()}


M6 = tracks(32, 64, 340000, 350000)
WIDE = 16 + 72          # M6 half width + wide-metal spacing next to a 1.35-um obstruction


@needs_tcl
def test_host_e_m6_sliver_row_is_cut_with_wide_metal_spacing():
    # (337.338,345.06)-(339.498,346.41): row 607 keeps 346.464 (38 nm, illegal) + 346.528 (legal) = 1 legal track
    src = {"M6": [(337338, 345060, 339498, 346410, WIDE)]}
    cuts, st = plan(src, {"M6": M6}, {"M6": 48})
    assert ("M6", 591, 607, 596, 608) in cuts
    # bottom row 605: 344.864 / 344.928 legal, 344.992 within 88 nm of 345.06 -> 2 legal -> cut as well
    assert ("M6", 591, 605, 596, 606) in cuts and st["cut"] == 10
    # min spacing only (the first draft): row 605 keeps 3 tracks
    cuts, _ = plan({"M6": [(337338, 345060, 339498, 346410)]}, {"M6": M6}, {"M6": 48})
    assert cuts == [("M6", 591, 607, 596, 608)]


@needs_tcl
def test_sdr2c_m4_single_track_row_is_cut_and_wide_rows_stay():
    src = {"M4": [(1990440, 34830, 1992600, 57780, 12 + 72)]}   # 34.776 is 42 nm below the edge: 0 legal
    cuts, st = plan(src, {"M4": tracks(24, 48, 30000, 60000)}, {"M4": 36})
    assert cuts == [("M4", 3492, 61, 3496, 62)]
    assert st["candidates"] == 8 and st["cut"] == 4              # top edge row 101 keeps 6 legal tracks


@needs_tcl
def test_extra_blockers_pg_and_track_truth_count_against_free_tracks():
    src = {"M6": [(337338, 345990, 339498, 346160, WIDE)]}     # row 607 bottom covered: 346.288 .. 346.528 -> 3+ legal
    cuts, _ = plan(src, {"M6": M6}, {"M6": 48})
    assert cuts == []
    cuts, _ = plan(src, {"M6": M6}, {"M6": 48}, blk={"M6": [(330000, 346400, 345000, 346560, WIDE)]})
    assert cuts == [("M6", 591, 607, 596, 608)]                  # a PG / PG-truth shape over the rest leaves 0


@needs_tcl
def test_pin_exempts_only_the_gcells_it_touches():
    src = {"M6": [(337338, 345060, 339498, 346410, WIDE)]}
    cuts, st = plan(src, {"M6": M6}, {"M6": 48}, pins={"M6": [(338100, 346450, 338132, 346500)]})
    assert st["exempt"] == 1                                    # gcell 593 of row 607 only
    assert ("M6", 591, 607, 593, 608) in cuts and ("M6", 594, 607, 596, 608) in cuts


@needs_tcl
def test_gcell_aligned_edges_have_no_candidates():
    cuts, st = plan({"M6": [(337338, 345990, 339498, 346560, WIDE)]}, {"M6": M6}, {"M6": 48})
    assert cuts == [] and st["candidates"] == 0


@needs_tcl
def test_macro_orientation_transform():
    out = subprocess.run([TCLSH], input=f"source {{{TOOL}}}\n"
                         "puts [ot_obsgc_xform R0 100 50 1000 2000 10 5 20 15]\n"
                         "puts [ot_obsgc_xform MX 100 50 1000 2000 10 5 20 15]\n"
                         "puts [ot_obsgc_xform R90 100 50 1000 2000 10 5 20 15]\n",
                         capture_output=True, text=True, check=True).stdout.split("\n")
    assert out[0] == "1010 2005 1020 2015"
    assert out[1] == "1010 2035 1020 2045"
    assert out[2] == "1035 2010 1045 2020"


def test_hook_is_wired_after_pg_track_truth_replayed_and_copied_into_kits():
    g = (HERE / "grt_pre.tcl").read_text()
    assert "ot_obsgc_add" in g and g.index("ot_pgtt_add") < g.index("ot_obsgc_add")
    r = (HERE / "grt_pg_replay.tcl").read_text()
    assert "ot_obsgc_add" in r and r.index("ot_pgtt_add") < r.index("ot_obsgc_add") < r.index("ot_pgcap_add")
    assert '"obs_gcell_cap.tcl"' in (HERE / "gen_phys.py").read_text()
    t = TOOL.read_text()
    assert "OT_OBS_GCELL_CAP" in t and "set_global_routing_region_adjustment" in t and "::ot_pgtt_obs" in t


def test_tap_chain_seed_leaves_the_reserved_strip_on_one_side():
    t = (HERE / "tap_balance.tcl").read_text()
    p = t.index("proc tb_tap_pass")
    assert "proc tb_seed_side" in t and t.index("proc tb_seed_side") < p
    body = t[p:]
    assert body.index("lassign [tb_seed_side $bt $tree $x $y] x y") < body.index('dbInst_create $tb_blk $tb_master "${n}_tb${tb_tag}${it}_d$b"')
    assert "OT_TAP_SEED_SIDE" in t and "OT_CLK_OBS_HALO_ROWS" in t
