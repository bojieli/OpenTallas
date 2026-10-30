"""FLOW-GEN-1 10-28: shared-generator fixes for the 5 bugs DIE-HEAD-9 patched kit-locally in the one-entry hd_tile kit
(results/die_head_1028/die_head_9_oe on claude/die-head-9-oe-1028).
  1 scalar count straps (strap_ca_efall / strap_ca_root) get a pin name without [0]   (gen_phys.strap_pin_sites)
  2 pg_island_cut.tcl runs at global scope (ORFS sources POST_PDN_TCL inside a proc) (gen_phys.pg_island_cut_tcl)
  3 face_flops.tcl sources landing_placement.tcl at global scope                     (gen_phys.LANDING_PLACEMENT_HOOK)
  4 landing status FF mapped DFFHQN + INV: follow the one INV to its QN flop          (landing_placement.tcl)
  5 a status window around a point in the core margin slides inside the core        (landing_placement.tcl)
python3 -m pytest -q tools/die_plan/test_flow_gen_1028.py"""
import inspect
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import clock_landings as CL
import gen_phys as G
import schema as S

HERE = Path(__file__).resolve().parent
LP_TCL = HERE / "landing_placement.tcl"


def _tclsh():
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")


def _tcl(tmp_path, script):
    """run a Tcl script FILE (stdin-fed tclsh exits 0 on errors)"""
    f = tmp_path / "t_main.tcl"
    f.write_text(script)
    return subprocess.run(["tclsh", str(f)], text=True, capture_output=True)


def _plan(count_straps, id_straps=()):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    tn = next(iter(raw["partition_types"]))
    raw["partition_types"][tn]["count_straps"] = list(count_straps)
    if id_straps:
        raw["partition_types"][tn]["id_straps"] = list(id_straps)
    return S.Plan(raw), tn


# ---- bug 1 ---------------------------------------------------------------------------------------------------------
def test_scalar_count_strap_pin_has_no_bit_index():
    P, tn = _plan([dict(name="strap_ca_efall", width=1, layer="M5", sites_um=[[13.0, 7.0]]),
                   dict(name="strap_ca_pad", width=2, layer="M5", sites_um=[[3.0, 7.0], [5.0, 7.0]])],
                  [dict(name="strap_id", width=1, layer="M7", sites_um=[[10.0, 4.32]])])
    sps = G.strap_pin_sites(P, tn)
    assert [s[0] for s in sps] == ["strap_id[0]", "strap_ca_efall", "strap_ca_pad[0]", "strap_ca_pad[1]"]
    pins = G.type_pins(P, tn)
    io = G.io_tcl(P, tn, pins)
    assert "place_pin -pin_name {strap_ca_efall} -layer M5" in io and "strap_ca_efall[0]" not in io
    pb = {(p["bus"], p["bit"]) for p in G.port_bind_pin_records(P, tn, pins)}
    assert ("strap_ca_efall", None) in pb and ("strap_id", 0) in pb and ("strap_ca_pad", 1) in pb
    assert {"strap_ca_efall", "strap_id[0]"} <= {r["name"] for r in G.plan_pin_records(P, tn, pins)}


def test_scalar_strap_width_must_be_one():
    P, tn = _plan([dict(name="strap_ca_root", width=2, layer="M5", sites_um=[[3.0, 7.0], [5.0, 7.0]])])
    with pytest.raises(ValueError, match="scalar"):
        G.strap_pin_sites(P, tn)


def test_scalar_set_matches_the_rtl_declarations():
    """SCALAR_STRAPS is exactly the set of strap inputs _origin_strap_rtl declares without a range."""
    src = inspect.getsource(CL)
    import re
    scalars = set(re.findall(r'"    input wire (strap_\w+)"', src))
    assert scalars == set(CL.SCALAR_STRAPS)


# ---- bug 2 ---------------------------------------------------------------------------------------------------------
PG_MOCK = """
namespace eval ord { proc get_db_block {} { return blk } }
proc blk {m args} { switch $m { getDbUnitsPerMicron { return 1000 } findNet { return NULL } } }
proc orfs_hook {} { source %s }
orfs_hook
"""


def test_pg_island_cut_runs_inside_a_proc(tmp_path):
    _tclsh()
    tcl = G.pg_island_cut_tcl([("u_core", "rst_n", (1.0, 2.0, 3.0, 4.0))])
    f = tmp_path / "pg_island_cut.tcl"
    f.write_text(tcl)
    r = _tcl(tmp_path, PG_MOCK % f)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_PG_ISLAND_CUT windows=1 strap_cuts=0 vias_removed=0" in r.stdout
    # control: the same body without the global-scope wrapper fails exactly as on hd_tile
    body = tcl.split("uplevel #0 {\n", 1)[1].rsplit("}\n", 1)[0]
    f.write_text(body)
    r = _tcl(tmp_path, PG_MOCK % f)
    assert r.returncode != 0 and 'pgc_u' in r.stderr


# ---- bug 3 ---------------------------------------------------------------------------------------------------------
def test_landing_hook_runs_at_global_scope(tmp_path):
    _tclsh()
    lp = tmp_path / "landing_placement.tcl"
    lp.write_text('if {![info exists ff_blk]} { error "OT_CLAND missing face placement context" }\nputs LP_OK\n')
    hook = tmp_path / "face_flops.tcl"
    for line, ok in ((G.LANDING_PLACEMENT_HOOK, True), ("source /work/landing_placement.tcl", False)):
        hook.write_text("uplevel #0 { set ff_blk blk }\n" + line.replace("/work/", f"{tmp_path}/") + "\n")
        r = _tcl(tmp_path, f"proc orfs_hook {{}} {{ source {hook} }}\norfs_hook\n")
        assert (r.returncode == 0 and "LP_OK" in r.stdout) == ok, r.stderr


# ---- bugs 4 + 5: landing_placement.tcl on a mock odb -----------------------------------------------------------------
MOCK = r"""
proc mk {o props} {
 set ::P($o) $props
 proc $o {m args} [string map [list @O@ $o] {
  if {[string match set* $m]} { dict set ::P(@O@) [string range $m 3 end] [lindex $args 0]; if {[llength $args]>1} { dict set ::P(@O@) [string range $m 3 end] $args }; return }
  return [dict get $::P(@O@) $m] }]
}
mk m_dff {getName DFFHQNx1_ASAP7_75t_R getWidth 1080 getHeight 270 isBlock 0}
mk m_inv {getName INVx1_ASAP7_75t_R getWidth 216 getHeight 270 isBlock 0}
mk m_nand {getName NAND2x1_ASAP7_75t_R getWidth 324 getHeight 270 isBlock 0}
mk t_out {getIoType OUTPUT}
mk t_in {getIoType INPUT}
mk bb {xMin 0 yMin 0 xMax 0 yMax 0}
# status net st_o <- INV (Y) <- net qn <- @QMASTER@ (QN)
mk dff {getName u_st/q_reg getMaster @QMASTER@ getPlacementStatus PLACED getBBox bb getITerms {it_dff_q}}
mk inv {getName u_st/inv getMaster m_inv getPlacementStatus PLACED getBBox bb getITerms {it_inv_a it_inv_y}}
mk it_dff_q {getMTerm t_out getNet qn getInst dff}
mk it_inv_a {getMTerm t_in getNet qn getInst inv}
mk it_inv_y {getMTerm t_out getNet st_o getInst inv}
mk qn {getName qn getITerms {it_dff_q it_inv_a}}
mk st_o {getName @STNAME@ getITerms {@STDRV@}}
mk it_st_d {getMTerm t_out getNet st_o getInst dff}
mk blk {getInsts {dff inv} getNets {qn st_o @XNET@}}
mk st_x {getName v/st_o getITerms {}}
proc blk_findNet {n} { if {$n eq "@STNAME@"} { return st_o }; return NULL }
rename blk blk_core
proc blk {m args} { if {$m eq "findNet"} { return [blk_findNet {*}$args] }; return [blk_core $m {*}$args] }
set ff_blk blk; set ff_dbu 1000
set ff_x0 4320; set ff_y0 4320; set ff_x1 100000; set ff_y1 100000; set ff_rh 270; set ff_sw 54
set ff_orient {}
for {set y $ff_y0} {$y < $ff_y1} {incr y $ff_rh} { dict set ff_orient $y R0 }
set ::env(RESULTS_DIR) @RES@
set cland_groups {}
set cland_optional_groups {}
set cland_status {{st_o @SX@ 50.0}}
source @LP@
puts "LOC [dict get $::P(dff) Location] [dict get $::P(dff) PlacementStatus]"
"""


def _run_lp(tmp_path, sx, qmaster="m_dff", inv=True, stname="st_o", xnet=""):
    _tclsh()
    script = (MOCK.replace("@QMASTER@", qmaster).replace("@STDRV@", "it_inv_y" if inv else "it_st_d")
              .replace("@STNAME@", stname).replace("@XNET@", xnet)
              .replace("@RES@", str(tmp_path)).replace("@SX@", str(sx)).replace("@LP@", str(LP_TCL)))
    return _tcl(tmp_path, script)


def _loc(r):
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("LOC "))
    _, x, y, st = line.split()
    return int(x), int(y), st


def test_status_ff_through_inverter_is_placed(tmp_path):
    r = _run_lp(tmp_path, 50.0)
    assert r.returncode == 0, r.stdout + r.stderr
    x, y, st = _loc(r)
    assert st == "FIRM" and 47840 <= x <= 52160 - 1080 and 47840 <= y <= 52160 - 270
    assert "cland:status:st_o" in (tmp_path / "ot_face_flops.txt").read_text()


def test_direct_dff_status_window_inside_core_unchanged(tmp_path):
    r = _run_lp(tmp_path, 50.0, inv=False)
    assert r.returncode == 0, r.stdout + r.stderr
    # first site/row at or above the window corner (47.84, 47.84) um, exactly as before the fix
    assert _loc(r) == (4320 + 54 * -(-(47840 - 4320) // 54), 4320 + 270 * -(-(47840 - 4320) // 270), "FIRM")


def test_inverter_from_non_flop_still_fails_closed(tmp_path):
    r = _run_lp(tmp_path, 50.0, qmaster="m_nand")
    assert r.returncode != 0 and "requires one actual dedicated output FF" in r.stderr


def test_status_point_in_core_margin_slides_inside_core(tmp_path):
    # point at x = 102.0 um, core x1 = 100.0 um (the hd_tile status pins at 706.336 on a 704.16 core edge)
    r = _run_lp(tmp_path, 102.0, inv=False)
    assert r.returncode == 0, r.stdout + r.stderr
    x, _y, st = _loc(r)
    assert st == "FIRM" and 100000 - 4320 <= x <= 100000 - 1080


def test_status_point_outside_core_by_more_than_window_fails_closed(tmp_path):
    r = _run_lp(tmp_path, 110.0, inv=False)     # window 107.84..112.16 entirely outside: no slide, still an error
    assert r.returncode != 0 and "no legal nonoverlapping" in r.stderr


def test_kit_rtl_prefixed_status_net_is_found(tmp_path):
    """DIE-KV-32 10-29 (KV hroot 3_3_place_gp 'OT_CLAND missing actual status net landing_ready_ft0_i'): the flattened
    --kit-rtl netlist names the status net u_bound.<net>; exactly one hierarchical match is placed as before."""
    r = _run_lp(tmp_path, 50.0, stname="u_bound.st_o")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _loc(r)[2] == "FIRM"


def test_ambiguous_prefixed_status_net_fails_closed(tmp_path):
    r = _run_lp(tmp_path, 50.0, stname="u_bound.st_o", xnet="st_x")
    assert r.returncode != 0 and "ambiguous status net st_o" in r.stderr


def test_status_half_window_slide_is_independent_of_dbu_rounding(tmp_path, monkeypatch):
    # Exact coll_ftn geometry: 691.2 - 686.88 = the 4.32um window width. The old
    # ceil/floor DBU guard rejects it by a few DBU due to floating representation.
    monkeypatch.setitem(globals(), 'MOCK', MOCK.replace('set ff_x1 100000', 'set ff_x1 686880'))
    r = _run_lp(tmp_path, 691.2, inv=False)
    assert r.returncode == 0, r.stdout + r.stderr
    x, _y, st = _loc(r)
    assert st == 'FIRM' and 686880 - 4320 <= x <= 686880 - 1080
