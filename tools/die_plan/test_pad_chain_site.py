"""PAD-CHAIN-SITE (FABLE-FIX-QC 11-18): landing-pad chains are sited from the kit netlist (pad_chain_site.tcl, wired by
gen_phys.pad_chain_site_place under the gen env OT_PAD_CHAIN_SITE).

QC sle_ctl x7 (N4 kits): one plan relay_sites table keyed by pad depth served seven types with other depths (10,100..13,316 of
21,808 keys matched nothing), and the matched x_fw_i chain ended at the consumer core's rectangle, 651 um from its pin on the
core's far edge (102 ends to -97.9 ps TT at CTS).  The hook derives launch, captures and the tail point in the kit.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as G

HERE = Path(__file__).resolve().parent
SRC = (HERE / "pad_chain_site.tcl").read_text()
TCS = (HERE / "tail_copy_anchor.tcl").read_text()
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")


def proc(name, src=None):
    src = SRC if src is None else src
    m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", src, re.M)
    i, d = m.end(), 1
    while d:
        c = src[i]
        i += 1
        if c == "\\":
            i += 1
            continue
        d += (c == "{") - (c == "}")
    return src[m.start():i]


TCS_PURE = ["tcs_l1_centre", "tcs_inside", "tcs_push_out", "tcs_seg_hits", "tcs_path_hits", "tcs_path_len", "tcs_route", "tcs_frac", "tcs_md"]


def tcl(tmp_path, names, body):
    f = tmp_path / "t.tcl"
    f.write_text("\n".join(proc(n, TCS) for n in TCS_PURE) + "\n" + "\n".join(proc(n) for n in names) + "\n" + body)
    return subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout.split()


@needs_tclsh
def test_chain_name_is_a_pad_chain_stage_and_nothing_else(tmp_path):
    out = tcl(tmp_path, ["pcs_chain_of"], r"""
foreach n {{u_bound.u_pd11_x_fw_i_236.q$_DFF_P_} {u_bound.u_pd11_x_fw_i_236.r\[9\]$_DFF_P_} {u_pd6_x_fw_p1_i_507/q$_DFF_P_}
           {u_bound.u_lpad_x_fw_i.q\[236\]$_DFF_P_} {u_bound.u_ist_x_fw_o_0/q\[2\]$_DFF_P_} {u_bound.u_pd11_x_fw_i_236.other$_DFF_P_}} {
  set c [pcs_chain_of $n]; puts [expr {$c eq "" ? "-" : $c}]
}""")
    assert out == ["u_pd11_x_fw_i_236", "u_pd11_x_fw_i_236", "u_pd6_x_fw_p1_i_507", "-", "-", "-"]


@needs_tclsh
def test_tail_leaves_the_core_towards_the_far_edge_pin_not_the_core_rectangle(tmp_path):
    """sle_ctl__cl372cea1c bit 236: the consumer pin sits on the TOP edge of u_u_ctl (550, 596), two FIRM stations south-east of
    it.  The L1 centre is inside the core; the tail goes to the middle of the routed path between the two farthest captures, so
    no capture is more than about half that path away (386 um), where the stale plan row left 651 um to the pin."""
    out = tcl(tmp_path, ["pcs_extremes", "pcs_tail"], """
set raw {{475212 336972 820812 596172} {164172 328332 466572 457932}}
set halo 9000; set boxes {}
foreach b $raw { lassign $b a c d e; lappend boxes [list [expr {$a-$halo}] [expr {$c-$halo}] [expr {$d+$halo}] [expr {$e+$halo}]] }
set pts {{908000 183000} {1001000 321000} {550000 597672}}
lassign [pcs_tail $pts $boxes $raw $halo 54] x y
puts "$x $y [expr {[tcs_inside $x $y $boxes] eq {}}]"
set w 0; foreach p $pts { set l [lindex [tcs_route [list $x $y] $p $raw $halo] 0]; if {$l > $w} { set w $l } }
puts $w
""")
    x, y, clear, worst = map(int, out)
    assert clear == 1 and x > 829812 and worst < 400000            # right of the core, under the 651 um of the stale row
    assert abs(x - 550000) + abs(y - 597672) == pytest.approx(386336, abs=2000)


@needs_tclsh
def test_tail_is_the_l1_centre_when_it_is_in_free_area(tmp_path):
    out = tcl(tmp_path, ["pcs_extremes", "pcs_tail"], """
puts [pcs_tail {{0 0} {1000 0} {0 600}} {{5000 5000 6000 6000}} {{5010 5010 5990 5990}} 10 5]
""")
    x, y = map(int, out)                      # u = x + y mid-range 500, v = x - y mid-range 200
    assert (x, y) == (350, 150) and max(abs(x - px) + abs(y - py) for px, py in [(0, 0), (1000, 0), (0, 600)]) == 800


@needs_tclsh
def test_stages_take_equal_hops_including_the_capture_fan(tmp_path):
    """n stages between launch and tail, the far capture rb beyond the tail: every hop is (route + rb) / (n + 1); a stage never
    passes the tail (the rest of the chain waits there)."""
    out = tcl(tmp_path, ["pcs_stage_points"], """
foreach p [pcs_stage_points {900 0 {0 0} {900 0}} 2 0] { puts [lindex $p 0] }
foreach p [pcs_stage_points {600 0 {0 0} {600 0}} 3 400] { puts [lindex $p 0] }
""")
    assert list(map(int, out)) == [300, 600, 250, 500, 600]


def test_hook_is_opt_in_and_wired_after_the_plan_sites(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "face_flops.tcl").write_text("# face flops\n")
    (kd / "config.mk").write_text("export A = 1\n")
    assert G.pad_chain_site_place(kd, env={}) is None and G.pad_chain_site_place(kd, env={"OT_PAD_CHAIN_SITE": "off"}) is None
    assert (kd / "face_flops.tcl").read_text() == "# face flops\n" and not (kd / "pad_chain_site.tcl").exists()
    assert G.pad_chain_site_place(kd, env={"OT_PAD_CHAIN_SITE": "auto"}) == "auto"
    assert (kd / "face_flops.tcl").read_text().rstrip().endswith("uplevel #0 {source /work/pad_chain_site.tcl}")
    assert (kd / "config.mk").read_text().endswith("export OT_PAD_CHAIN_SITE = auto\n")
    assert (kd / "pad_chain_site.tcl").read_text() == SRC and (kd / "tail_copy_anchor.tcl").read_text() == TCS
    with pytest.raises(ValueError):
        G.pad_chain_site_place(kd, env={"OT_PAD_CHAIN_SITE": "yes"})


def test_hook_keeps_plan_sited_chains_unless_stale_and_never_touches_tail_copies():
    assert 'if {$firm && $mode eq "unsited"} { incr kept; continue }' in SRC
    assert "if {$firm == $k && $far <= $hop_um * $dbu} { incr kept; continue }" in SRC
    assert "[dict exists $copies $c] || [tcs_is_trunk $nm]" in SRC
    assert "pcs_pin_out" in SRC and "tcs_out_pos $it 1.5" in SRC     # captures at the pin face, not at the core rectangle


@needs_tclsh
def test_origin_flops_are_recognised_and_sited_only_when_the_start_loads_are_spread(tmp_path):
    """ORIGIN-SITE (FABLE-FIX-QC 11-19): QC st_b, u_cland_origin at (99,470) with 13 loads near it and u_cland_rstart_tx at
    (313,1331): 1,075 um in one hop, -106.2 ps TT at GRT.  The origin's synchroniser input is asynchronous, so its flops go to the
    point with the smallest largest routed distance to the FIRM captures of start (622 um here); captures within the reach = left to GPL."""
    out = tcl(tmp_path, ["pcs_origin_of", "pcs_extremes", "pcs_tail"], r"""
foreach n {{u_bound.u_cland_origin/s2$_SDFF_PN0_} {u_bound.u_cland_origin/pd$_SDFF_PN0_} {u_bound.u_cland_origin.pd\[2\]$_SDFF_PN0_}
           {u_bound.u_cland_origin/sf$_DFF_N_} {u_bound.u_cland_rstart_tx/q$_SDFF_PN0_} {u_bound.u_cland_origin_x/s2$_DFF_P_}} {
  set o [pcs_origin_of $n]; puts [expr {$o eq "" ? "-" : [lindex $o 1]}]
}
set pts {{87000 535800} {77900 600900} {71500 330300} {82000 759900} {175500 316600} {118600 309300} {313100 1331500}
         {146900 320600} {205000 319800} {6200 530700} {5100 397800} {5000 605200} {5000 726200}}
lassign [pcs_tail $pts {} {} 9000 54] x y
set w 0; foreach p $pts { set d [expr {abs($x - [lindex $p 0]) + abs($y - [lindex $p 1])}]; if {$d > $w} { set w $d } }
puts $w
""")
    assert out[:6] == ["s2", "pd", "pd[2]", "sf", "-", "-"]
    assert 600000 < int(out[6]) < 640000                      # 1,075 um today
    assert "if {$spread <= $hop_um * $dbu} { incr nnear; continue }" in SRC and "pcs_run; pcs_origin_run" in SRC
