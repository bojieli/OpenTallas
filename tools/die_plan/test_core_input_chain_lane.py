"""CB-CHAIN-LANE (QC-CB-SPREAD-R2 11-24): the NK chain route gives each bit of a bus its own lane across the street instead of
the street centre line (cbn_q00 west street: all 514 bits of pq_/lk_/lpad stacked in one gcell column)."""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "tools/die_plan/core_input_chain.tcl").read_text()


def tcl_procs(names):
    out = []
    for name in names:
        m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
        assert m, name
        i, depth = m.end(), 1
        while depth:
            c = SRC[i]
            i += 1
            if c == "\\":
                i += 1
                continue
            depth += (c == "{") - (c == "}")
        out.append(SRC[m.start():i])
    return "\n".join(out) + "\n"


PROCS = ["nc_lines", "nc_gaps", "nc_lane_pos", "nc_gap_of", "nc_route_lane", "nc_lane_key", "nc_hit", "nc_len", "nc_ok", "nc_route", "nc_route_bit"]


def run(body):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.tcl"
        f.write_text(tcl_procs(PROCS) + body)
        p = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        return p.stdout.split()


def test_file_is_complete_tcl():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.tcl"
        f.write_text("set f [open {%s}]; set s [read $f]; close $f; puts [info complete $s]\n" % (ROOT / "tools/die_plan/core_input_chain.tcl"))
        p = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
        assert p.stdout.strip() == "1"


def test_gaps_match_lines():
    out = run("set iv {{100 500} {700 1100}}\n"
              "puts [join [nc_lines 0 1200 $iv] ,]\n"
              "set m {}; foreach g [nc_gaps 0 1200 $iv] { lappend m [lindex $g 0] }; puts [join $m ,]\n"
              "puts [join [nc_gaps 0 1200 $iv] ,]\n")
    assert out[0] == out[1] == "50,600,1150"


def test_lane_spreads_bits_over_street():
    # street x 0..100, margin 10: bit 0 of 4 at 20, bit 3 at 80; the centre line would put all four at 50
    out = run("foreach b {0 1 2 3} { puts [nc_lane_pos 0 100 $b 4 10] }\nputs [nc_lane_pos 0 100 0 1 10]\nputs [nc_lane_pos 0 15 2 4 10]\n")
    assert out == ["20", "40", "60", "80", "50", "7"]


def test_route_lane_moves_street_legs_with_jogs():
    out = run("set xg {{50 0 100}}; set yg {}\n"
              # head (300,2500) -> centre x 50 -> tail (104,900): the long vertical leg moves to lane 80, head / tail stay
              "puts [join [join [nc_route_lane {{300 2500} {50 2500} {50 900} {104 900}} $xg $yg 3 4 10 20]] ,]\n"
              # the leg runs on the tail column x 100 (in the street): a jog before the tail
              "puts [join [join [nc_route_lane {{130 2500} {100 2500} {100 900}} $xg $yg 0 4 10 20]] ,]\n"
              # one bit only: unchanged; a short leg (< lmin): unchanged
              "puts [join [join [nc_route_lane {{300 2500} {50 2500} {50 900} {104 900}} $xg $yg 0 1 10 20]] ,]\n"
              "puts [join [join [nc_route_lane {{300 910} {50 910} {50 900} {104 900}} $xg $yg 0 4 10 20]] ,]\n"
              # a straight vertical leg head -> tail in the street: jog both ends
              "puts [join [join [nc_route_lane {{90 2500} {90 900}} $xg $yg 0 4 10 20]] ,]\n")
    assert out[0] == "300,2500,80,2500,80,900,104,900"
    assert out[1] == "130,2500,20,2500,20,900,100,900"
    assert out[2] == "300,2500,50,2500,50,900,104,900"
    assert out[3] == "300,910,50,910,50,900,104,900"
    assert out[4] == "90,2500,20,2500,20,900,90,900"


def test_lane_key():
    out = run("puts [join [nc_lane_key {u_bound.u_pc_nk_u_t_0_0_n_a.q[123]}] |]\n"
              "puts [join [nc_lane_key {u_r8b_strap_r8pad_u_t_0_0_n_a_f.r[2][17]$_DFF_P_}] |]\n"
              "puts [llength [nc_lane_key u_rst_in]]\n")
    assert out[0] == "u_bound.u_pc_nk_u_t_0_0_n_a.q[]|123"
    assert out[1] == "u_r8b_strap_r8pad_u_t_0_0_n_a_f.r[2][]$_DFF_P_|17"
    assert out[2] == "0"


def test_route_bit_lanes_and_falls_back():
    # dbu 1000: one macro 104..562 x 69..2445 um; head above it at (130, 2500), tail on its west face (100, 900)
    body = ("set nc_mac {{104000 69000 562000 2445000}}\nset nc_xs [nc_lines 0 1236000 {{104000 562000}}]\n"
            "set nc_ys [nc_lines 0 2566000 {{69000 2445000}}]\n"
            "set nc_xgap [nc_gaps 0 1236000 {{104000 562000}}]; set nc_ygap [nc_gaps 0 2566000 {{69000 2445000}}]\n"
            "set nc_lane_on 1; set nc_lane_m 11000; set nc_lane_lmin 20000; set nc_lane_used 0; set nc_lane_fallback 0\n"
            "set nc_lane_w [dict create {u_pc_nk_a.q[]} 4]\n"
            "foreach b {0 3} { puts [join [join [nc_route_bit 130000 2500000 100000 900000 \"u_pc_nk_a.q\\[$b\\]\"]] ,] }\n"
            "puts [join [join [nc_route_bit 130000 2500000 100000 900000 u_other]] ,]\n"
            "set nc_lane_on 0; puts [join [join [nc_route_bit 130000 2500000 100000 900000 {u_pc_nk_a.q[3]}]] ,]\n"
            "puts $nc_lane_used\n")
    out = run(body)
    # centre route: along the north street (y 2445..2566 um) to the tail column x 100 um (west street 0..104 um), down to the tail.
    # Bit b of 4 takes lane b of each street: x 21.25 / 82.75 um (11..93 um), y 2468.375 / 2542.625 um; head and tail unchanged.
    assert out[0] == "130000,2500000,130000,2468375,21250,2468375,21250,900000,100000,900000"
    assert out[1] == "130000,2500000,130000,2542625,82750,2542625,82750,900000,100000,900000"
    assert out[2] == out[3] == "130000,2500000,100000,2500000,100000,900000,100000,900000"
    assert out[4] == "2"
