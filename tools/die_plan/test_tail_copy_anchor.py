"""KV-HG-OPUS-SITE 11-18: bind tail-split copies are sited (tail_copy_anchor.tcl, wired by gen_phys.tail_copy_place).

The split alone did nothing on the QC st_a proof (wns -901 -> -912 ps, copy -> pin wire 1585 ps): GPL left the copies where
it liked.  The hook puts each copy's last stage 1.5 um off its core pin and stages 1..K-1 evenly on the line from the trunk
end (the L1 centre of the group's consumer pins, where bind sized K = ceil((S / 2) / hop)), FIRM at GPL, released for DPL.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as G

HERE = Path(__file__).resolve().parent
SRC = (HERE / "tail_copy_anchor.tcl").read_text()
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")


def proc(name):
    m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
    i, d = m.end(), 1
    while d:
        c = SRC[i]
        i += 1
        if c == "\\":
            i += 1
            continue
        d += (c == "{") - (c == "}")
    return SRC[m.start():i]


def tcl(tmp_path, names, body):
    f = tmp_path / "t.tcl"
    f.write_text("\n".join(proc(n) for n in names) + "\n" + body)
    return subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout.split()


@needs_tclsh
def test_trunk_end_is_the_l1_centre_so_the_longest_branch_is_half_the_spread(tmp_path):
    pts = [(0, 0), (1000, 0), (0, 600), (700, 900)]
    x, y = map(int, tcl(tmp_path, ["tcs_l1_centre"], "puts [tcs_l1_centre {{0 0} {1000 0} {0 600} {700 900}}]"))
    a = [p[0] + p[1] for p in pts]
    b = [p[0] - p[1] for p in pts]
    s = max(max(a) - min(a), max(b) - min(b))                       # bind_pad_tail_split.spread
    assert max(abs(x - px) + abs(y - py) for px, py in pts) == s / 2


@needs_tclsh
def test_hops_go_around_a_hard_core_and_stages_are_even_on_the_route(tmp_path):
    """kv3_pv_pair has OBS on M1-M7 (the signal ceiling): the straight / L route through the core is refused, the Z through the
    channel beside it is taken, and the K stages sit at equal routed length (hop = length / K)."""
    names = ["tcs_md", "tcs_seg_hits", "tcs_path_hits", "tcs_path_len", "tcs_route", "tcs_along"]
    out = tcl(tmp_path, names, """
set r [tcs_route {0 0} {300 0} {{100 -100 200 100}} 2]
puts [lindex $r 0]; puts [lindex $r 1]
foreach p [tcs_along $r 3] { puts [join $p ,] }
set r [tcs_route {0 0} {300 400} {{1000 1000 1100 1100}} 2]
puts [lindex $r 0]; puts [lindex $r 1]; puts [llength [lrange $r 2 end]]
foreach p [tcs_along $r 2] { puts [join $p ,] }
""")
    assert out[:5] == ["504", "0", "66,-102", "234,-102", "300,0"]
    assert out[5:8] == ["700", "0", "3"] and out[8:] == ["300,50", "300,400"]       # free L shape: plain Manhattan length


@needs_tclsh
def test_interior_targets_leave_the_macro_halo_and_snap_to_a_row_site(tmp_path):
    out = tcl(tmp_path, ["tcs_inside", "tcs_push_out", "tcs_snap"], """
puts [join [tcs_push_out 10 50 {{0 0 100 100}} 2] ,]
puts [join [tcs_push_out 50 97 {{0 0 100 100}} 2] ,]
puts [join [tcs_push_out 150 50 {{0 0 100 100}} 2] ,]
puts [join [tcs_push_out 99 50 {{0 0 100 100} {100 0 200 100}} 2] ,]
puts [join [tcs_snap 1003 2071 {0 0 5000 5000} 0 0 54 270] ,]
puts [join [tcs_snap -40 9000 {0 0 5000 5000} 0 0 54 270] ,]
""")
    assert out[0] == "-2,50,1" and out[1] == "50,102,1" and out[2] == "150,50,1"
    x, y, ok = map(int, out[3].split(","))
    assert ok == 1 and not (0 < x < 200 and 0 < y < 100)            # abutted macros: pushed out of both
    assert out[4] == "1026,2160" and out[5] == "0,4590"


@needs_tclsh
def test_only_listed_copies_are_recognised_kept_or_flat(tmp_path):
    out = tcl(tmp_path, ["tcs_copy_of"], r"""
set c [dict create u_pd3_a_0_pvg0_p0_29 {3 g}]
foreach n [list {u_bound.u_pd3_a_0_pvg0_p0_29/r[0]$_DFF_P_} {\u_bound.u_pd3_a_0_pvg0_p0_29/q$_DFF_P_} {u_bound.u_pd3_a_0_pvg0_p0_29.q$_DFF_P_} \
              {u_bound.u_pd26_a_0_t_29.q$_DFF_P_} {u_bound.u_pd3_a_0_pvg0_p1_29/q$_DFF_P_} {u_bound.u_pd29_a_0.r[3]$_DFF_P_}] {
  set r [tcs_copy_of $n $c]; puts [expr {$r eq "" ? "-" : $r}]
}
""")
    assert out == ["u_pd3_a_0_pvg0_p0_29"] * 3 + ["-"] * 3


BOUND = """module ts_bound(input clk);
    ot_dp_dly #(.W(1), .D(26)) u_pd26_i_a_cmd_0_t_29 (.clk(clk), .d(i_a_cmd_q[0]), .q(pd26_i_a_cmd_0_t_29));  // landing pad trunk: shared stages of pad 29 (tail split)
    ot_dp_dly_keep #(.W(1), .D(3)) u_pd3_i_a_cmd_0_pvg0_p0_29 (.clk(clk), .d(pd26_i_a_cmd_0_t_29[0]), .q(pd3_i_a_cmd_0_pvg0_p0_29));  // landing pad tail copy for core pvg0_p0: as-built relative timing
    ot_dp_dly_keep #(.W(1), .D(3)) u_pd3_i_a_cmd_0_pvg2_p0_29 (.clk(clk), .d(pd26_i_a_cmd_0_t_29[0]), .q(pd3_i_a_cmd_0_pvg2_p0_29));  // landing pad tail copy for core pvg2_p0: as-built relative timing
    ot_dp_dly #(.W(1), .D(2)) u_pd2_i_a_cmd_1_c1_2 (.clk(clk), .d(i_a_cmd_q[1]), .q(pd2_i_a_cmd_1_c1_2));  // landing pad tail copy for core c1: as-built relative timing
    ot_dp_dly #(.W(1), .D(4)) u_pd4_i_a_cmd_2 (.clk(clk), .d(i_a_cmd_q[2]), .q(pd4_i_a_cmd_2));  // landing pad: as-built relative timing
endmodule
"""


def _kit(tmp_path, rtl):
    kd = tmp_path / "kit"
    (kd / "rtl").mkdir(parents=True)
    (kd / "rtl" / "ts_bound.sv").write_text(rtl)
    (kd / "face_flops.tcl").write_text("uplevel #0 {source /work/landing_placement.tcl}\n")
    return kd


def test_gen_phys_lists_the_bind_copies_and_sources_the_hook(tmp_path):
    kd = _kit(tmp_path, BOUND)
    assert G.tail_copy_place(kd) == 3
    rows = [ln.split("\t") for ln in (kd / "tail_copies.tsv").read_text().splitlines() if not ln.startswith("#")]
    assert rows == [["u_pd3_i_a_cmd_0_pvg0_p0_29", "3", "pd26_i_a_cmd_0_t_29[0]/3", "pvg0_p0"],
                    ["u_pd3_i_a_cmd_0_pvg2_p0_29", "3", "pd26_i_a_cmd_0_t_29[0]/3", "pvg2_p0"],
                    ["u_pd2_i_a_cmd_1_c1_2", "2", "i_a_cmd_q[1]/2", "c1"]]        # trunk and plain pad are not copies
    ff = (kd / "face_flops.tcl").read_text()
    assert ff.endswith(G.TAIL_COPY_SITE_HOOK) and ff.index("landing_placement") < ff.index("tail_copy_anchor")
    assert (kd / "tail_copy_anchor.tcl").read_text() == SRC


def test_no_copies_no_change(tmp_path):
    kd = _kit(tmp_path, BOUND.replace("tail copy", "x"))
    before = (kd / "face_flops.tcl").read_text()
    assert G.tail_copy_place(kd) == 0
    assert (kd / "face_flops.tcl").read_text() == before and not (kd / "tail_copies.tsv").exists()
    assert not (kd / "tail_copy_anchor.tcl").exists()


@needs_tclsh
def test_hook_reads_the_gen_phys_table(tmp_path):
    kd = _kit(tmp_path, BOUND)
    G.tail_copy_place(kd)
    out = tcl(tmp_path, ["tcs_read_tsv"], f"""
set d [tcs_read_tsv {kd / 'tail_copies.tsv'}]
dict for {{c v}} $d {{ puts "$c|[join $v |]" }}
""")
    assert out == ["u_pd3_i_a_cmd_0_pvg0_p0_29|3|pd26_i_a_cmd_0_t_29[0]/3", "u_pd3_i_a_cmd_0_pvg2_p0_29|3|pd26_i_a_cmd_0_t_29[0]/3",
                   "u_pd2_i_a_cmd_1_c1_2|2|i_a_cmd_q[1]/2"]


def test_kit_writer_wiring_and_hook_contract():
    gp = (HERE / "gen_phys.py").read_text()
    i = gp.index("    tail_copy_place(kd)\n")
    assert gp.rindex("if core_input_place(P.raw, tn):", 0, i) > gp.rindex("def ", 0, i)     # same kit writer, after the NK anchor
    run = SRC[SRC.index("proc tcs_run"):]
    assert "tcs_out_pos $pin 1.5 $dbu" in run and "tcs_route $t $l $raw $halo" in run and "tcs_along $route $k" in run
    assert "setPlacementStatus FIRM" in run and "ot_face_flops.txt" in run          # FIRM at GPL, released for DPL
    assert "/work/tail_copies.tsv" in run and run.rstrip().endswith("tcs_run")
    assert "[llength $macs] != 1" in run and "[llength $ffs] != $k" in run          # merged / shared copies are left alone


# ---- KV-D23-REACH 11-18: pipe copies and reset spine relay copies ride the same hook ------------------------------------------
BOUND_D23 = """module ts_bound(input clk);
    ot_dp_dly #(.W(512), .D(56)) u_d60_vport_W_out_v_hi_t (.clk(clk), .d(w_vport_W_out_v_hi), .q(d60_vport_W_out_v_hi_t));  // pipe trunk: shared stages of the 60-stage pipe (tail split)
    ot_dp_dly_keep #(.W(1), .D(4)) u_pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60 (.clk(clk), .d(d60_vport_W_out_v_hi_t[7]), .q(pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60));  // landing pad tail copy for core pvg0_p2: pipe tail, as-built relative timing
    ot_dp_rsync #(.W(1), .S(2)) u_rs_ri_pv_u_g0_j_rst_n (.clk(clk), .a(ri_pv_u_g0_j_rst_n), .q(ri_pv_u_g0_j_rst_n_q));  // KV-D23-REACH: synchroniser, 4 relay stage(s) replicated per region
    ot_dp_rtail #(.D(4)) u_rs_ri_pv_u_g0_j_rst_n_r3 (.clk(clk), .a(ri_pv_u_g0_j_rst_n), .d(ri_pv_u_g0_j_rst_n_q[0]), .q(rs_ri_pv_u_g0_j_rst_n_r3[0]));  // landing pad tail copy for core u_pvg0_p2: reset spine relay (2 load(s)); 6 stage(s) total
endmodule
"""


def test_gen_phys_lists_pipe_and_reset_copies(tmp_path):
    kd = _kit(tmp_path, BOUND_D23)
    assert G.tail_copy_place(kd) == 2
    rows = [ln.split("\t") for ln in (kd / "tail_copies.tsv").read_text().splitlines() if not ln.startswith("#")]
    assert rows == [["u_pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60", "4", "d60_vport_W_out_v_hi_t[7]/4", "pvg0_p2"],
                    ["u_rs_ri_pv_u_g0_j_rst_n_r3", "4", "ri_pv_u_g0_j_rst_n_q[0]/4", "u_pvg0_p2"]]


@needs_tclsh
def test_hook_names_reset_copies_and_pipe_trunks(tmp_path):
    out = tcl(tmp_path, ["tcs_copy_of", "tcs_is_trunk"], r"""
set c [dict create u_rs_ri_pv_u_g0_j_rst_n_r3 {4 g} u_pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60 {4 h}]
foreach n [list {u_bound.u_rs_ri_pv_u_g0_j_rst_n_r3.r[2]$_DFF_PN0_} {u_bound.u_rs_ri_pv_u_g0_j_rst_n_r4.r[2]$_DFF_PN0_} \
              {u_bound.u_rs_ri_pv_u_g0_j_rst_n.b[0].r[1]$_DFF_PN0_} {u_bound.u_pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60.r[3]$_DFF_P_}] {
  set r [tcs_copy_of $n $c]; puts [expr {$r eq "" ? "-" : $r}]
}
foreach n [list {u_bound.u_d60_vport_W_out_v_hi_t.r[55][7]$_DFF_P_} {u_bound.u_pd26_a_0_t_29.q$_DFF_P_} {u_bound.u_d60_vport_W_out_v_hi.r[59][7]$_DFF_P_} \
              {u_bound.u_pd3_a_0_pvg0_p0_29.q$_DFF_P_} {u_bound.u_d60_x_t_y.r[1]$_DFF_P_}] {
  puts [tcs_is_trunk $n]
}
""")
    assert out == ["u_rs_ri_pv_u_g0_j_rst_n_r3", "-", "-", "u_pd4_d60_vport_W_out_v_hi_7_pvg0_p2_60", "1", "1", "0", "0", "0"]
