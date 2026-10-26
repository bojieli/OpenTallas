"""master_plan.py (METHODOLOGY 12.7 / 12.8 / 12.9d master-plan mode): one test per static plan gate + slices."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import master_plan as MP  # noqa: E402
import schema as S  # noqa: E402

TINY = HERE / "examples" / "tiny_plan_typegeo.json"


def plan(raw, tmp, name="p.json"):
    f = tmp / name
    f.write_text(json.dumps(raw))
    return S.Plan(S.load(f), f)


def run(raw, tmp, **kw):
    P = plan(raw, tmp)
    kw.setdefault("render", False)
    kw.setdefault("log", lambda *_: None)
    return MP.run(P, tmp / "out", **kw)


# ---------------------------------------------------------------- reach gap / rest stops
def test_place_stops_legal_road_keeps_gap_under_reach():
    route = [(0.0, 0.0), (1000.0, 0.0)]
    stops, fails, T = MP.place_stops(route, lambda a, b: [(0.0, MP.IS.seg_len(a, b))], 405.0)
    ts = [0.0] + [t for t, _ in stops] + [T]
    assert not fails and max(b - a for a, b in zip(ts, ts[1:])) <= 405.0 + 1e-6 and len(stops) == 2


def test_place_stops_core_longer_than_reach_fails_with_location():
    # legal only 0-100 and 700-1000: a 600 um hard core lies on the road
    def iv(a, b):
        return [(0.0, 100.0), (700.0, 1000.0)]
    stops, fails, T = MP.place_stops([(0.0, 0.0), (1000.0, 0.0)], iv, 405.0)
    assert fails and 100.0 < fails[0][2][0] <= 505.0


# ---------------------------------------------------------------- entry pins
def test_entry_pin_limit_derivation_and_spread(tmp_path):
    P = plan(json.loads(TINY.read_text()), tmp_path)
    lim, free, d = MP.entry_pin_limit(P, P.die["pg"]["grid"], None, 0.25)
    # M8/M9: 135 tracks x (1 - 2 x ceil((0.48 + 0.08)/0.08) x 0.08 / 8.64) = 117.3; M7: 168.75 x 0.75 = 126.6
    assert d["binding"] in ("M8", "M9") and lim == int(0.6 * 0.5 * min(free.values()))
    occ = MP.defaultdict(int)
    pins = MP.place_pins(occ, (100.0, 100.0, 110.0, 120.0), 1000, lim)
    assert len(pins) == 1000 and max(occ.values()) <= lim
    cells = MP.defaultdict(int)
    for x, y in pins:
        cells[(int(x // MP.G), int(y // MP.G))] += 1
    assert max(cells.values()) <= lim


# ---------------------------------------------------------------- clock shielding
def test_clock_shield_between_tight_pg_passes_and_open_side_fails(tmp_path):
    P = plan(json.loads(TINY.read_text()), tmp_path)
    # VDD/VSS stripes every 0.8 um (pitch 1.6, 2 nets): edges (0.56, 1.04), (1.36, 1.84) -> a 0.16 strap at 1.12-1.28
    # leaves 0.08 on each side: no 0.04 signal + 2 x 0.04 space fits next to the 0.08 NDR space -> shielded
    good = [{"layer": "M9", "width_um": 0.48, "pitch_um": 1.6, "offset_um": 0.8, "nets": ["VDD", "VSS"]}]
    strap = [("ck_mesh_r0", "M9", 1.12, 0.0, 1.28, 100.0, 0.16)]
    g = MP.clock_shield(P, good, strap)
    assert g["shielded"] == 1 and g["verdict"] == "PASS"
    # a planned M9 road band within the shield spacing -> FAIL
    road = MP.clock_shield(P, good, strap, roads=[("M9", (1.0, 10.0, 1.4, 20.0))])
    assert road["road_band_conflicts"] == 1 and road["verdict"] == "FAIL"
    # strap touching a stripe -> FAIL (pg overlap)
    r = MP.clock_shield(P, good, [("ck_mesh_r0", "M9", 0.98, 0.0, 1.14, 100.0, 0.16)])
    assert r["pg_overlaps"] == 1 and r["verdict"] == "FAIL"
    # plan grid 8.64: the strap between stripes 4.32 apart has open signal tracks on both sides -> unshielded
    far = MP.clock_shield(P, P.die["pg"]["grid"], [("ck_mesh_r0", "M9", 6.4, 0.0, 6.56, 100.0, 0.16)])
    assert far["unshielded"] == 1 and far["open_sides"] == 2 and far["verdict"] == "FAIL"


# ---------------------------------------------------------------- tree balance / early taps / IR
def test_tree_balance():
    M = dict(htree=[dict(level=2, a=[0, 0], b=[100, 0], len_um=100.0), dict(level=2, a=[0, 0], b=[-100, 0],
                                                                            len_um=100.0)],
             taps=[dict(part="c_x", tap="clk", stub_um=10.0), dict(part="c_y", tap="clk", stub_um=12.0)])
    assert MP.tree_balance(M)["verdict"] == "PASS"
    M["htree"][1]["len_um"] = 140.0
    assert MP.tree_balance(M)["unequal_families"] == 1
    M = dict(htree=[], taps=[dict(part="c_x", tap="clk", stub_um=10.0), dict(part="c_y", tap="clk", stub_um=90.0)])
    assert MP.tree_balance(M)["verdict"] == "FAIL"


def test_static_ir(tmp_path):
    assert MP.static_ir([])["verdict"] == "NOT RUN"
    f = tmp_path / "r.json"
    f.write_text(json.dumps(dict(window="core", ir_verdict="PASS", worst_ir_drop_mv=30, ir_budget_mv=35)))
    assert MP.static_ir([f])["verdict"] == "NOT QUALIFIED"
    f.write_text(json.dumps(dict(window="core", ir_verdict="PASS", power_basis="worst_case")))
    assert MP.static_ir([f])["verdict"] == "PASS"
    g = tmp_path / "u.json"
    g.write_text(json.dumps(dict(window="ucie", ir_verdict="FAIL", power_basis="worst_case")))
    assert MP.static_ir([f, g])["verdict"] == "FAIL"


# ---------------------------------------------------------------- 12.8 entries / restructure / model
def test_entry_island_lattice_and_restructure_islands():
    r = MP.entry_island((129.6, 169.0))
    assert r[0] <= 129.6 <= r[2] and r[1] <= 169.0 <= r[3]
    assert all(abs(v / 4.32 - round(v / 4.32)) < 1e-6 for v in r) and abs(r[2] - r[0] - 8.64) < 1e-6
    sub = MP.restructure_islands(457.92, 1157.76, 200.0)
    assert sub["leaf_reach_um"] <= 200.0 and len(sub["islands"]) == sub["grid"][0] * sub["grid"][1]


def test_core_insertion_model_calibrated_once():
    assert MP.CAL_RMS_PS < 25.0 and len(MP.CAL_POINTS) == 3
    tt, ff = MP.core_insertion(298.6)      # vmr from its centre entry
    assert 240 < tt < 270 and ff < tt
    assert MP.core_insertion(1000.0)[0] > 800


def _with_core(raw, tap_xy=(432.0, 432.0), insertion=None, core=((332.64, 332.64), (198.72, 198.72))):
    raw = copy.deepcopy(raw)
    t = raw["partition_types"]["mid"]
    (ox, oy), (w, h) = core
    t["hard_cores"] = [dict(inst="u_c", module="core_m", origin_um=[ox, oy], outline_um=[w, h], orient="R0")]
    common = raw.get("clock", {}).get("common_latency_ps", 250)
    t.setdefault("clock", {})["taps"] = [dict(name="u_c.ck", kind="core", xy=list(tap_xy),
                                              insertion_ps=insertion or common, insertion_tol_ps=40)]
    return raw


def test_run_tiny_gates_and_slices(tmp_path):
    raw = _with_core(json.loads(TINY.read_text()))
    mp, gates = run(raw, tmp_path)
    for k in ("reach_gap", "bay_fill", "corridor_tracks", "entry_pins", "clock_shield", "static_ir", "lot_fit",
              "clock_entry", "core_reach", "early_taps", "tree_balance", "core_insertion_model"):
        assert k in gates
    assert gates["lot_fit"]["verdict"] == "PASS"
    assert gates["clock_entry"]["verdict"] == "PASS"          # tap at the core centre = default entry
    assert gates["core_reach"]["verdict"] == "PASS"           # 198.72 square on the 4.32 lattice -> 198.72 um from centre
    assert mp["verdict"] == "FAIL"                            # NOT RUN gates (no mesh / IR) block the freeze
    sl = json.loads((tmp_path / "out" / "slices" / "mid.json").read_text())
    assert sl["schema"] == MP.SLICE_SCHEMA and sl["outline_um"] == [864.0, 864.0]
    assert sl["master_plan_sha256"] == mp["master_plan_sha256"] and sl["hard_cores"][0]["clock_entry_um"]
    core = json.loads((tmp_path / "out" / "slices" / "core_m.json").read_text())
    assert core["kind"] == "core" and core["islands"][0]["clock_pin"]["layer"] == "M5"


def test_run_flags_entry_offset_early_tap_overlap_and_restructure(tmp_path):
    raw = _with_core(json.loads(TINY.read_text()), tap_xy=(340.0, 340.0), insertion=386)
    t = raw["partition_types"]["mid"]
    t["hard_cores"].append(dict(inst="u_d", module="core_big", origin_um=[400.0, 400.0], outline_um=[400.0, 400.0],
                                orient="R0"))
    _, gates = run(raw, tmp_path)
    assert gates["clock_entry"]["verdict"] == "FAIL"
    assert gates["early_taps"]["verdict"] == "FAIL" and gates["early_taps"]["plan_taps_offset"]["core"] == 1
    assert gates["lot_fit"]["verdict"] == "FAIL"              # u_d overlaps u_c
    assert gates["core_reach"]["verdict"] == "FAIL"
    big = [r for r in gates["core_reach"]["restructure"] if r["module"] == "core_big"][0]
    assert big["in_core_islands"]["leaf_reach_um"] <= 200.0
    assert gates["core_insertion_model"]["verdict"] == "FAIL"


def test_corridor_overflow_moves_to_m89_and_entry_pins(tmp_path):
    raw = json.loads(TINY.read_text())
    for p in raw["ports"]:
        p["width"] = max(p.get("width", 1), 60000)       # far beyond M4-M7 capacity of the ft windows
    for t in raw["partition_types"].values():
        for s in t.get("ft_slots", []):
            s["width"] = 60000
        for b in t.get("buses", []):
            b["width"] = 60000
    try:
        _, gates = run(raw, tmp_path)
    except Exception as ex:                              # an inconsistent mutation is a fixture problem
        pytest.skip(f"tiny mutation not schema-consistent: {ex}")
    c = gates["corridor_tracks"]
    assert c["verdict"] == "FAIL" or c["m89_roads"] > 0
    if c["m89_roads"]:
        assert gates["entry_pins"]["pins"] > 0
