"""SERDES-H-FORM (S81-SERDES-GEN 11-17): the H17 lineage knobs the generator now emits for a PHY-region RCK4 serdes kit.

Keyed on a PHY supply region (phy_pg.json) + the RCK4 source profile, never on a type name.
"""
import json
import tempfile
from pathlib import Path

import gen_phys as G

HERE = Path(__file__).resolve().parent
BOOT = {"OT_S81_SERDES_BOOT_RELEASE3", "OT_S81_RCK_RELAY4"}


def _kit(phy=True):
    d = tempfile.mkdtemp()
    (Path(d) / "phy_pg.json").write_text(json.dumps([{"name": "phy_lk_EN2"}] if phy else []))
    return d


def test_phy_region_detection():
    assert G.serdes_phy_region(_kit(True))
    assert not G.serdes_phy_region(_kit(False))
    assert not G.serdes_phy_region(tempfile.mkdtemp())


def test_h_form_lines_match_h17_knobs():
    kd = _kit()
    out = G.serdes_h_lines([], kd, BOOT, {}, "post_global_boot3.tcl")
    assert "export PLACE_DENSITY = 0.3" in out                 # H17: 0.30 (0.5 clumped the XOR plates: DRT-0255)
    assert "export OT_CLK_LEAF_SLEW_PS = 165" in out
    assert "export PRE_RESIZE_TCL = /work/h4_meta_reflow.tcl" in out
    assert "export OT_SERDES_BOOT_RELEASE_LOCAL = 1" in out
    assert "export OT_SERDES_BOOT_PATH_LOCAL = 1" in out
    assert (Path(kd) / "h4_meta_reflow.tcl").read_bytes() == (HERE / "h4_meta_reflow.tcl").read_bytes()


def test_own_pre_resize_is_kept_and_boot_release_needs_its_define():
    out = G.serdes_h_lines(["export PRE_RESIZE_TCL = /work/x.tcl"], _kit(), {"OT_S81_RCK_RELAY4"}, {}, "rck_transport_mid.tcl")
    assert not any(c.startswith("export PRE_RESIZE_TCL") for c in out)
    assert "export OT_SERDES_BOOT_RELEASE_LOCAL = 1" not in out


def test_boot_release_post_gpl_chain():
    kd = _kit()
    assert G.serdes_h_post_gpl(kd, BOOT, "rck_transport_mid.tcl") == "post_global_boot3.tcl"
    body = (Path(kd) / "post_global_boot3.tcl").read_text().splitlines()
    assert body == ["source /work/rck_transport_mid.tcl", "source /work/serdes_boot_release_local.tcl"]   # H17 post_global_boot3.tcl
    assert G.serdes_h_post_gpl(_kit(), {"OT_S81_RCK_RELAY4"}, "rck_transport_mid.tcl") == "rck_transport_mid.tcl"


def test_pre_drt_chain_equals_h17_serdes_pre_drt():
    kd = _kit()
    out = G.serdes_pre_drt_lines([], kd)
    assert out[-1] == "export PRE_DETAIL_ROUTE_TCL = /work/serdes_pre_drt.tcl"
    chain = [l for l in (Path(kd) / "serdes_pre_drt.tcl").read_text().splitlines() if l.startswith("source")]
    assert chain == ["source /work/pad_in_direct.tcl", "source /work/pg_pin_notch.tcl", "source /work/pg_row_guides.tcl"]
    for f in ("pad_in_direct.tcl", "pg_pin_notch.tcl", "pg_row_guides.tcl"):
        assert (Path(kd) / f).exists()
    assert G.serdes_pre_drt_lines(["override export PRE_DETAIL_ROUTE_TCL = /work/own.tcl"], _kit()) == []


def test_generator_family_wiring_has_no_type_name():
    src = (HERE / "gen_phys.py").read_text()
    body = src[src.index("def serdes_phy_region"):src.index("def txl_mid_exports")]
    assert "serdes__t" not in body and "t13" not in body
    assert 'serdes_h = rck4 and serdes_phy_region(kd)' in src


# ---- part 2: generic stage hook, cohorts, corridor ------------------------------------------------------------------------------
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(HERE))
TCLSH = shutil.which("tclsh")


def test_empty_stage_hook_is_a_noop():
    kd = tempfile.mkdtemp()
    cfg = ["export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl"]
    assert G.stage_hook_lines(cfg, kd, "POST_DETAIL_PLACE_TCL", [], "c.tcl") == []
    assert cfg == ["export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl"] and not list(Path(kd).iterdir())
    assert G.post_dpl_hook_lines(cfg, kd, env={}) == [] and G.post_dpl_hook_lines(cfg, kd, env={"OT_POST_DPL_SCRIPTS": " , "}) == []


def test_stage_hook_chains_existing_script_first_and_replaces_its_line():
    kd = tempfile.mkdtemp()
    cfg = ["export A = 1", "export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl"]
    out = G.stage_hook_lines(cfg, kd, "PRE_DETAIL_PLACE_TCL", ["serdes_corridor.tcl"], "chain.tcl")
    assert out == ["export PRE_DETAIL_PLACE_TCL = /work/chain.tcl"] and cfg == ["export A = 1"]
    assert [l for l in (Path(kd) / "chain.tcl").read_text().splitlines() if l.startswith("source")] == [
        "source /work/face_flops_release.tcl", "source /work/serdes_corridor.tcl"]
    post = G.post_dpl_hook_lines([], kd, env={"OT_POST_DPL_SCRIPTS": "a.tcl, b.tcl"})
    assert post == ["export POST_DETAIL_PLACE_TCL = /work/post_dpl_chain.tcl"]


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_stage_hook_chain_runs_each_script_in_order():
    kd = tempfile.mkdtemp()
    G.post_dpl_hook_lines([], kd, env={"OT_POST_DPL_SCRIPTS": "a.tcl,b.tcl"})
    script = f"""set ::log {{}}
rename source real_source
proc source {{f}} {{lappend ::log $f}}
real_source {Path(kd) / "post_dpl_chain.tcl"}
puts $::log
"""
    out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.strip()
    assert out == "/work/a.tcl /work/b.tcl"


def test_corridor_is_opt_in_and_chained_on_pre_dpl():
    kd = _kit()
    cfg = ["export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl"]
    off = G.serdes_h_lines(cfg, kd, BOOT, {}, "post_global_boot3.tcl")
    assert not any("PRE_DETAIL_PLACE" in c for c in off) and not (Path(kd) / "serdes_corridor.tcl").exists()
    kd2 = _kit()
    on = G.serdes_h_lines(cfg, kd2, BOOT, {"OT_SERDES_CORRIDOR": "1"}, "post_global_boot3.tcl")
    assert "export PRE_DETAIL_PLACE_TCL = /work/serdes_pre_dpl_chain.tcl" in on
    for f in G.SERDES_CORRIDOR_FILES:
        assert (Path(kd2) / f).exists()


def test_cohort_hook_inserts_before_clock_taps_once():
    kd = _kit()
    (Path(kd) / "pre_cts.tcl").write_text("a\nsource /work/clock_taps.tcl\nb\n")
    assert G.serdes_cohort_hook(kd, {})
    assert (Path(kd) / "pre_cts.tcl").read_text() == "a\nsource /work/serdes_cohorts.tcl\nsource /work/clock_taps.tcl\nb\n"
    for f in G.SERDES_COHORT_FILES:
        assert (Path(kd) / f).exists()
    kd2 = _kit()
    (Path(kd2) / "pre_cts.tcl").write_text("a\nsource /work/clock_taps.tcl\n")
    assert not G.serdes_cohort_hook(kd2, {"OT_SERDES_COHORTS": "0"})
    kd3 = _kit()
    assert not G.serdes_cohort_hook(kd3, {})                          # no pre_cts.tcl / no clock_taps step: nothing written


def test_cohort_env_maps_groups_like_the_h17_stager():
    import serdes_cohorts_env as E
    model = {"hop_budget_um": 405.0, "unfit_light_root_groups": [], "groups": [
        {"key": 0, "rrl_ids": [0, 1, 2], "bbox_span_um": 316.2, "root_candidates": [{"name": "clk_t4"}, {"name": "clk_t12"}]},
        {"key": 6, "rrl_ids": [6, 7], "bbox_span_um": 100.0, "root_candidates": [{"name": "clk_t3"}]}]}
    v = E.env_values(model, "serdes_rst_x:clk_t9")
    assert v["OT_SERDES_RELAY_COHORTS"] == "0,1,2;6,7"
    assert v["OT_TAP_GROUP_FIXED"] == "serdes_rst_x:clk_t9,serdes_rst_0:clk_t4,serdes_rst_6:clk_t3" and v["OT_SERDES_RESET_COHORT"] == "1"
    bad = dict(model, groups=[dict(model["groups"][0], bbox_span_um=500.0)])
    with pytest.raises(SystemExit):
        E.env_values(bad)
    with pytest.raises(SystemExit):
        E.env_values(dict(model, unfit_light_root_groups=["x"]))


def test_boot_release_sites_are_not_type_constants():
    t = (HERE / "serdes_boot_release_local.tcl").read_text()
    assert "1656.72" not in t and "905.85" not in t and "proc ot_serdes_boot_sites" in t
    assert "OT_BOOT_RELEASE_SITES" in t
