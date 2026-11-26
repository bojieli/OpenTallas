"""place_log_gate (HEAD-INT-R2 11-26): synthetic logs shaped like the retained fed00 / ffbe77 lines."""
import place_log_gate as G

FED00_GPL = """OT_LOGIC_CLUSTER lep_rx0_nz_predict cells=8 skipped_fixed=0 cell_um2=0.9 rect_um2=128.9 util=0.007
OT_LOGIC_CLUSTER lep_rx0_nz_self cells=3 skipped_fixed=0 cell_um2=0.3 rect_um2=63.3 util=0.004
[INFO GPL-0100] Timing-driven iteration 1/2, virtual: false.
[INFO GPL-0101]    Iter: 1, overflow: 0.185, keep resizer changes at: 1, HPWL: 13086605568
[INFO RSZ-0038] Inserted 56515 buffers in 27960 nets.
[INFO GPL-0107] Timing-driven: repair_design delta area: 3668.736 um^2 (+25.53%)
[INFO GPL-0107] Timing-driven: repair_design delta area: 0.000 um^2 (+0.00%)
"""
FFBE77_GPL = """OT_LOGIC_CLUSTER west_lep_c20b_select cells=17 skipped_fixed=0 cell_um2=1.6 rect_um2=373.2 util=0.004
[INFO GPL-0100] Timing-driven iteration 1/2, virtual: false.
[INFO GPL-0101]    Iter: 170, overflow: 0.635, keep resizer changes at: 1, HPWL: 5107751599
[INFO RSZ-0038] Inserted 20234 buffers in 10570 nets.
[INFO GPL-0107] Timing-driven: repair_design delta area: 1140.987 um^2 (+13.33%)
[INFO GPL-0100] Timing-driven iteration 2/2, virtual: false.
[INFO GPL-0101]    Iter: 354, overflow: 0.186, keep resizer changes at: 1, HPWL: 5071508472
[INFO RSZ-0038] Inserted 14970 buffers in 10888 nets.
[INFO GPL-0107] Timing-driven: repair_design delta area: 100.412 um^2 (+1.04%)
"""
CLEAN = """[INFO GPL-0100] Timing-driven iteration 1/2, virtual: true.
[INFO GPL-0101]    Iter: 10, overflow: 0.7, keep resizer changes at: 0.3, HPWL: 100
[INFO RSZ-0038] Inserted 99999 buffers in 9 nets.
[INFO GPL-0100] Timing-driven iteration 2/2, virtual: false.
[INFO GPL-0101]    Iter: 300, overflow: 0.25, keep resizer changes at: 0.3, HPWL: 200
[INFO RSZ-0038] Inserted 120 buffers in 100 nets.
[INFO GPL-0107] Timing-driven: repair_design delta area: 20.0 um^2 (+1.20%)
"""


def test_passes_parse_and_virtual_passes_are_ignored():
    p = G.gpl_td_passes(FED00_GPL)
    assert len(p) == 1 and p[0]["iteration"] == 1 and p[0]["overflow"] == 0.185 and p[0]["buffers"] == 56515 and p[0]["area_pct"] == 25.53
    q = G.gpl_td_passes(CLEAN)
    assert len(q) == 1 and q[0]["buffers"] == 120


def test_fed00_fails_on_trigger_buffers_and_area():
    ok, why = G.gpl_td_verdict(FED00_GPL, cells=153589)
    assert not ok and any("iteration 1" in w and "regions" in w for w in why) and any("25.53" in w for w in why), why
    assert any("56515 buffers" in w for w in why), why        # 36.8 % of the 153589 movable cells
    ok, why = G.gpl_td_verdict(FED00_GPL, cells=153589, max_buffer_frac=0.4)
    assert not any("buffers >" in w for w in why) and not ok, why


def test_ffbe77_fails_on_the_area_of_pass_one_and_clean_passes():
    ok, why = G.gpl_td_verdict(FFBE77_GPL, cells=85000)
    assert not ok and any("13.33" in w for w in why), why
    assert G.gpl_td_verdict(CLEAN, cells=5000) == (True, [])
    # no clusters: a late small pass is fine and the early-trigger rule does not apply
    assert G.gpl_td_verdict(FED00_GPL.split("[INFO GPL-0100]")[0].replace("OT_LOGIC_CLUSTER", "x") + "[INFO GPL-0100] Timing-driven iteration 1/2, virtual: false.\n[INFO GPL-0101]    Iter: 1, overflow: 0.185, keep resizer changes at: 1, HPWL: 1\n[INFO RSZ-0038] Inserted 5 buffers in 5 nets.\n", cells=1000)[0]


def test_dpl_firm_released_must_be_zero():
    assert G.dpl_firm_released("OT_CLAND released 9 FIRM cland cells grown into an occupied site (in-place resize) for DPL\n") == (9, 0)
    ok, why = G.dpl_verdict("OT_CLAND released 9 FIRM cland cells grown into an occupied site (in-place resize) for DPL\n")
    assert not ok and "FIRM released = 9" in why[0]
    assert G.dpl_verdict("OT_CLAND released 0 FIRM cland cells grown into an occupied site (in-place resize) for DPL\n") == (True, [])
    ok, why = G.dpl_verdict("OT_CLAND released 0 FIRM cland cells x\nOT_FT_KEEP_FIRM released 3 keep_firm ft station cells placed\n")
    assert not ok and "keep_firm" in why[0]
    assert G.dpl_verdict("no such line")[0] is False


def test_cli_exit_codes(tmp_path):
    f = tmp_path / "dp.log"
    f.write_text("OT_CLAND released 9 FIRM cland cells\n")
    assert G.main(["x", "dpl", str(f)]) == 1
    f.write_text("OT_CLAND released 0 FIRM cland cells\n")
    assert G.main(["x", "dpl", str(f)]) == 0
    assert G.main(["x", "dpl", str(tmp_path / "missing")]) == 2


def _release(env=""):
    import shutil
    import subprocess
    import pytest
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh not installed")
    import gen_phys as GP
    mock = r"""
set ::I {{u_cland_a FIRM 0 10} {u_cland_b FIRM 6 16} {u_cland_c FIRM 40 50}}
set ff_blk blk
proc blk {op} { set r {}; foreach x $::I { lappend r "I:[lindex $x 0]" }; return $r }
proc inst_of {c} { foreach x $::I { if {"I:[lindex $x 0]" eq $c} { return $x } } }
proc unknown {cmd args} {
  if {[string match I:* $cmd]} { lassign [inst_of $cmd] n st x0 x1
    switch [lindex $args 0] { getName { return $n } getPlacementStatus { return $st } getMaster { return M } getBBox { return "B:$cmd" }
      setPlacementStatus { puts "STATUS $n [lindex $args 1]"; return } } }
  if {$cmd eq "M"} { return 0 }
  if {[string match B:* $cmd]} { lassign [inst_of [string range $cmd 2 end]] n st x0 x1
    switch [lindex $args 0] { xMin { return $x0 } yMin { return 0 } xMax { return $x1 } } }
  error "unknown $cmd $args"
}
proc ff_ft_keep_slot {n} { return "" }
"""
    mock = mock.replace("if {$cmd eq \"M\"} { return 0 }", "if {$cmd eq \"M\"} { switch [lindex $args 0] { isBlock { return 0 } getName { return DFFHQNx2 } } }")
    return subprocess.run(["tclsh"], input=mock + env + "\n" + GP.CLAND_RELEASE_GROWN_TCL, capture_output=True, text=True)


def test_release_scan_names_every_released_cell_and_fails_only_when_opted_in():
    r = _release()
    assert r.returncode == 0 and "OT_CLAND released 2 FIRM cland cells" in r.stdout, r.stdout + r.stderr
    assert "OT_CLAND_RELEASED_CELL u_cland_a DFFHQNx2" in r.stdout and "OT_CLAND_RELEASED_CELL u_cland_b DFFHQNx2" in r.stdout, r.stdout
    assert "u_cland_c" not in r.stdout
    r = _release('set ::env(OT_FIRM_RELEASE_FAIL) 1')
    assert "FIRM released = 2 cland cells (OT_FIRM_RELEASE_FAIL=1 requires 0)" in r.stderr + r.stdout, r.stdout + r.stderr   # tclsh stdin: the error is printed
    r = _release('set ::env(OT_FIRM_RELEASE_FAIL) 0')
    assert "requires 0" not in r.stdout + r.stderr
