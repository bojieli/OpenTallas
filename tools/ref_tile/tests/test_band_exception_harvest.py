"""HBM-MC3G 10-20: band confinement + placed exception harvest for lattice_channel_bound kits.

Python half: the harvested exceptions make measured_band_fill pass only for exact pin/clock cells of the flow role
list; an ordinary cell outside the band, a missing band approval or a dropped exception all FAIL (causal negatives).
Tcl half: std_band_fence.tcl on a mocked OpenDB: FIRM pin cells / port-net cells stay out of the group, ordinary cells
and births join it, clock drivers are kept out, and the band check catches a member left outside the band.
"""
import copy
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as R  # noqa: E402
from band_exception_harvest import harvest  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
LO, HI, W, H = 248.4, 291.6, 388.8, 561.6


def candidate(approved="ROOT"):
    s = {"kind": "tile", "macros": [{}] * 4,
         "fill_reason": {"lattice_channel_bound": {"why": "literal lattice", "approved_by": approved,
                                                   "std_band_y_um": [LO, HI]}}}
    bs = [[f"m{i}", "sram", x, y, x + 18.79, y + 18.36]
          for i, (x, y) in enumerate([(43.2, 43.2), (86.4, 43.2), (43.2, 345.6), (86.4, 345.6)])]
    area, cells, i = 6987.47, [], 0
    while area > 1e-7:
        a = min(area, 380 * 0.27)
        cells.append([f"u{i}", "logic", "PLACED", 2.16, LO + i * 0.27, 2.16 + a / 0.27, LO + (i + 1) * 0.27])
        area -= a
        i += 1
    rows = [[f"r{k}", 2.16, 2.16 + k * 0.27, W - 2.16, 2.16 + (k + 1) * 0.27] for k in range(round((H - 4.32) / 0.27))]
    # boundary cells outside the band: a pin flop at the S face, a CTS buffer just above the band
    cells += [["pf0", "DFF", "PLACED", 100.0, 2.16, 101.0, 2.43], ["ck0", "BUF", "PLACED", 200.0, 300.24, 201.0, 300.51]]
    p = {"occupancy_schema": "opentallas.layout.occupancy.v1", "die": [0, 0, W, H], "blocks": bs, "std_cells": cells,
         "rows": rows, "stats": {"std_area": sum((c[5] - c[3]) * (c[6] - c[4]) for c in cells)},
         "band_roles": {"schema": "opentallas.band_roles.v1", "stage": "post_cts", "band_y_um": f"{LO}:{HI}",
                        "pin": ["pf0"], "clock": ["ck0"]}}
    return s, copy.deepcopy(p), p


def with_ex(s, ex):
    s = copy.deepcopy(s)
    s["fill_reason"]["lattice_channel_bound"]["placed_exceptions"] = ex
    return s


def test_harvest_makes_measured_band_pass():
    s, f, p = candidate()
    assert not R.measured_band_fill(s, f, p)["valid"]          # before harvest: pf0/ck0 unapproved
    ex, err = harvest(s, p)
    assert err == []
    assert [(e["inst"], e["role"]) for e in ex] == [("ck0", "clock"), ("pf0", "pin")]
    r = R.measured_band_fill(with_ex(s, ex), f, p)
    assert r["valid"], r
    assert r["exception_instances"] == ["ck0", "pf0"]


def test_ordinary_cell_outside_band_is_refused():
    s, f, p = candidate()
    p["std_cells"].append(["u_stray", "logic", "PLACED", 150.0, 400.14, 151.0, 400.41])
    p["stats"]["std_area"] += 0.27
    ex, err = harvest(s, p)
    assert any("without a pin/clock role" in e for e in err)
    assert not R.measured_band_fill(with_ex(s, ex), f, p)["valid"]


def test_no_band_approval_no_harvest():
    s, _, p = candidate(approved="")
    _, err = harvest(s, p)
    assert any("no coordinator approval" in e for e in err)


def test_dropped_or_stale_exception_fails():
    s, f, p = candidate()
    ex, _ = harvest(s, p)
    assert not R.measured_band_fill(with_ex(s, ex[:1]), f, p)["valid"]
    stale = ex + [dict(ex[0], inst="gone")]
    r = R.measured_band_fill(with_ex(s, stale), f, p)
    assert not r["valid"] and any("stale" in e for e in r["errors"])


def test_missing_roles_refused():
    s, _, p = candidate()
    del p["band_roles"]
    _, err = harvest(s, p)
    assert any("no band role list" in e for e in err)


# ---- Tcl: std_band_fence.tcl on a mocked OpenDB (dbu 1000) ----
MOCK = r'''
set ::env(OT_BAND_Y) "10:20"
set ::env(RESULTS_DIR) [pwd]
namespace eval ord {}
namespace eval odb {}
proc ord::get_db_tech {} { return tech }
proc tech {m} { return 1000 }
proc ord::get_db_block {} { return blk }
proc core {m} { return [dict get {xMin 0 yMin 0 xMax 100000 yMax 100000} $m] }
set ::groups {}
proc blk {m args} {
  switch $m {
    getCoreArea { return core }
    getInsts { return $::insts }
    findGroup { return [expr {[dict exists $::groups [lindex $args 0]] ? "grp" : "NULL"}] }
    findRegion { return NULL }
  }
}
proc odb::dbRegion_create {b n} { return reg }
proc reg {m args} {}
proc odb::dbBox_create {args} {}
proc odb::dbGroup_create {r n} { dict set ::groups $n {}; return grp }
proc grp {m args} {
  switch $m {
    setType {}
    addInst { set i [lindex $args 0]; set ::owner($i) grp; dict lappend ::groups ot_std_band $i }
    getInsts { return [dict get $::groups ot_std_band] }
    getName { return ot_std_band }
  }
}
# inst: name status x y w h port clockdrv
proc mk {name status x y {port 0} {ck 0}} {
  set ::st($name) $status; set ::loc($name) [list $x $y]; set ::port($name) $port; set ::ck($name) $ck
  set ::owner($name) NULL
  proc $name {m args} "inst_m $name \$m {*}\$args"
  lappend ::insts $name
}
proc master {m} { return [dict get {isBlock 0 getType CORE getName BUFx2} $m] }
proc inst_m {n m args} {
  switch $m {
    getMaster { return master }
    getName { return $n }
    getPlacementStatus { return $::st($n) }
    setPlacementStatus { set ::st($n) [lindex $args 0] }
    getGroup { return $::owner($n) }
    getLocation { return $::loc($n) }
    setLocation { set ::loc($n) $args }
    getBBox { lassign $::loc($n) x y; return [list bb $x $y [expr {$x+1000}] [expr {$y+270}]] }
    getITerms { return [list [list it $n]] }
  }
}
proc bb {x0 y0 x1 y1 m} { return [dict get [list xMin $x0 yMin $y0 xMax $x1 yMax $y1] $m] }
proc it_m {n m args} {
  switch $m {
    getNet { return [list net $n] }
    isOutputSignal { return $::ck($n) }
    isInputSignal { return 0 }
  }
}
proc net_m {n m args} {
  switch $m {
    getSigType { return [expr {$::ck($n) ? "CLOCK" : "SIGNAL"}] }
    getBTerms { return [expr {$::port($n) ? [list [list bt]] : {}}] }
    getITerms { return {} }
  }
}
proc unknown {cmd args} {
  switch [lindex $cmd 0] {
    bb { return [bb {*}[lrange $cmd 1 4] [lindex $args 0]] }
    it { return [it_m [lindex $cmd 1] {*}$args] }
    net { return [net_m [lindex $cmd 1] {*}$args] }
    bt { return [expr {[lindex $args 0] eq "getSigType" ? "SIGNAL" : "d_in"}] }
  }
  error "unknown $cmd"
}
set ::insts {}
mk pf_s FIRM 5000 0            ;# pin flop FIRM at the S face (outside band)
mk pf_w FIRM 0 12000           ;# pin flop FIRM at the W face, inside the band y range
mk pbuf PLACED 6000 500 1      ;# port buffer on a port net, outside the band
mk u1 PLACED 50000 60000       ;# ordinary cell (GPL start anywhere)
source CHELPER
ot_band_fence_create
puts "MEMBERS [lsort [grp getInsts]]"
set fh [open ot_band_boundary.txt]; puts "BOUNDARY [lsort [split [string trim [read $fh]] \n]]"; close $fh
mk hb PLACED 50000 70000       ;# repair birth
mk ckb PLACED 40000 30000 0 1  ;# CTS clock buffer birth
puts "ADOPTED [ot_band_fence_adopt post_cts]"
puts "MEMBERS2 [lsort [grp getInsts]]"
puts "HBLOC $::loc(hb)"
set ::loc(u1) {50000 60000}    ;# member left outside the band (fence not honoured)
if {[catch {ot_band_fence_check post_cts} e]} { puts "CHECK_FAIL $e" } else { puts "CHECK_PASS" }
'''


def test_tcl_fence_membership_and_causal_check(tmp_path):
    helper = ROOT / "physical/common_flow/std_band_fence.tcl"
    script = MOCK.replace("CHELPER", str(helper))
    p = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, cwd=tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    out = dict(line.split(" ", 1) for line in p.stdout.splitlines() if line.split(" ", 1)[0] in
               ("MEMBERS", "BOUNDARY", "ADOPTED", "MEMBERS2", "HBLOC", "CHECK_FAIL", "CHECK_PASS"))
    assert out["MEMBERS"] == "pf_w u1"          # FIRM pin flop inside the band joins, ordinary cell joins
    assert out["BOUNDARY"] == "pbuf pf_s"       # FIRM / port-net cells outside the band stay out
    assert out["ADOPTED"] == "1"                # repair birth adopted; clock buffer kept out
    assert out["MEMBERS2"] == "hb pf_w u1"
    assert out["HBLOC"].split()[1] == "19730"   # seeded inside the band (20000 - 270)
    assert "u1" in out["CHECK_FAIL"]            # causal negative: a member outside the band is an error


def test_post_stage_extra_hooks_are_opt_in():
    base = dict(name='probe', kind='tile', recipe=3, clock='cts', pins={}, sources=[], macros=[], children=[], route={})
    cts, grt = 'physical/common_flow/std_band_post_cts.tcl', 'physical/common_flow/std_band_post_grt.tcl'
    s = dict(base, post_cts_extra=[cts], post_grt_extra=[grt])
    refs = R.referenced_paths(s, 'physical/ref_tile/probe')
    assert cts in refs and grt in refs
    assert cts not in R.referenced_paths(base, 'physical/ref_tile/probe')
