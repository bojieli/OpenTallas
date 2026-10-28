"""clkplan unit tests: pytest opentools/clkplan/tests (light, < 5 s)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from common import plan as PL  # noqa: E402
from clkplan import model as MD, streets as ST, tracks as TK, tree as TR, ocv, run as RUN  # noqa: E402

EX = ROOT / "examples" / "toy.json"
M = MD.load()


def toy():
    return PL.load(EX)


def test_schema_validates_and_rejects():
    P = toy()
    assert PL.validate(P) == []
    bad = json.loads(json.dumps(P))
    bad["crossings"][0]["a"] = "nope"
    assert any("not a sink" in e for e in PL.validate(bad))


def test_stage_model_matches_measured_stage():
    assert abs(M.seg_ps(450.0, "TT") - 100.239) < 1e-6
    assert abs(M.seg_cell_ps(450.0, "TT") - 53.386) < 1e-6
    assert abs(M.wire_ps(900.0, "TT") - 2 * 100.239) < 1e-6


def test_toy_passes_and_is_h_tree_balanced():
    res, T, S = RUN.analyse(toy(), M)
    assert res["verdict"] == "PASS", res["checks"]
    tt = res["tree"]["corners"]["TT"]
    assert abs(tt["insertion_max_ps"] - tt["insertion_min_ps"]) < 1e-6      # symmetric H-tree: equal arrivals
    b = {r["sink"]: r for r in res["budgets"]["rows"]}
    assert b["m10/clk"]["balance_ps"] == 0.0 and b["m00/clk"]["balance_ps"] == 50.0  # deeper macro defines target


def test_blocked_leg_over_wide_macro():
    """a 1.4 mm macro under the only leg: the gap between legal repeater sites exceeds 480 um."""
    W, H = 3000.0, 1000.0
    ko = [(800.0, 0.0, 2200.0, 1000.0, "big", "hard_core")]
    S = ST.Streets(W, H, ko, raster_um=8.64)
    sinks = [dict(name="a", xy=(300.0, 500.0), insertion_ps={}, region=None, macro=None, weight=1),
             dict(name="b", xy=(2700.0, 500.0), insertion_ps={}, region=None, macro=None, weight=1)]
    T = TR.build(sinks, W, H, M, streets=S, entry=(400.0, 500.0), cfg=dict(leaf_sinks=1))
    s = TR.summary(T)
    assert s["blocked_legs"] >= 1 and s["blocked_span_um"][1] > 680 and s["unplaced"] == 1
    # in-macro islands every <= 350 um along the leg restore legality
    isl = [(x - 20.0, 480.0, x + 20.0, 520.0) for x in (1150.0, 1500.0, 1850.0)]
    S2 = ST.Streets(W, H, ko, raster_um=8.64, islands=isl)
    T2 = TR.build(sinks, W, H, M, streets=S2, entry=(400.0, 500.0), cfg=dict(leaf_sinks=1))
    s2 = TR.summary(T2)
    assert s2["blocked_legs"] == 0 and s2["unplaced"] == 0


def test_qc_class_failure_zero_off_window_slots():
    """M8 PG stripe every 4.32 um, 16w clock with PG-flank shields, +-2.5 um pin windows on 8.64-um slot rows:
    every PG gap is inside a window (QC R34 finding)."""
    pg = dict(layer="M8", dir="H", pitch_um=8.64, stripes=[dict(offset_um=0.0, width_um=0.48), dict(offset_um=4.32, width_um=0.48)])
    ndr = dict(width_um=0.64, space_um=0.5, shield="pg_flank")
    win = [dict(layer="M8", rows=dict(pitch_um=8.64, offset_um=8.37, half_um=2.5))]
    s = TK.layer_supply(pg, ndr, win)
    assert s["slots"] == 2 and s["off_window"] == 0
    assert TK.layer_supply(pg, ndr)["off_window"] == 2
    assert TK.layer_supply(pg, dict(ndr, shield="drawn"))["slots"] == 0   # drawn 16w shields do not fit a 3.84 gap


def test_crossing_margin_drops_with_unshared_delay():
    T = M.T
    a = ocv.branch(T, "TT", 300.0, 3, 250.0)
    b = ocv.branch(T, "TT", 300.0, 3, 250.0)
    _, _, _, m_small = ocv.landed_margin(T, "TT", 0.0, a, b, 1000.0, False, 416.5)
    a = ocv.branch(T, "TT", 5000.0, 50, 250.0)
    b = ocv.branch(T, "TT", 5000.0, 50, 250.0)
    _, _, _, m_big = ocv.landed_margin(T, "TT", 0.0, a, b, 15000.0, False, 416.5)
    assert m_small > 300 and m_big < 100


def test_lefdef_roundtrip(tmp_path):
    from common import lefdef
    (tmp_path / "m.lef").write_text("MACRO ram\n CLASS BLOCK ;\n SIZE 10 BY 20 ;\n PIN clk\n  DIRECTION INPUT ;\n  USE CLOCK ;\n"
                                    "  PORT\n   LAYER M4 ;\n    RECT 0 1 0.2 1.2 ;\n  END\n END clk\nEND ram\n")
    (tmp_path / "d.def").write_text("UNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( 100000 50000 ) ;\nCOMPONENTS 1 ;\n"
                                    " - u0 ram + FIXED ( 5000 6000 ) FS ;\nEND COMPONENTS\n")
    L = lefdef.read_lef_macros([tmp_path / "m.lef"])
    D = lefdef.read_def(tmp_path / "d.def")
    assert L["ram"]["w"] == 10 and D["die"] == (0, 0, 100, 50)
    x, y = lefdef.pin_point(L["ram"], D["comps"][0], "clk")
    assert abs(x - 5.1) < 1e-9 and abs(y - (6 + 20 - 1.1)) < 1e-9
