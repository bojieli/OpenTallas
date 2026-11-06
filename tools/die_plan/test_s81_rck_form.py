"""S81-RCK-3 11-06: serdes PHY clock-pin class form = PHY PG west notch + RX capture band (both opt-in type keys)."""
import json
from pathlib import Path

import gen_phys as G
import schema as S

HERE = Path(__file__).parent
PLAN = HERE.parents[1] / "physical/die_plan/s81/plan_h2_2249.json"
SERDES = sorted(t for t in json.loads(PLAN.read_text())["partition_types"] if t.startswith("serdes__"))


def _plan(notch=None, band=None):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    q = dict(lef="m.lef", lib="m_tt.lib", outline_um=[8.64, 2.16], orient="MX")
    c = dict(inst="u_phy", module="logical_phy", status="rework", origin_um=[17.28, 25.92], outline_um=[8.64, 8.64],
             physical_parts=[dict(q, physical_inst="u_bound.u_core.u_ptx", physical_master="txm", origin_um=[17.28, 32.4]),
                             dict(q, physical_inst="u_bound.u_core.u_prx", physical_master="rxm", origin_um=[17.28, 28.08])])
    t = raw["partition_types"]["src"]
    t["contents"] = [c]
    if notch is not None:
        t["phy_pg_west_notch_um"] = notch
    if band is not None:
        t["rck_band"] = band
    p = S.Plan(raw)
    n = next(n for n, r in p.parts.items() if r["type"] == "src")
    a, b = p.to_die(n, (4.32, 25.92)), p.to_die(n, (25.92, 34.56))      # region reaches 13 um west of the macros
    raw["die"]["pg"] = {"domains": [dict(name="phy", nets=["VDDPHY", "VSS"],
                                         rect_um=[min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])])]}
    return S.Plan(raw)


def test_key_absent_region_unchanged():
    doms = G.phy_pg_domains(_plan(), "src")
    assert doms[0][3][0] == 4.32
    assert G.rck_band_exports(_plan(), "src") == []


def test_west_notch_starts_at_macro_edge_minus_halo_on_site_grid():
    p = _plan(notch=4.32)
    assert not [e for e in S.validate(p.raw) if "phy_pg_west_notch_um" in e]
    r = G.phy_pg_domains(p, "src")[0][3]
    assert r[0] == 12.96 and r[1:] == G.phy_pg_domains(_plan(), "src")[0][3][1:]   # 17.28 - 4.32, site grid
    assert abs(r[0] / G.PHY_PG_NOTCH_SITE_UM - round(r[0] / G.PHY_PG_NOTCH_SITE_UM)) < 1e-6
    # a halo wider than the gap keeps the plan edge (never grows the region)
    assert G.phy_pg_domains(_plan(notch=40.0), "src")[0][3][0] == 4.32


def test_notch_reaches_the_kit_pdn(tmp_path):
    p = _plan(notch=4.32)
    (tmp_path / "m.lef").write_text("MACRO m\n PIN VDD\n PORT\n LAYER M5 ;\n END\n END VDD\n"
                                    " PIN VSS\n PORT\n LAYER M5 ;\n END\n END VSS\nEND m\n")
    doms = G.phy_pg_domains(p, "src")
    tcl = G.phy_pg_pdn(p, "src", doms, G.type_macros(p, "src"), root=tmp_path)
    assert "round(12.96*$dbu)" in tcl and "round(4.32*$dbu)" not in tcl


def test_rck_band_exports_region_bottom():
    p = _plan(notch=4.32, band={"inst": "u_bound.u_core.u_prx"})
    assert not [e for e in S.validate(p.raw) if "rck_band" in e]
    bot = G.phy_pg_domains(p, "src")[0][3][1]
    assert G.rck_band_exports(p, "src") == ["export OT_RCK_BAND_INST = u_bound.u_core.u_prx",
                                            f"export OT_RCK_BAND_TOP_UM = {G._um(bot)}", "export OT_RCK_BAND_ROWS = 4"]
    try:
        G.rck_band_exports(_plan(band={"inst": "u_nope"}), "src")
    except ValueError as e:
        assert "exactly one PHY PG domain" in e.args[0]
    else:
        raise AssertionError("band inst outside every PHY domain accepted")


def test_rck_band_hook_is_generic():
    s = (HERE / "rck_band.tcl").read_text()
    assert "u_prx" not in s and "$::env(OT_RCK_BAND_INST)" in s and "$::env(OT_RCK_BAND_ROWS)" in s and "RCKB" in s


def test_all_s81_serdes_types_carry_the_class_form():
    P = S.Plan(json.loads(PLAN.read_text()))
    assert len(SERDES) == 11
    for tn in SERDES:
        t = P.types[tn]
        assert t["phy_pg_west_notch_um"] == 4.32 and t["rck_band"] == {"inst": "u_bound.u_core.u_prx"}, tn
        dom = G.phy_pg_domains(P, tn)
        assert len(dom) == 1 and "u_bound.u_core.u_prx" in dom[0][4], tn
        prx = min(q["origin_um"][0] for c in t["contents"] for q in c.get("physical_parts", [])
                  if q["physical_inst"] in dom[0][4])
        assert prx - 4.32 - G.PHY_PG_NOTCH_SITE_UM < dom[0][3][0] <= prx - 4.32, tn
        assert G.rck_band_exports(P, tn)[1] == f"export OT_RCK_BAND_TOP_UM = {G._um(dom[0][3][1])}", tn
