"""RELAY-PLACE-1 11-12 (FT-LANE): ft stations of a slot with plan regs_um (one site per stage = the slot centre line)
keep each bit on its own lane, site + the bit's pin offset from the slot pin centroid blended in -> out, instead of all
W bits spiralling around one point (S81 slice_station t41 a7: face flop at pin y 485 -> stage-1 blob at y 367 = 447-um
hop, relay_collapse 131).  Real face_flops.tcl walkers + station pass in tclsh, OpenDB mocked (test_face_flops_landed_ft)."""
import os
import subprocess

import test_face_flops_landed_ft as T

# two-bit slot tx, k=3, W -> E, frame 0..300 um; in pins at y 40 / 60, out pins at y 30 / 70 (centroids 50 / 50)
DESIGN = r'''
proc design2 {landed} {
 set bts {}
 foreach b {0 1} yi {40000 60000} yo {30000 70000} {
  if {$landed} {
   cell "u_cland_tx_i/u_ring/dch\[0\].y\[$b\]\$_DFF_P_" mff [list D n_in$b CLK clkf] [list QN n_r$b]
   cell "u_cland_tx_i/u_ring/rd_mux\[$b\]" mlog [list A n_r$b] [list Y n_land$b]
   set d0 n_land$b
  } else { cell buf_in$b mbuf [list A n_in$b] [list Y n_b$b]; set d0 n_b$b }
  cell "u_ft_tx_s0/q\[$b\]\$_DFF_P_" mff [list D $d0 CLK clk] [list QN n_s0$b]
  cell inv01$b minv [list A n_s0$b] [list Y n_s0b$b]
  cell "u_ft_tx_s1/q\[$b\]\$_DFF_P_" mff [list D n_s0b$b CLK clk] [list QN n_s1$b]
  cell buf12$b mbuf [list A n_s1$b] [list Y n_s1b$b]
  cell "u_ft_tx_s2/q\[$b\]\$_DFF_P_" mff [list D n_s1b$b CLK clk] [list QN n_out$b]
  bbox bbi$b 0 $yi; bbox bbo$b 300000 $yo
  object bti$b [dict create getSigType SIGNAL getIoType INPUT getName "tx_i\[$b\]" getNet n_in$b getBBox bbi$b]
  object bto$b [dict create getSigType SIGNAL getIoType OUTPUT getName "tx_o\[$b\]" getNet n_out$b getBBox bbo$b]
  lappend bts bti$b bto$b
 }
 object blk [dict create getBTerms $bts]
 proc blk {method args} {
  if {$method eq "findBTerm"} { if {[regexp {^tx_o\[([01])\]$} [lindex $args 0] -> b]} { return bto$b }; return NULL }
  return [dict get $::props(blk) $method]
 }
}
'''


REPORT = next(ln for ln in T.SRC.splitlines() if ln.startswith("if {$ff_lane_bits}"))


def _run(landed, regs, lane=None):
    body = (T.MOCK + DESIGN + T._procs() + "\n"
            + "proc ff_put_near {f x y} { return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + f"design2 {landed}\nset ff_done {{}}\nset ff_ft [dict create tx [list 3 W E {{{regs}}}]]\n"
            + T._station_pass() + "\n" + REPORT
            + '\nputs "RESULT st=$ff_st miss=$ff_st_miss lst=$ff_lst bits=$ff_lane_bits"\n')
    env = dict(os.environ)
    env.pop("OT_FT_LANE", None)
    if lane is not None:
        env["OT_FT_LANE"] = lane
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True, env=env)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


def _rows(out, tag):
    return {(r[0], r[1]): (float(r[2]), float(r[3])) for r in (ln.split("\t") for ln in out.splitlines())
            if r[1:2] and r[1].startswith(tag)}


REGS = "0 50 110 50 210 50"


def test_unlanded_plan_sites_keep_each_bit_on_its_lane():
    out = _run(0, REGS)
    assert "RESULT st=4 miss=0 lst=0 bits=2" in out, out
    got = _rows(out, "st")
    # t = j/k: dy = (1-t)(pin_in - 50) + t(pin_out - 50); bit 0: -10 -> -20, bit 1: +10 -> +20
    assert got[("u_ft_tx_s1/q[0]$_DFF_P_", "st1")] == (110.0, 36.667)
    assert got[("u_ft_tx_s2/q[0]$_DFF_P_", "st2")] == (210.0, 33.333)
    assert got[("u_ft_tx_s1/q[1]$_DFF_P_", "st1")] == (110.0, 63.333)
    assert got[("u_ft_tx_s2/q[1]$_DFF_P_", "st2")] == (210.0, 66.667)
    assert "OT_FT_LANE on: 2 slot bits" in out, out


def test_lane_off_restores_slot_point_form():
    out = _run(0, REGS, lane="0")
    got = _rows(out, "st")
    assert {v for k, v in got.items() if k[1] == "st1"} == {(110.0, 50.0)}
    assert {v for k, v in got.items() if k[1] == "st2"} == {(210.0, 50.0)}
    assert "OT_FT_LANE off (OT_FT_LANE=0)" in out, out


def test_landed_plan_sites_keep_each_bit_on_its_lane():
    # landed: station i takes plan stage i+1 (t = (i+1)/k); the last station is the out-face register (per-bit route)
    out = _run(1, REGS)
    assert "RESULT st=0 miss=0 lst=6 bits=2" in out, out
    got = _rows(out, "lst")
    assert got[("u_ft_tx_s0/q[0]$_DFF_P_", "lst0")] == (110.0, 36.667)
    assert got[("u_ft_tx_s1/q[1]$_DFF_P_", "lst1")] == (210.0, 66.667)
    assert got[("u_ft_tx_s2/q[0]$_DFF_P_", "lst2")] == (300.0, 30.0)
    assert got[("u_ft_tx_s2/q[1]$_DFF_P_", "lst2")] == (300.0, 70.0)


def test_siteless_slot_unchanged_per_bit_route():
    # no regs_um: stations already follow each bit's own Z route (L*j/k); FT-LANE does not touch them
    on, off = _rows(_run(0, ""), "st"), _rows(_run(0, "", lane="0"), "st")
    assert on == off and len(on) == 4


def test_hop_report_counts_hops_over_reach():
    # lane report: 1 bit hop from st1 (110) to st2 (210) = 100 um + |dy| < 405
    out = _run(1, REGS)
    line = next(ln for ln in out.splitlines() if ln.startswith("OT_FT_LANE"))
    assert "0 hops > 405 um" in line, line
    hop = float(line.split("max placed station hop ")[1].split(" um")[0])
    assert 90.0 < hop < 110.0, line
