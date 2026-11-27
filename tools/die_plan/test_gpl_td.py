"""C-GPL-TD-INFLATION (CLASS-OWNERS-B 11-26): plan flag gpl_td, default OFF; absent = byte-identical kit text.
Plan side (spec / config lines / kit install / logic_cluster seating text) and the Tcl side (gpl_td.tcl in tclsh with OpenDB mocked)."""
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace as N

import pytest

import gpl_td as GT
import logic_cluster as LC

HERE = Path(__file__).resolve().parent
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def test_absent_flag_is_empty_everywhere(tmp_path):
    assert GT.spec({}) == {} and GT.spec(None) == {} and GT.cfg_lines({}, "T") == [] and GT.firm_small({}, "T") == 0
    for name in ("face_flops.tcl", "face_flops_release.tcl", "config.mk"):
        (tmp_path / name).write_text("orig\n")
    assert GT.apply(tmp_path, {}, "T") is False
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config.mk", "face_flops.tcl", "face_flops_release.tcl"]
    assert all((tmp_path / n).read_text() == "orig\n" for n in ("face_flops.tcl", "config.mk"))


def test_logic_cluster_text_unchanged_without_flag():
    t = dict(outline_um=[100, 50], logic_cluster_rects_um=[dict(name="a", patterns=["x"], rect_um=[1, 1, 9, 9])])
    P = N(types={"T": t})
    assert LC.tcl(P, "T") == LC.tcl(P, "T", firm_small=0)
    assert "FIRM-SEAT" not in LC.tcl(P, "T") and "set grp [odb::dbGroup_create $reg $name]" in LC.tcl(P, "T")


def test_settle_default_is_the_rflow_keep_overflow():
    import gen_phys
    assert GT.SETTLE_DEFAULT == gen_phys.RFLOW["gpl_keep_overflow"]


@pytest.mark.parametrize("d,want", [
    ({"top_overflow_trigger": 1, "firm_small_clusters": 1, "cell_growth_gate": 1}, {"top": 0.25, "firm_small": 20, "growth": 1}),
    ({"top_overflow_trigger": 0.3}, {"top": 0.3, "firm_small": 0, "growth": 0}),
    ({"firm_small_clusters": 8, "cell_growth_gate": "fail"}, {"top": 0, "firm_small": 8, "growth": 2}),
    ({"cell_growth_gate": "report"}, {"top": 0, "firm_small": 0, "growth": 1}),
])
def test_spec(d, want):
    assert GT.spec({"gpl_td": d}) == want


@pytest.mark.parametrize("d", [{}, {"nope": 1}, {"top_overflow_trigger": 1.5}, {"top_overflow_trigger": -0.1},
                               {"firm_small_clusters": 2}, {"firm_small_clusters": 21}, {"cell_growth_gate": 3},
                               {"cell_growth_gate": "x"}])
def test_bad_spec_fails_closed(d):
    with pytest.raises(ValueError, match="gpl_td"):
        GT.spec({"gpl_td": d})


def test_apply_installs_hook_config_and_release(tmp_path):
    for name in ("face_flops.tcl", "face_flops_release.tcl", "config.mk"):
        (tmp_path / name).write_text("orig\n")
    raw = {"gpl_td": {"top_overflow_trigger": 1, "cell_growth_gate": 2}}
    assert GT.apply(tmp_path, raw, "T") is True
    assert (tmp_path / "gpl_td.tcl").read_text() == (HERE / "gpl_td.tcl").read_text()
    assert (tmp_path / "face_flops.tcl").read_text() == "orig\n\nsource /work/gpl_td.tcl\n"
    assert "ot_gpl_td_growth_gate post_resize" in (tmp_path / "face_flops_release.tcl").read_text()
    mk = (tmp_path / "config.mk").read_text()
    assert "export OT_GPL_TD_TOP = 0.25" in mk and "export OT_GPL_TD_GROWTH = 2" in mk and "OT_GPL_TD_GROWTH_REL = 0.35" in mk


def test_firm_small_only_installs_no_tcl(tmp_path):
    (tmp_path / "config.mk").write_text("orig\n")
    assert GT.apply(tmp_path, {"gpl_td": {"firm_small_clusters": 1}}, "T") is False
    assert not (tmp_path / "gpl_td.tcl").exists()


def test_gen_phys_wiring():
    src = (HERE / "gen_phys.py").read_text()
    assert "firm_small=gpl_td.firm_small(P.raw, tn)" in src and "gpl_td.apply(kd, P.raw, tn)" in src


def test_firm_small_text_seats_small_clusters_and_keeps_regions_for_big_ones():
    t = dict(outline_um=[100, 50], logic_cluster_rects_um=[dict(name="a", patterns=["x"], rect_um=[1, 1, 9, 9])])
    s = LC.tcl(N(types={"T": t}), "T", firm_small=20)
    assert "set lc_small 20" in s and "FIRM-SEAT" in s and "proc ot_lc_seat" in s
    assert "setPlacementStatus FIRM" in s and "ot_face_flops.txt" in s and "CLUSTER" in s
    assert "odb::dbRegion_create $lc_b $name" in s     # clusters above the bound stay regions


# ---------------------------------------------------------------------------------------------------------------- Tcl
GP = (HERE / "gpl_td.tcl").read_text()
MOCK = r"""
set ::cells {%(CELLS)s}
namespace eval ord { proc get_db_block {} { return blk } }
proc blk {op args} { if {$op eq "getInsts"} { set r {}; set k 0; foreach c $::cells { lappend r "i$k"; incr k }; return $r } }
proc unknown {cmd args} {
  if {[regexp {^i(\d+)$} $cmd -> k]} { switch [lindex $args 0] { getMaster { return "m$k" } } }
  if {[regexp {^m(\d+)$} $cmd -> k]} { switch [lindex $args 0] { isBlock { return [string match BLK* [lindex $::cells $k]] }
                                                              getName { return [lindex $::cells $k] } } }
  error "unknown $cmd"
}
set ::calls {}
proc global_placement {args} { lappend ::calls $args; return done }
set ::env(RESULTS_DIR) %(RES)s
%(ENV)s
"""


def _tcl(tmp_path, body, cells="NAND2 NAND2 INV TAPCELL TAPCELL BLK1", env=""):
    pre = MOCK % dict(CELLS=cells, RES=str(tmp_path), ENV=env)
    out = subprocess.run(["tclsh"], input=pre + GP + body, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


CALL = "-density 0.5 -pad_left 0 -pad_right 0 -timing_driven -keep_resize_below_overflow 0.25 -force_center_initial_place -min_phi_coef 0.95"


@needs_tcl
def test_top_trigger_keeps_one_call_and_restricts_the_reweight_thresholds(tmp_path):
    out = _tcl(tmp_path, f"global_placement {CALL}\nforeach c $::calls {{ puts \"C: $c\" }}\n", env="set ::env(OT_GPL_TD_TOP) 0.25")
    c = re.findall(r"^C: (.*)$", out, re.M)
    assert len(c) == 1, out                                          # one call: no restart (a two-phase form was measured and rejected)
    assert c[0] == CALL + " -timing_driven_net_reweight_overflow 25", c
    assert "OT_GPL_TD_TOP timing-driven repair only at overflow <= 0.25" in out


@needs_tcl
def test_top_trigger_keeps_only_thresholds_at_or_below_settle(tmp_path):
    call = CALL + " -timing_driven_net_reweight_overflow {79 64 49 29 21 15}"
    out = _tcl(tmp_path, f"global_placement {call}\nforeach c $::calls {{ puts \"C: $c\" }}\n", env="set ::env(OT_GPL_TD_TOP) 0.25")
    c = re.findall(r"^C: (.*)$", out, re.M)
    assert c == [CALL + " -timing_driven_net_reweight_overflow {21 15}"], c


@needs_tcl
def test_settle_is_capped_by_the_keep_threshold(tmp_path):
    call = CALL.replace("0.25", "0.2")
    out = _tcl(tmp_path, f"global_placement {call}\nforeach c $::calls {{ puts \"C: $c\" }}\n", env="set ::env(OT_GPL_TD_TOP) 0.3")
    c = re.findall(r"^C: (.*)$", out, re.M)
    assert c == [call + " -timing_driven_net_reweight_overflow 20"], c


@needs_tcl
def test_calls_without_timing_driven_or_flag_are_untouched(tmp_path):
    plain = "-density 0.5 -pad_left 0"
    out = _tcl(tmp_path, f"global_placement {plain}\nglobal_placement {CALL}\nforeach c $::calls {{ puts \"C: $c\" }}\n", env="set ::env(OT_GPL_TD_TOP) 0.25")
    assert re.findall(r"^C: (.*)$", out, re.M)[0] == plain
    out = _tcl(tmp_path, f"global_placement {CALL}\nforeach c $::calls {{ puts \"C: $c\" }}\n")      # flag env unset
    assert re.findall(r"^C: (.*)$", out, re.M) == [CALL]


@needs_tcl
def test_exit_overflow_at_or_above_settle_moves_the_pass_five_points_above_the_exit(tmp_path):
    call = CALL + " -overflow 0.3"
    out = _tcl(tmp_path, f"global_placement {call}\nforeach c $::calls {{ puts \"C: $c\" }}\n", env="set ::env(OT_GPL_TD_TOP) 0.25")
    assert re.findall(r"^C: (.*)$", out, re.M) == [call + " -timing_driven_net_reweight_overflow 35"]


@needs_tcl
def test_wraps_an_existing_guard_alias(tmp_path):
    body = "proc guard {args} { lappend ::guarded $args; return [uplevel 1 [list ::ot_native {*}$args]] }\n"
    pre = MOCK % dict(CELLS="A B", RES=str(tmp_path), ENV="set ::env(OT_GPL_TD_TOP) 0.25") + "rename global_placement ot_native\nset ::guarded {}\n" + body \
        + "interp alias {} ::global_placement {} ::guard\n" + GP + f"global_placement {CALL}\nputs \"G=[llength $::guarded] N=[llength $::calls]\"\n"
    out = subprocess.run(["tclsh"], input=pre, capture_output=True, text=True)
    assert out.returncode == 0 and "G=1 N=1" in out.stdout, out.stdout + out.stderr


@needs_tcl
@pytest.mark.parametrize("mode,verdict", [(1, "FLAG"), (2, "FAIL")])
def test_growth_gate_flags_or_fails(tmp_path, mode, verdict):
    env = f"set ::env(OT_GPL_TD_GROWTH) {mode}; set ::env(OT_GPL_TD_GROWTH_REL) 0.35"
    body = ("ot_gpl_td_growth_record\nset ::cells [concat $::cells [lrepeat 4 BUFx2]]\n"
            "set rc [catch {ot_gpl_td_growth_gate post_resize} m]\nputs \"RC=$rc\"\n")
    out = _tcl(tmp_path, body, env=env)       # 3 non-tap standard cells pre, 7 after: growth 1.333 > bound int(3*1.35) = 4
    assert f"stage=post_resize pre=3 now=7 bound=4 growth=1.333: {verdict}" in out, out
    assert f"RC={1 if mode == 2 else 0}" in out


@needs_tcl
def test_growth_gate_ok_and_cap_derived_bound(tmp_path):
    env = "set ::env(OT_GPL_TD_GROWTH) 2; set ::env(OT_CELL_CENSUS_CAP) 3"
    out = _tcl(tmp_path, "ot_gpl_td_growth_record\not_gpl_td_growth_gate post_gpl\n", env=env)
    assert "pre=3 now=3 bound=3 growth=0.000: OK" in out, out          # bound = min(cap, pre x 1.35)


@needs_tcl
def test_growth_gate_off_is_silent(tmp_path):
    out = _tcl(tmp_path, "ot_gpl_td_growth_record\not_gpl_td_growth_gate post_gpl\nglobal_placement -density 0.5\n")
    assert "OT_GPL_TD_GROWTH" not in out and not (tmp_path / "ot_gpl_td_pre.txt").exists()


@needs_tcl
def test_growth_gate_wraps_gpl_and_reports(tmp_path):
    out = _tcl(tmp_path, "global_placement -density 0.5\n", env="set ::env(OT_GPL_TD_GROWTH) 1")
    assert "stage=pre_gpl nontap=3" in out and "stage=post_gpl pre=3 now=3" in out, out


# --- seat proc of logic_cluster.py in tclsh (mock OpenDB) -----------------------------------------------------------------
SEAT_MOCK = r"""
namespace eval ord { proc get_db_block {} { return blk }; proc get_db_tech {} { return tech } }
proc tech {op} { return 1000 }
proc core {op} { switch $op { xMin { return 0 } yMin { return 0 } } }
proc site {op} { switch $op { getWidth { return 54 } getHeight { return 270 } } }
proc row {op} { return site }
set ::cells {%(CELLS)s}
set ::flag {}
proc blk {op args} { switch $op { getRows { return row } getCoreArea { return core } getInsts { set r {}; set k 0
  foreach c $::cells { lappend r "i$k"; incr k }; return $r } } }
proc unknown {cmd args} {
  if {[regexp {^i(\d+)$} $cmd -> k]} { lassign [lindex $::cells $k] nm w st
    switch [lindex $args 0] { getName { return $nm } getMaster { return "m$k" } isBlock { return 0 } getGroup { return NULL }
      getPlacementStatus { return [expr {[info exists ::pst($k)] ? $::pst($k) : $st}] }
      setPlacementStatus { set ::pst($k) [lindex $args 1] } setLocation { set ::loc($k) [lrange $args 1 2] } } ; return }
  if {[regexp {^m(\d+)$} $cmd -> k]} { lassign [lindex $::cells $k] nm w st
    switch [lindex $args 0] { getWidth { return $w } getHeight { return 270 } } ; return }
  error "unknown $cmd"
}
set ::env(RESULTS_DIR) %(RES)s
"""


def _seat(tmp_path, cells, rect, small=20):
    t = dict(outline_um=[1000, 1000], logic_cluster_rects_um=[dict(name="cl", patterns=["^u_c"], rect_um=rect)])
    s = LC.tcl(N(types={"T": t}), "T", firm_small=small)
    cs = " ".join("{" + " ".join(map(str, c)) + "}" for c in cells)
    (tmp_path / "ot_face_flops.txt").write_text("pin\tFACE\n")
    body = SEAT_MOCK % dict(CELLS=cs, RES=str(tmp_path)) + s + '\nforeach k [lsort -integer [array names ::loc]] { puts "LOC $k $::loc($k) $::pst($k)" }\n'
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True)
    assert out.returncode == 0 and not out.stderr, out.stderr      # tclsh reading stdin reports a script error on stderr and exits 0
    return out.stdout


@needs_tcl
def test_small_cluster_is_seated_firm_on_the_site_grid_and_listed_for_release(tmp_path):
    cells = [(f"u_c{k}", 108, "PLACED") for k in range(5)] + [("other", 108, "PLACED")]
    out = _seat(tmp_path, cells, [10, 10, 20, 20])
    locs = re.findall(r"LOC (\d+) (\d+) (\d+) FIRM", out)
    assert [int(a) for a, _, _ in locs] == [0, 1, 2, 3, 4], out
    assert all(int(x) % 54 == 0 and int(y) % 270 == 0 for _, x, y in locs)
    assert all(10000 <= int(x) <= 20000 and 10000 <= int(y) <= 20000 for _, x, y in locs)
    assert "FIRM-SEAT cells=5" in out
    assert (tmp_path / "ot_face_flops.txt").read_text().splitlines() == ["pin\tFACE"] + [f"u_c{k}\tCLUSTER" for k in range(5)]


@needs_tcl
def test_seat_wraps_rows_inside_the_rect(tmp_path):
    cells = [(f"u_c{k}", 1080, "PLACED") for k in range(6)]               # 6 x 20 sites = 6480 dbu in a 5000 dbu wide rect: two rows
    out = _seat(tmp_path, cells, [10, 10, 15, 12])
    ys = sorted({int(y) for _, y in re.findall(r"LOC \d+ (\d+) (\d+) FIRM", out)})
    assert len(ys) == 2 and ys[1] - ys[0] == 270, out


@needs_tcl
def test_area_check_still_applies_to_seated_clusters(tmp_path):
    cells = [(f"u_c{k}", 1080, "PLACED") for k in range(6)]
    t = dict(outline_um=[1000, 1000], logic_cluster_rects_um=[dict(name="cl", patterns=["^u_c"], rect_um=[10, 10, 15, 10.2])])
    s = LC.tcl(N(types={"T": t}), "T", firm_small=20)
    body = SEAT_MOCK % dict(CELLS=" ".join("{" + " ".join(map(str, c)) + "}" for c in cells), RES=str(tmp_path)) + s
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True)
    assert "exceeds 0.7 of rect" in out.stderr and "FIRM-SEAT" not in out.stdout


@needs_tcl
def test_cluster_above_the_bound_is_not_seated(tmp_path):
    cells = [(f"u_c{k}", 108, "PLACED") for k in range(5)]
    t = dict(outline_um=[1000, 1000], logic_cluster_rects_um=[dict(name="cl", patterns=["^u_c"], rect_um=[10, 10, 20, 20])])
    s = LC.tcl(N(types={"T": t}), "T", firm_small=4)
    body = (SEAT_MOCK % dict(CELLS=" ".join("{" + " ".join(map(str, c)) + "}" for c in cells), RES=str(tmp_path))
            + "namespace eval odb { proc dbRegion_create {b n} { puts REGION; return reg }; proc dbBox_create {args} {}; proc dbGroup_create {r n} { return grp } }\n"
            + "proc reg {args} {}\nproc grp {op i} { puts \"ADD $i\" }\n" + s)
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True)
    assert out.returncode == 0 and "REGION" in out.stdout and out.stdout.count("ADD") == 5 and "FIRM-SEAT" not in out.stdout, out.stdout + out.stderr


# ---- C-TDREPAIR-REGION-MEAN 11-27 (HEAD-EAST-R4): top_overflow_trigger alone keys the trigger on the top-level overflow ----
# OpenROAD tests the timing-driven trigger on the MEAN overflow of every Nesterov region; the threshold wrapper keeps reading that mean
# while clusters above firm_small_clusters (r6 East: 24 / 80 / 291 cells) stay GPL regions, so the flag implies post-GPL regions.
@pytest.mark.parametrize("d,want", [
    (None, False), ({"top_overflow_trigger": 0, "cell_growth_gate": 1}, False), ({"firm_small_clusters": 1}, False),
    ({"top_overflow_trigger": 1}, True), ({"top_overflow_trigger": 0.3, "firm_small_clusters": 1}, True),
])
def test_post_gpl_regions_follows_top_overflow_trigger(d, want):
    raw = {} if d is None else {"gpl_td": d}
    assert GT.post_gpl_regions(raw, "T") is want


def test_gen_phys_exports_post_gpl_regions_from_the_plan_flag():
    import gen_phys as GP
    src = Path(GP.__file__).read_text()
    line = next(ln for ln in src.splitlines() if '"export OT_LOGIC_CLUSTER_POST_GPL = 1"' in ln)
    assert '_gpl_td_mod.post_gpl_regions(P.raw, tn)' in line and 'os.environ.get("OT_LOGIC_CLUSTER_POST_GPL", "") == "1"' in line
    assert 't.get("logic_cluster_rects_um")' in line          # still only for a type that has clusters
    k = src.index('"export OT_LOGIC_CLUSTER_POST_GPL = 1"')
    assert src.rfind("import gpl_td as _gpl_td_mod", 0, k) > src.rfind("\ndef ", 0, k)   # imported inside the same function, before use
