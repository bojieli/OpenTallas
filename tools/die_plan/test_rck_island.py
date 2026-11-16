"""PLAN-READERS-1 11-14 (FABLE-PLAN-B6B 6.4): type key rck_island (rck_island.py, serdes_lanes.tcl cfg key islands) and the
optional min_early_ps of pad-clock entries / early core taps (pad_clock.early_rows, rck_early_report.tcl).
python3 -m pytest -q tools/die_plan/test_rck_island.py"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP  # noqa: E402
import pad_clock as PC  # noqa: E402
import rck_island as RI  # noqa: E402
import schema  # noqa: E402
from test_pad_clock import plan as base_plan  # noqa: E402

CHN = ("u_core.u_dec.u_chn", "ot_s81_kp4_dchn")
# serdes__t2 B6c1 geometry (type frame): u_chn, the two SRAM sites, the PMA receiver, the io_pma_rck pad
T2 = dict(chn=[864.0, 95.04], dmem=[1183.68, 62.652], cmem=[1373.76, 62.652], pad=[257.952, 1090.8], top=947.16)


def iplan(rect=(40.0, 40.0, 300.0, 240.0), chn=(60.0, 60.0), **over):
    """tiny plan, type mid made serdes-like: pad clock io_pma_rck with u_chn / SRAM sink macros, one non-sink macro."""
    p = base_plan()
    t = p.types["mid"]
    pc = t["clock"]["pad_clock"]["pins"]
    pc[0]["name"] = "io_pma_rck"
    t["pads"][0]["name"] = "io_pma_rck"
    pc[0]["sink_pins"] = [dict(module=CHN[1], pin="clk"), dict(module="ot_sram_x", pin="wclk")]
    t["hard_cores"] = [dict(inst=CHN[0], module=CHN[1], origin_um=list(chn), outline_um=[50.0, 40.0], orient="R180")]
    t["contents"] = [dict(inst="u_phy", module="ot_pdie_serdes", status="rework", origin_um=[0.0, 0.0], outline_um=[800.0, 800.0],
                          physical_parts=[
        dict(physical_inst="u_prx", physical_master="ot_s81_pma_rxm", origin_um=[500.0, 500.0], outline_um=[200.0, 100.0],
             lef="x.lef", lib="x.lib", orient="MX"),
        dict(physical_inst="u_dmem", physical_master="ot_sram_x", origin_um=[130.0, 70.0], outline_um=[60.0, 40.0],
             lef="y.lef", lib="y.lib", orient="R0")])]
    t["rck_island"] = dict(rect_um=list(rect), clock="io_pma_rck", inst_re="u_core[.](u_dec|u_rxf|u_lrx)", release_before_dpl=True)
    t["rck_island"].update(over)
    return p


def test_absent_key_emits_nothing():
    p = base_plan()
    assert RI.check(p, "mid") == [] and RI.exports(p, "mid") == [] and RI.island(p, "mid") is None
    assert GP.rck_island_exports(p, "mid") == []


def test_valid_island_exports_and_cfg():
    p = iplan()
    assert RI.check(p, "mid") == []
    assert RI.exports(p, "mid") == ["export OT_RCK_ISLAND = 1", "export OT_RCK_ISLAND_RECT_UM = 40,40,300,240",
                                    "export OT_RCK_ISLAND_CLOCK = io_pma_rck", "export OT_RCK_ISLAND_RELEASE = 1"]
    cfg = RI.cfg_tcl(p, "mid")
    assert "{rck_isl 40.000 40.000 300.000 240.000 io_pma_rck {u_core[.](u_dec|u_rxf|u_lrx)}}" in cfg
    assert "release_regions_before_dpl 1" in cfg and "blocks {}" in cfg and "chains {}" in cfg
    assert RI.cfg_tcl(iplan(release_before_dpl=False), "mid").count("release_regions_before_dpl 0") == 1


@pytest.mark.parametrize("fault", ["outside", "empty", "no-chn", "overlap-prx", "bad-clock", "bad-re", "brace-re", "extra-key",
                                   "no-key", "no-sink-macro", "release-type"])
def test_bad_island_fails_closed(fault):
    kw = {}
    if fault == "outside": kw["rect"] = (40.0, 40.0, 900.0, 240.0)
    if fault == "empty": kw["rect"] = (40.0, 40.0, 40.0, 240.0)
    if fault == "no-chn": kw["chn"] = (400.0, 400.0)
    if fault == "overlap-prx": kw["rect"] = (40.0, 40.0, 700.0, 700.0)
    p = iplan(**kw)
    r = p.types["mid"]["rck_island"]
    if fault == "bad-clock": r["clock"] = "pma_nope"
    if fault == "bad-re": r["inst_re"] = "u_(core"
    if fault == "brace-re": r["inst_re"] = "u_{core}"
    if fault == "extra-key": r["note"] = "x"
    if fault == "no-key": r.pop("inst_re")
    if fault == "release-type": r["release_before_dpl"] = "yes"
    if fault == "no-sink-macro":
        p.types["mid"]["clock"]["pad_clock"]["pins"][0]["sink_pins"] = [dict(module="native_mem", pin="clk")]
    errs = RI.check(p, "mid")
    assert errs, fault
    with pytest.raises(ValueError):
        RI.exports(p, "mid")
    with pytest.raises(ValueError):
        GP.rck_island_exports(p, "mid")


def test_island_must_not_overlap_a_phy_pg_domain(monkeypatch):
    monkeypatch.setattr(GP, "phy_pg_domains", lambda P, tn: [("phy_x", "VDDPHY", "VSS", [100.0, 100.0, 200.0, 200.0], [])])
    assert any("PHY PG domain phy_x" in e for e in RI.check(iplan(), "mid"))


def test_phy_pg_domain_value_error_surfaces_in_the_check(monkeypatch):
    """S81-PHYPG-1: check() no longer swallows the ValueError of phy_pg_domains (t12 'u_dmem straddles phy_lk_WS3')"""
    def boom(P, tn):
        raise ValueError("type mid: macro u_dmem straddles PG domain phy_lk_WS3 [0, 840.4, 2437.32, 1226.88]")
    monkeypatch.setattr(GP, "phy_pg_domains", boom)
    errs = RI.check(iplan(), "mid")
    assert any("u_dmem straddles PG domain phy_lk_WS3" in e for e in errs), errs
    with pytest.raises(ValueError, match="straddles"):
        RI.island(iplan(), "mid")


def test_plan_g0_reports_an_invalid_island():
    """schema.validate runs the island check next to the pad-clock check (G0 local consistency)."""
    def errs(rect):
        p = iplan(rect=rect)
        raw = copy.deepcopy(p.raw)
        raw["partition_types"]["mid"] = copy.deepcopy(p.types["mid"])
        return schema.validate(raw)
    bad = errs((40.0, 40.0, 900.0, 240.0))
    assert any("rck_island" in e and "outside the outline" in e for e in bad), bad
    assert not any("rck_island" in e for e in errs((40.0, 40.0, 300.0, 240.0)))


def test_schema_knows_the_new_keys():
    t = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert set(t["rck_island"]["required"]) == {"rect_um", "clock", "inst_re"}
    ent = t["clock"]["properties"]["pad_clock"]["properties"]["pins"]["items"]["properties"]["entries"]["items"]
    assert "min_early_ps" in ent["properties"] and "min_early_ps" not in ent["required"]
    assert "min_early_ps" in t["clock"]["properties"]["taps"]["items"]["properties"]
    static = json.loads(HERE.joinpath("die_plan.schema.json").read_text())
    s = json.dumps(static)
    assert "rck_island" in s and s.count("min_early_ps") >= 2


# ---------------------------------------------------------------------------------------------- B6c derivation
def t2_plan(monkeypatch):
    p = base_plan()
    t = p.types["mid"]
    t["outline_um"] = [2885.76, 1226.88]
    pc = t["clock"]["pad_clock"]["pins"]
    pc[0].update(name="io_pma_rck", xy_um=T2["pad"])
    t["pads"][0]["name"] = "io_pma_rck"
    pc[0]["sink_pins"] = [dict(module=CHN[1], pin="clk"), dict(module="ot_s81_pma_rxm", pin="pma_rck"),
                          dict(module="ot_sram_1r1w2c_64x546_m1", pin="wclk"), dict(module="ot_sram_1r1w_32x546_m1", pin="clk")]
    t["hard_cores"] = [dict(inst=CHN[0], module=CHN[1], origin_um=T2["chn"], outline_um=[276.48, 138.24], orient="R180",
                               track_offset_um=[0, -2.112])]
    t["contents"] = [dict(inst="u_phy", module="ot_pdie_serdes", origin_um=[63.64, 302.4], outline_um=[2608.48, 924.48], physical_parts=[
        dict(physical_inst="u_prx", physical_master="ot_s81_pma_rxm", origin_um=[244.536, 951.48], outline_um=[2246.4, 129.6]),
        dict(physical_inst="u_dmem", physical_master="ot_sram_1r1w2c_64x546_m1", origin_um=T2["dmem"], outline_um=[178.632, 81.0]),
        dict(physical_inst="u_cmem", physical_master="ot_sram_1r1w_32x546_m1", origin_um=T2["cmem"], outline_um=[177.768, 81.0])])]
    monkeypatch.setattr(GP, "rck_band_exports", lambda P, tn: ["export OT_RCK_BAND_INST = u_prx",
                                                              f"export OT_RCK_BAND_TOP_UM = {T2['top']}", "export OT_RCK_BAND_ROWS = 4"])
    return p


def test_island_is_derived_from_the_types_own_rck_pad(monkeypatch):
    p = t2_plan(monkeypatch)
    assert RI.derive(p, "mid") == [245.0, 640.0, 1005.0, 944.0]               # kitH / kitH2 geometry of serdes__t2
    p.types["mid"]["clock"]["pad_clock"]["pins"][0]["xy_um"] = [332.704, 1090.8]  # t3 / t4 / t13 / t16 pad
    assert RI.derive(p, "mid")[0] == 319.752                                    # follows the pad, not HEAD's x 1603-2412
    p.types["mid"]["clock"]["pad_clock"]["pins"][0]["xy_um"] = [2800.0, 1090.8]
    with pytest.raises(ValueError, match="does not fit"):
        RI.derive(p, "mid")


def test_plan_patch_moves_u_chn_and_the_srams_by_the_t2_vector(monkeypatch):
    p = t2_plan(monkeypatch)
    pa = RI.plan_patch(p, "mid", rck_buf_cell="BUFx24_ASAP7_75t_R")
    assert pa["shift_um"] == (-583.2, 587.52)      # FABLE-PLAN-B6B 6.4: u_chn plan origin and both SRAM sites
    assert pa["core_moves"] == {CHN[0]: [280.8, 682.56]}      # kit location 280.8, 680.448 = origin + track_offset_um
    assert "u_prx" not in pa["sram_moves"] and pa["sram_moves"] == {"u_dmem": [600.48, 650.172], "u_cmem": [790.56, 650.172]}
    isl, chn = pa["entries"]
    assert isl["name"] == "rck_isl" and chn["name"] == "rck_chn" and chn["min_early_ps"] == 175.0
    assert [s["module"] for s in chn["sink_pins"]] == [CHN[1]] and CHN[1] not in {s["module"] for s in isl["sink_pins"]}
    for e in pa["entries"]:                                                           # trunks obey the 405-um reach
        chain = [T2["pad"]] + e["stations_um"] + [e["xy_um"]]
        assert max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(chain, chain[1:])) <= 400.0 + 1e-6, e["name"]
    assert chn["xy_um"] == [276.48, 749.568]                                          # west of u_chn, at the clk pin height
    # the patched plan validates: island holds u_chn + both SRAMs, the PMA receiver stays outside
    t = p.types["mid"]
    t["rck_island"] = pa["rck_island"]
    t["hard_cores"][0]["origin_um"] = pa["core_moves"][CHN[0]]
    for part in t["contents"][0]["physical_parts"]:
        part["origin_um"] = pa["sram_moves"].get(part["physical_inst"], part["origin_um"])
    assert RI.check(p, "mid") == []


def test_trunk_hops_are_bounded():
    assert RI.trunk([0.0, 0.0], [0.0, 100.0]) == []
    st = RI.trunk([0.0, 0.0], [300.0, 900.0])
    chain = [[0.0, 0.0]] + st + [[300.0, 900.0]]
    assert max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(chain, chain[1:])) <= 400.0


def test_domain_patch_keeps_the_phy_domain_floor(monkeypatch):
    """moving the macros into the island must not let the PHY PG domain grow over them (B6c1 smoke 947.16 -> 645.84)"""
    p = t2_plan(monkeypatch)
    inst = sorted(n for n, q in p.parts.items() if q["type"] == "mid")[0]
    p.die.setdefault("pg", {})["domains"] = [dict(name="phy_x", rect_um=list(p.rect(inst)))]
    monkeypatch.setattr(GP, "phy_pg_domains", lambda P, tn: [("phy_x", "VDDPHY", "VSS", [240.0, 947.16, 2500.0, 1226.88], ["u_prx"])])
    assert RI.domain_patch(p, "mid")["phy_x"][1] == 947.16 + p.rect(inst)[1] or RI.domain_patch(p, "mid")["phy_x"][1] > p.rect(inst)[1]
    assert set(RI.domain_patch(p, "mid")) == {"phy_x"}
    assert "die_pg_domain_rects" not in RI.plan_patch(p, "mid")      # S81-PHYPG-1: the die-rect shrink is not part of the patch


# ---------------------------------------------------------------------------------------------- min_early_ps
def eplan(min_early=175.0):
    p = iplan()
    pc = p.types["mid"]["clock"]["pad_clock"]["pins"][0]
    pc["entries"] = [dict(name="rck_chn", xy_um=[100.0, 100.0], stations_um=[[50.0, 50.0]], cell="BUFx24_ASAP7_75t_R",
                          region_um=[[90.0, 90.0, 110.0, 110.0]], sink_pins=[dict(module=CHN[1], pin="clk")], evidence="unit")]
    if min_early is not None:
        pc["entries"][0]["min_early_ps"] = min_early
    return p


def test_entry_min_early_is_optional_and_unchanged_without_it():
    p = eplan(None)
    assert PC.early_rows(p, "mid") == [] and GP.rck_early_exports(p, "mid") == []
    assert PC.entries_tcl(p, "mid") == PC.entries_tcl(eplan(175.0), "mid")      # the trunk data never carries it
    assert PC.ENTRY_OPT == {"min_early_ps"}


def test_entry_min_early_rows_and_sidecar(tmp_path):
    p = eplan()
    assert PC.early_rows(p, "mid") == [("rck_chn", CHN[0], "clk", 175.0)]
    assert GP.rck_early_exports(p, "mid") == ["export OT_RCK_EARLY = rck_early.txt"]
    PC.write_contract(p, "mid", tmp_path)
    assert (tmp_path / "rck_early.txt").read_text().splitlines()[1:] == [f"rck_chn {CHN[0]} clk 175"]
    PC.write_contract(eplan(None), "mid", tmp_path)                                 # the generator owns the file
    assert not (tmp_path / "rck_early.txt").exists()


@pytest.mark.parametrize("bad", [-1, True, float("nan"), "175", float("inf")])
def test_bad_min_early_fails_closed(bad):
    p = eplan(bad)
    with pytest.raises(ValueError, match="min_early_ps"):
        PC.entries(p, "mid")


def test_min_early_sink_module_must_resolve_to_an_instance():
    p = eplan()
    p.types["mid"]["hard_cores"] = []
    with pytest.raises(ValueError, match="names no placed hard core"):
        PC.early_rows(p, "mid")


def tap_plan(ins, min_early):
    p = base_plan()
    t = p.types["mid"]
    t["hard_cores"] = [dict(inst=CHN[0], module=CHN[1], origin_um=[60.0, 60.0], outline_um=[50.0, 40.0], orient="R0")]
    t["clock"].update(core_taps="early", taps=[dict(name=CHN[0], xy=[80.0, 80.0], kind="core", insertion_ps=ins,
                                                     min_early_ps=min_early)])
    return p


def test_early_core_tap_must_already_deliver_min_early(monkeypatch):
    base = float(base_plan().clock["insertion_ps"])
    monkeypatch.setattr(GP, "bound_core_clock_pins", lambda *a, **k: {}, raising=False)
    ok = tap_plan(base + 200.0, 175.0)
    assert PC.early_rows(ok, "mid") == [(CHN[0], CHN[0], "*", 175.0)]
    with pytest.raises(ValueError, match="delivers 100.0 ps early"):
        PC.early_rows(tap_plan(base + 100.0, 175.0), "mid")
    p = tap_plan(base + 200.0, 175.0)
    p.types["mid"]["clock"]["core_taps"] = "internal"
    with pytest.raises(ValueError, match="core_taps 'early'"):
        PC.early_rows(p, "mid")


# ---------------------------------------------------------------------------------------------- hooks
def test_island_hooks_ship_and_parse():
    d = Path(GP.__file__).resolve().parent
    body, rel = (d / "serdes_lanes.tcl").read_text(), (d / "serdes_lanes_release.tcl").read_text()
    assert "dict exists $sl_cfg islands" in body and "sl_isl_" in body and "OT_SERDES_LANES island" in body
    assert "dbRegion_destroy" in rel and "release_regions_before_dpl" in rel
    rep = (d / "rck_early_report.tcl").read_text()
    assert "OT_RCK_EARLY_SUMMARY" in rep and "report only" in rep
    assert "rck_early_report.tcl" in (d / "postcts_gate.tcl").read_text()
    tclsh = shutil.which("tclsh")
    if tclsh:
        for f in ("serdes_lanes.tcl", "serdes_lanes_release.tcl", "rck_early_report.tcl", "postcts_gate.tcl"):
            r = subprocess.run([tclsh], input=f"set f [open {{{d / f}}}]; exit [expr {{[info complete [read $f]] ? 0 : 1}}]",
                               capture_output=True, text=True)
            assert r.returncode == 0, f
