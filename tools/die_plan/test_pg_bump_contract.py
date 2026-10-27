"""One plan-owned bump geometry in full-die and window emitters; actual Tcl overlap controls."""
from types import SimpleNamespace
import subprocess
import pytest
import die_trial as D


def plan(**cfg):
    return SimpleNamespace(W=25194.24, H=2000., die={"pg": {"bumps": cfg}})


def test_edge_fill_preserves_pitch_and_parity():
    old = D.bump_grid(plan(), [])
    new = D.bump_grid(plan(pitch_um=150., pad_um=70., edge_margin_um=60.), [])
    assert min(x for _, x, _ in old) == 147.12
    assert min(x for _, x, _ in new) == 72.12
    xs = sorted({x for _, x, _ in new})
    assert len(xs) == 168 and all(abs(b-a-150) < 1e-8 for a,b in zip(xs,xs[1:]))
    y = min(y for _, _, y in new)
    assert [n for n,x,yy in new if yy == y][:4] == ["VDD", "VSS", "VDD", "VSS"]


def test_plan_bump_contract_validation():
    for c in [{"pitch_um": 0}, {"pad_um": 150}, {"pad_um": float("nan")},
              {"pad_um": 70, "edge_margin_um": 20}, {"pitch_um": True}]:
        with pytest.raises(ValueError):
            D.bump_grid(plan(**c), [])
    p=plan(pad_um=70.)
    assert "set pad_half [expr {round(70*$bump_dbu/2.0)}]" in D.bumps_tcl(p, [("VDD",75,75)])
    assert D.bumps_tcl(plan(), [("VDD",75,75)]) == D.bumps_tcl(None, [("VDD",75,75)],pad_um=0.)


MOCK = r'''namespace eval ord {}
namespace eval odb {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m args} {if {$m eq "findLayer"} {return M9};return 1}
proc blk {m args} {if {$m eq "findBTerm"} {return NULL};return n_[lindex $args 0]}
proc n_VDD {m} {return w_VDD}
proc n_VSS {m} {return w_VSS}
proc w_VDD {m} {return {s0 s1}}
proc w_VSS {m} {return s2}
set rect [dict create s0 {50 0 55 200} s1 {100 0 105 200} s2 {75 0 80 200}]
proc shape {id m} {global rect; switch $m {isVia {return 0} getTechLayer {return M9} xMin {return [lindex [dict get $rect $id] 0]} yMin {return [lindex [dict get $rect $id] 1]} xMax {return [lindex [dict get $rect $id] 2]} yMax {return [lindex [dict get $rect $id] 3]}}}
foreach id {s0 s1 s2} {interp alias {} $id {} shape $id}
proc odb::dbBTerm_create {net name} {return term}
proc term {args} {}
proc odb::dbBPin_create {term} {return pin}
proc pin {args} {}
set boxes {}
proc odb::dbBox_create {pin layer args} {global boxes;lappend boxes $args}
'''


def run_pad(bumps):
    return subprocess.run(["tclsh"], input=MOCK+"\nif {[catch {\n"+D.bumps_tcl(plan(pad_um=70.),bumps)+"\n} msg]} {puts stderr $msg; exit 7}\n"+
                          '\nputs "BOXES $boxes"\n', text=True, capture_output=True)


def test_actual_tcl_contacts_all_and_only_same_net_overlaps():
    r=run_pad([("VDD",75,75)])
    assert "BOXES {50 40 55 110} {100 40 105 110}" in r.stdout, r.stdout+r.stderr
    assert "pad_fallback 0" in r.stdout
    assert "{75 40 80 110}" not in r.stdout


def test_actual_tcl_pad_missing_metal_fails_without_point_fallback():
    r=run_pad([("VDD",300,75)])
    assert "pad misses actual same-net M9 metal" in r.stderr
    assert r.returncode == 7 and "OT_BUMPS pad_um" not in r.stdout


def test_complete_pad_stays_out_of_signal_window():
    p=plan(pad_um=70.)
    first=D.bump_grid(p,[])[0]
    n,x,y=first
    win=[{"rect_um":[x+20,y-10,x+40,y+10]}]
    assert first not in D.bump_grid(p,win)
    assert first in D.bump_grid(plan(),win)
