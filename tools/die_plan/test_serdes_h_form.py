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
