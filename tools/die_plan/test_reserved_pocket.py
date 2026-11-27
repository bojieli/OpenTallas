from types import SimpleNamespace

import gen_phys as GP
import plan_advisory
import reserved_pocket as RP


WALLS = [(2, 4, 6, 14), (8, 4, 12, 14)]
CAP = (6, 4, 8, 6)
END = (6, 12, 8, 14)
SLIT = (6, 6, 8, 14)


def test_capped_slit_and_open_channel():
    assert RP.candidates(WALLS, (20, 20)) == []
    assert RP.candidates([*WALLS, CAP], (20, 20)) == [[SLIT]]
    wide = [WALLS[0], (9, 4, 13, 14), (6, 4, 9, 6)]
    assert RP.candidates(wide, (20, 20)) == []


def test_enclosed_pocket_and_protected_tap():
    groups = RP.candidates([*WALLS, CAP, END], (20, 20))
    assert groups == [[(6, 6, 8, 12)]]
    assert RP.clear_fill(groups, [(6.1, 8, 6.2, 8.2)]) == []
    assert RP.clear_fill(groups, [(8, 8, 8.2, 8.2)]) == groups[0]


def test_generator_opt_in_and_report_only():
    rows = [dict(kind="die_clock_tree", rect_um=r, route_layers="M1-M4") for r in [*WALLS, CAP]]
    t = dict(outline_um=[20, 20], clock=dict(reserved_sites_um=rows))
    p = SimpleNamespace(types={"T": t})
    off, _, _ = GP.reserved_sites_tcl(p, "T")
    assert "OT_RESERVED_POCKET" not in off
    findings = plan_advisory.run({"partition_types": {"T": t}}, None, checks=["RESERVED-POCKET"], jobs=1)
    assert any("WARN ADV-RESERVED-POCKET T: 1" in line for line in findings)
    t["clock"]["reserved_pocket_fill"] = True
    on, _, _ = GP.reserved_sites_tcl(p, "T")
    assert "OT_RESERVED_POCKET rects=1" in on
    assert on.count("odb::dbBlockage_create") == off.count("odb::dbBlockage_create") + 1
    assert on.count("odb::dbObstruction_create") == off.count("odb::dbObstruction_create") + 4
    t["clock"]["added_taps"] = [{"name": "clk_t0", "xy": [7, 9]}]
    assert GP.reserved_sites_tcl(p, "T")[0] == off
