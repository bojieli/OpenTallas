"""gen_phys logic_cluster_rects_um (QC-GLUE 11-25, opt-in)."""
from types import SimpleNamespace as N
import pytest
import logic_cluster as LC


def plan(rows):
    t = dict(outline_um=[100, 50])
    if rows is not None:
        t["logic_cluster_rects_um"] = rows
    return N(types={"T": t})


ROW = dict(name="rec", patterns=[r"^u_bound\.u_sys_face\.u_ot_pr_core\.u_record\."], rect_um=[10, 5, 60, 40])


def test_absent_key_emits_nothing():
    assert LC.tcl(plan(None), "T") == ""


def test_emits_region_group_and_checks():
    s = LC.tcl(plan([ROW, dict(name="rx", patterns=["rx_payload__ot_q", "u_head_tx"], rect_um=[0, 0, 5, 5])]), "T")
    assert "odb::dbRegion_create" in s and "INCLUSIVE" in s and "odb::dbGroup_create $reg $name" in s
    assert "ot_logic_cluster rec 10 5 60 40 [list {" in s
    assert "matches no instance" in s and "exceeds 0.7" in s
    assert s.count("\not_logic_cluster ") == 2 and "{rx_payload__ot_q} {u_head_tx}" in s


@pytest.mark.parametrize("row,msg", [
    (dict(ROW, rect_um=[90, 0, 101, 5]), "outside"),
    (dict(ROW, rect_um=[5, 5, 5, 6]), "outside"),
    (dict(ROW, patterns=[]), "patterns"),
    (dict(ROW, patterns=["a{2}"]), "braces"),
    (dict(ROW, patterns=["("]), "missing|unterminated"),
    (dict(ROW, name="1x"), "invalid"),
    (dict(ROW, rect_um=[1, 2, 3]), "four"),
])
def test_bad_rows_fail_closed(row, msg):
    with pytest.raises(Exception, match=msg):
        LC.tcl(plan([row]), "T")


def test_repeated_name_and_empty_list_fail():
    with pytest.raises(ValueError, match="repeated"):
        LC.tcl(plan([ROW, ROW]), "T")
    with pytest.raises(ValueError, match="non-empty"):
        LC.tcl(plan([]), "T")


def test_cluster_inside_effective_phy_row_cut_fails_early():
    domains = [("phy", [0, 400, 2885.76, 1226.88])]
    r7e2 = dict(ROW, name="serdes_syndrome_local", rect_um=[1935.36, 400.68, 2073.6, 423.36])
    r7e3 = dict(r7e2, rect_um=[2201.04, 352.08, 2304.72, 382.32])
    crossing = dict(r7e2, rect_um=[1935.36, 395.28, 2073.6, 416.88])

    def emit(row, no_core_rows=()):
        p = N(types={"hd_serdes": dict(outline_um=[2885.76, 1226.88], logic_cluster_rects_um=[row])})
        return LC.tcl(p, "hd_serdes", no_core_rows=no_core_rows)

    with pytest.raises(ValueError, match="serdes_syndrome_local is fully inside PHY domain phy"):
        emit(r7e2, domains)
    for row in (r7e3, crossing):
        assert emit(row, domains) == emit(row)
    assert "ot_logic_cluster serdes_syndrome_local" in emit(r7e2)


def test_gen_phys_wires_the_hook():
    import gen_phys as GP
    from pathlib import Path
    src = Path(GP.__file__).read_text()
    assert "logic_cluster.tcl" in src and "import logic_cluster" in src


def test_schema_accepts_the_key():
    import schema
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert props["logic_cluster_rects_um"]["items"]["required"] == ["name", "patterns", "rect_um"]


# ---- HEAD-INT-R2 11-26 (C-GPL-TD-INFLATION): opt-in OT_LOGIC_CLUSTER_POST_GPL=1 ----
# GPL timing-driven repair is triggered on the mean over the per-group Nesterov regions: 15 tiny clusters (3-20 cells, 0.4-1.5 %
# util) read overflow 0.185 while the top level sat at 0.73 (fed00: +56,515 buffers at iteration 1; ffbe77: pass 2 at mean 0.186,
# top 0.27, +14,970).  Post mode creates region + group after global_placement and snaps each member into its rect.
import shutil
import subprocess

needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

LC_MOCK = r"""
namespace eval ord { proc get_db_block {} { return blk }; proc get_db_tech {} { return tech } }
proc tech {op} { return 1000 }
namespace eval odb {
  proc dbRegion_create {b n} { puts "REGION $n"; return "reg_$n" }
  proc dbBox_create {r x0 y0 x1 y1} { puts "BOX $r $x0 $y0 $x1 $y1" }
  proc dbGroup_create {r n} { puts "GROUP $n"; return "grp_$n" }
}
proc reg_x {args} {}
# insts: name status x y w h
set ::I {{c_a PLACED 500000 500000 400 270} {c_b PLACED 12000 9000 400 270} {c_c FIRM 5000 5000 400 270} {other PLACED 0 0 400 270}}
proc blk {op args} { if {$op eq "getInsts"} { set r {}; foreach x $::I { lappend r "I:[lindex $x 0]" }; return $r } }
proc inst_of {c} { foreach x $::I { if {"I:[lindex $x 0]" eq $c} { return $x } } }
proc unknown {cmd args} {
  if {[string match I:* $cmd]} { set x [inst_of $cmd]; lassign $x n st px py w h
    switch [lindex $args 0] {
      getName { return $n } isBlock { return 0 } getPlacementStatus { return $st } getGroup { return NULL }
      getMaster { return "M:$cmd" } getBBox { return "B:$cmd" }
      setLocation { puts "SETLOC $n [lindex $args 1] [lindex $args 2]"; return }
    } }
  if {[string match M:* $cmd]} { set x [inst_of [string range $cmd 2 end]]
    switch [lindex $args 0] { getWidth { return [lindex $x 4] } getHeight { return [lindex $x 5] } } }
  if {[string match B:* $cmd]} { set x [inst_of [string range $cmd 2 end]]; lassign $x n st px py w h
    switch [lindex $args 0] { xMin { return $px } yMin { return $py } xMax { return [expr {$px+$w}] } yMax { return [expr {$py+$h}] } } }
  if {[string match grp_* $cmd]} { puts "ADD $args"; return }
  if {[string match reg_* $cmd]} { return }
  error "unknown $cmd $args"
}
set ::calls 0
proc global_placement {args} { incr ::calls; puts "GPL $args  groups_seen_by_gpl=[expr {[info exists ::seen] ? $::seen : 0}]"; return ok }
%(ENV)s
"""
LC_ROW = dict(name="cl", patterns=[r"^c_"], rect_um=[10, 8, 20, 18])


def _lc_run(env="", gpl_calls=("-density 0.5 -timing_driven",)):
    s = LC.tcl(plan([LC_ROW]), "T").replace("uplevel #0 {\n", "", 1).rsplit("}\n", 1)[0]
    body = LC_MOCK % dict(ENV=env) + s + "\n" + "".join(f"puts \"RC=[catch {{global_placement {c}}} r] $r\"\n" for c in gpl_calls)
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr + out.stdout
    return out.stdout


@needs_tcl
def test_default_creates_region_before_gpl_and_never_snaps():
    out = _lc_run()
    assert out.index("REGION cl") < out.index("GPL ") and "SETLOC" not in out and "OT_LOGIC_CLUSTER_POST" not in out, out
    assert "OT_LOGIC_CLUSTER cl cells=2 skipped_fixed=1" in out and "after_gpl" not in out, out


@needs_tcl
def test_post_mode_defers_region_until_after_gpl_and_snaps_into_rect():
    out = _lc_run('set ::env(OT_LOGIC_CLUSTER_POST_GPL) 1')
    assert out.index("GPL ") < out.index("REGION cl"), out                   # region only after the call
    assert "OT_LOGIC_CLUSTER cl cells=2 skipped_fixed=1" in out and "region=after_gpl" in out, out
    assert "BOX reg_cl 10000 8000 20000 18000" in out, out
    # c_a at (500,500) um -> clamped to the rect's far corner minus the cell; c_b already inside: untouched
    assert "SETLOC c_a 19600 17730" in out and "SETLOC c_b" not in out, out
    assert "OT_LOGIC_CLUSTER_POST cl cells=2 snapped=1" in out and out.count("ADD ") == 2, out


@needs_tcl
def test_post_mode_applies_once_skips_skip_io_and_failed_calls():
    out = _lc_run('set ::env(OT_LOGIC_CLUSTER_POST_GPL) 1', gpl_calls=("-skip_io", "-density 0.5", "-density 0.5"))
    assert out.count("REGION cl") == 1 and out.count("OT_LOGIC_CLUSTER_POST") == 1, out
    assert out.index("GPL -skip_io") < out.index("GPL -density 0.5") < out.index("REGION cl"), out
    for v in ("0", ""):
        assert "after_gpl" not in _lc_run(f'set ::env(OT_LOGIC_CLUSTER_POST_GPL) "{v}"')


def test_gen_phys_exports_the_post_gpl_flag_only_when_asked():
    from pathlib import Path
    import gen_phys as GP
    src = Path(GP.__file__).read_text()
    assert "OT_LOGIC_CLUSTER_POST_GPL" in src
