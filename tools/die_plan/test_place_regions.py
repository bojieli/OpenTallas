"""PLACE-REGION (lever 5): plan key partition_types.<type>.place_regions -> place_regions_data.tcl + place_regions.tcl in the kit."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import schema  # noqa: E402

ROW = {"name": "core", "inst_re": r"(^|[./])u_core\.", "util": 0.55, "near_re": r"u_core\.u_gi\.g_op"}


def test_absent_key_writes_nothing(tmp_path):
    assert gen_phys.install_place_regions(tmp_path, None) == []
    assert gen_phys.install_place_regions(tmp_path, []) == []
    assert list(tmp_path.iterdir()) == []


def test_kit_gets_data_and_hook(tmp_path):
    cfg = gen_phys.install_place_regions(tmp_path, [ROW, {"name": "rows", "inst_re": r"u_x\.(tt_pw|dh_prog)\[", "centre_um": [550, 955.5]}])
    assert len(cfg) == 1 and cfg[0].startswith("#") and "core, rows" in cfg[0]
    data = (tmp_path / "place_regions_data.tcl").read_text()
    assert "set ::ot_place_regions {" in data
    assert r"  {core {(^|[./])u_core\.} 0.55 {} {} {u_core\.u_gi\.g_op}}" in data
    assert r"  {rows {u_x\.(tt_pw|dh_prog)\[} 0.55 550 955.5 {}}" in data
    assert (tmp_path / "place_regions_cone.tcl").is_file() and (tmp_path / "place_regions_inherit.tcl").is_file()
    hook = (tmp_path / "place_regions.tcl").read_text()
    assert "dbRegion_create" in hook and "OT_PLACE_REGION" in hook
    assert hook == (Path(gen_phys.__file__).resolve().parent / "place_regions.tcl").read_text()


def test_face_flops_sources_the_hook_only_with_data():
    t = (Path(gen_phys.__file__).resolve().parent / "face_flops.tcl").read_text()
    assert "if {[file exists /work/place_regions_data.tcl] && [file exists /work/place_regions.tcl]} { source /work/place_regions_data.tcl; source /work/place_regions.tcl }" in t
    assert t.index("place_regions.tcl") < t.index("OT_GPL_GUARD begin")      # regions exist before the GPL guard / global_placement


@pytest.mark.parametrize("bad", [dict(ROW, util=0.95), dict(ROW, name="1x"), dict(ROW, inst_re="a{b"), dict(ROW, inst_re=""),
                                 dict(ROW, centre_um=[1, 2]), dict(ROW, inst_re="(")])
def test_bad_rows_are_refused(tmp_path, bad):
    with pytest.raises(Exception):
        gen_phys.install_place_regions(tmp_path, [bad])
    assert not (tmp_path / "place_regions_data.tcl").exists()


def test_repeated_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        gen_phys.install_place_regions(tmp_path, [ROW, ROW])


def test_schema_has_the_key():
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["place_regions"]
    assert p["items"]["required"] == ["name", "inst_re"] and p["items"]["additionalProperties"] is False
    assert set(p["items"]["properties"]) == {"name", "inst_re", "util", "centre_um", "near_re", "note"}


def test_region_box_is_snapped_to_the_placement_grid():
    """DPL-0033 (glue kit H, leaf t27fence): an off-grid box edge fails the region check; the hook snaps outward to site / row"""
    hook = (Path(gen_phys.__file__).resolve().parent / "place_regions.tcl").read_text()
    assert "getSite" in hook and "$pr_sw) * $pr_sw" in hook and "$pr_rh) * $pr_rh" in hook
    assert "odb::dbBox_create $pr_r $pr_bx0 $pr_by0 $pr_bx1 $pr_by1" in hook
    assert "int($pr_x0*$pr_dbu)}] [expr {int($pr_y0*$pr_dbu)}]" not in hook      # the unsnapped box is gone


import shutil  # noqa: E402
import subprocess  # noqa: E402

HERE = Path(gen_phys.__file__).resolve().parent


def _tcl(body):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    r = subprocess.run(["tclsh"], input=f"source {HERE / 'place_regions_cone.tcl'}\n" + body, text=True, capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# a synthetic netlist: flops f0..f2 (members) fed by gates g0..g3 and feeding g4; g5 hangs on a flop of another cone (stops at it)
NET = """
array set drv {f0 {g0 g1} f1 {g1 g2} f2 {g3} g0 {} g1 {} g2 {} g3 {g0} g4 {f0} g5 {x9}}
array set ld  {f0 {g4} f1 {} f2 {} g0 {f0 g3} g1 {f0 f1} g2 {f1} g3 {f2} g4 {} g5 {} x9 {g5}}
proc nin {i} { global drv; if {[info exists drv($i)]} { return $drv($i) } else { return {} } }
proc nout {i} { global ld; if {[info exists ld($i)]} { return $ld($i) } else { return {} } }
proc cand {i} { return [expr {[string index $i 0] eq "g"}] }
"""


def test_cone_adds_the_combinational_cells_around_the_members_and_stops_at_flops():
    out = _tcl(NET + 'puts [lsort [ot_pr_cone {f0 f1 f2} nin nout cand 8]]')
    assert out == "g0 g1 g2 g3 g4"                                     # g5 belongs to another cone (reached only through x9, not a candidate)


def test_coverage_under_half_is_detected_and_a_runaway_cone_is_refused():
    assert _tcl('puts [ot_pr_coverage 5926 5975]') == "0.49626996891689974" or float(_tcl('puts [ot_pr_coverage 5926 5975]')) < 0.5
    assert float(_tcl('puts [ot_pr_coverage 5 5]')) == 0.5 and float(_tcl('puts [ot_pr_coverage 9 1]')) == 0.9
    out = _tcl(NET + 'if {[catch {ot_pr_cone {f0 f1 f2} nin nout cand 1} e]} { puts "REFUSED $e" } else { puts OK }')
    assert out.startswith("REFUSED") and "not separable" in out


def test_kit_hooks_are_wired():
    t = (HERE / "place_regions.tcl").read_text()
    assert "OT_PLACE_REGION_EXTEND" in t and "ot_pr_cone" in t and "< 0.5" in t
    f = (HERE / "face_flops_release.tcl").read_text()
    assert "place_regions_inherit.tcl" in f and "place_regions_data.tcl" in f
    i = (HERE / "place_regions_inherit.tcl").read_text()
    assert "addInst" in i and "OT_PLACE_REGION_INHERIT" in i and "BUF|INV|HB|DLY" in i
