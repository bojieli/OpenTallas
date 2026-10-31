"""DIE-HEAD-42 V1 (FLOW-10 10-30): landed stations of a plan-siteless slot bit follow the bit's PLACED ring fan-in.

Runs the REAL face_flops.tcl station pass + ff_landed_line_place (tclsh, OpenDB mocked as in
test_face_flops_landed_ft.py).  Ring flop R placed at (40, 80) um, out pin S at (300, 50) um, k=3: stations s0, s1 go to
R + (S-R)*(i+1)/k; the out-face register s2 keeps its L*(j+1)/k place.  Before: s0/s1 stayed at the plan line
L*(j+1)/k from the in pin although the ring flop feeding s0 sits elsewhere (HEAD st_str r2r 510 um)."""
import re
import subprocess
from pathlib import Path

import test_face_flops_landed_ft as T

LP = Path(__file__).with_name("landing_placement.tcl").read_text()

EXTRA = r'''
set rn "u_cland_tx_i/u_ring/dch\[0\].y\[0\]\$_DFF_P_"
object bbr [dict create xMin 39500 xMax 40500 yMin 79500 yMax 80500]
dict set ::props($rn) getBBox bbr
foreach s {0 1 2} { dict set ::props(u_ft_tx_s$s/q\[0\]\$_DFF_P_) getLocation {0 0} }
set ff_x0 0; set ff_y0 0; set ff_cpitch 1; set ff_rh 1; set ff_gocc {}
set env(RESULTS_DIR) [pwd]
'''


def _run(tmp_path, regs="{}"):
    body = (T.MOCK + T._procs() + "\n"
            + "proc ff_put_near {f x y} { return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + f"design 1 {{}}\nset ff_done {{}}\nset ff_ft [dict create tx [list 3 W E {regs}]]\n" + T._station_pass()
            + EXTRA + "ff_landed_line_place\nputs \"MOVED $ff_landed_moved\"\n")
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True, cwd=tmp_path)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


def test_landed_stations_follow_the_placed_ring_flop(tmp_path):
    out = _run(tmp_path)
    assert "landed line: 2 stations of 1 plan-siteless landed bits" in out, out
    rows = [ln.split("\t") for ln in (tmp_path / "ot_landed_line.txt").read_text().splitlines()]
    assert [r[0] for r in rows] == ["u_ft_tx_s0/q[0]$_DFF_P_", "u_ft_tx_s1/q[0]$_DFF_P_"]
    got = [(round(float(r[2]), 3), round(float(r[3]), 3)) for r in rows]
    assert got == [(126.667, 70.0), (213.333, 60.0)], got
    assert "MOVED u_ft_tx_s0/q\\[0\\]$_DFF_P_ u_ft_tx_s1/q\\[0\\]$_DFF_P_" in out or "MOVED {u_ft_tx_s0" in out, out


def test_plan_sited_bits_keep_their_plan_sites(tmp_path):
    # regs_um given for all k stages: the plan contract wins, no station is re-placed
    out = _run(tmp_path, regs="{0 50 100 50 200 50}")
    assert "landed line: 0 stations of 0 plan-siteless landed bits" in out, out


def test_landing_placement_runs_the_line_pass_after_the_ring_is_placed():
    a = LP.index('puts "OT_CLAND placed $cland_n')
    b = LP.index("ff_landed_line_place", a)
    assert LP.index("cland_place_ff $prefix $rect $tag") < a < b


def test_landed_line_moves_get_their_reset_repointed():
    """AUTOBUILD-PIPE-2: S81 t14/t26 r2r 580-677 um = landed-line stations kept the reset tap chosen before they moved"""
    b = LP.index("ff_landed_line_place }")
    tail = LP[b:]
    assert "rt_repoint_only" in tail and tail.index("source /work/reset_taps.tcl") > tail.index("ff_landed_moved")
