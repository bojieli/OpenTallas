"""FLOW-KITFAIL-3 10-29 (KV kv3_io_ft landed: 1052 ft stations missing): a landed slot whose plan carries explicit bit
sites (ft_bit_sites.tcl) or regs_um places station i at plan stage i+1 (the landed target L*(i+1)/k) and the last
station at the out face, instead of failing closed.  Real face_flops.tcl walkers + station pass in tclsh."""
import subprocess

import test_face_flops_landed_ft as T

SITES = r'''
foreach c [array names ::props] {
  if {[string match {u_ft_tx_s*} $c] && ![string match {*.*} $c]} {
    set ::props($c) [dict merge $::props($c) [dict create getPlacementStatus PLACED setPlacementStatus {} setOrient {} setLocation {}]]
  }
}
set ::props(mff) [dict merge $::props(mff) [dict create getHeight 270]]
set ff_x0 0; set ff_y0 0; set ff_x1 400000; set ff_y1 100000; set ff_sw 54
set ff_orient [dict create 40230 R0 60210 MX]
set ff_bit_site_cells [dict create tx {1.404 0.27}]
set ff_bit_sites [dict create tx,1,0 {90.018 40.23} tx,2,0 {190.026 60.21}]
'''


def _run(landed, explicit, regs=""):
    body = (T.MOCK + T._procs() + "\n"
            + "proc ff_put_near {f x y} { return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + f"design {landed} {{}}\n" + (SITES if explicit else "")
            + f"set ff_done {{}}\nset ff_ft [dict create tx [list 3 W E {{{regs}}}]]\n" + T._station_pass()
            + '\nputs "RESULT st=$ff_st miss=$ff_st_miss lst=$ff_lst"\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


def _rows(out, tag):
    return [(r[0], r[1], float(r[2]), float(r[3])) for r in (ln.split("\t") for ln in out.splitlines()) if r[1:2] and r[1].startswith(tag)]


def test_landed_slot_with_explicit_sites_uses_stage_i_plus_1():
    out = _run(1, True)
    assert "RESULT st=0 miss=0 lst=3" in out, out
    assert _rows(out, "lst") == [("u_ft_tx_s0/q[0]$_DFF_P_", "lst0", 90.018, 40.23),
                                 ("u_ft_tx_s1/q[0]$_DFF_P_", "lst1", 190.026, 60.21),
                                 ("u_ft_tx_s2/q[0]$_DFF_P_", "lst2", 300.0, 50.0)]


def test_landed_slot_with_plan_regs_uses_stage_i_plus_1():
    # regs_um: stage 0 at the in face (unused when landed), stages 1, 2 at the plan sites; last station at the out face
    out = _run(1, False, regs="0 50 110 55 210 45")
    assert "RESULT st=0 miss=0 lst=3" in out, out
    assert [(r[2], r[3]) for r in _rows(out, "lst")] == [(110.0, 55.0), (210.0, 45.0), (300.0, 50.0)]


def test_unlanded_explicit_sites_unchanged():
    out = _run(0, True)
    assert "RESULT st=2 miss=0 lst=0" in out, out
    assert [(r[1], r[2], r[3]) for r in _rows(out, "st")] == [("st1", 90.018, 40.23), ("st2", 190.026, 60.21)]
