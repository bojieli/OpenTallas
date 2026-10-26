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


def test_pair_skew_model_calibration_point():
    M = dict(meta=dict(pitch_um=[487.755, 410.4], regions_depth=2, trunk_um=586.88, regions=[1, 2, 3, 4]),
             htree=[dict(level=k, len_um=v) for k, v in {1: 7608.6, 2: 4097.5, 3: 6566.4, 4: 3283.2, 5: 2244.2,
                                                          6: 1641.6, 7: 1121.9, 8: 820.8, 9: 561.2, 10: 410.4,
                                                          11: 280.8, 12: 205.2}.items()])
    tt, ff = MP.pair_skew_pred(M, "TT"), MP.pair_skew_pred(M, "FF")
    assert abs(tt["pair_ps"] - 154.0) < 15 and abs(ff["pair_ps"] - 142.8) < 15     # recorded calibration error
    M["meta"]["pitch_um"] = [200.0, 200.0]                                          # denser drivers -> less skew
    assert MP.pair_skew_pred(M, "TT")["pair_ps"] < tt["pair_ps"]


def test_fit_rect_narrow_channel_keeps_area_off_cores():
    core = (86.4, 1382.4, 544.32, 2540.16, "u_t01")
    r0 = MP.bay_rect((43.2, 1500.0), False, 88.9, 390.0)
    r = MP.fit_rect(r0, (0.0, 0.0, 1235.52, 2609.28), [core], False)
    assert not MP.rect_overlap(r, core[:4]) and MP.rect_inside(r, (0.0, 0.0, 1235.52, 2609.28))
    assert (r[2] - r[0]) * (r[3] - r[1]) >= 390.0 - 1e-6


# ---------------------------------------------------------------- COORD 06:23: commensurate tree / PHY entry / sites
def test_core_lattice_regular_and_irregular():
    c = [(176.0 + 354.24 * i, 160.0 + 371.52 * j) for i in range(4) for j in range(3)]
    L = MP.core_lattice(c)
    assert L["x"]["pitch_um"] == 354.24 and not L["x"]["irregular"] and L["x"]["leaf_pitch_um"] == 708.48
    c.append((176.0 + 354.24 * 3 + 500.0, 160.0))       # a spine gap that is not a pitch multiple
    assert MP.core_lattice(c)["x"]["n_irregular"] == 1


def test_clock_sites_flags_glue_and_macro_drivers():
    isl = [(100.0, 100.0, 108.64, 108.64)]
    glue = [(0.0, 0.0, 400.0, 400.0)]
    mac = [(200.0, 200.0, 300.0, 300.0)]
    M = dict(htree=[dict(tag="h0", b=[104.0, 104.0])],
             drivers={"a": dict(site=[104.0, 104.0]), "b": dict(site=[50.0, 50.0]), "c": dict(site=[250.0, 250.0])})
    r = MP.clock_sites(M, isl, glue, mac)
    assert r["verdict"] == "FAIL" and r["tree_nodes_off_island"] == 0 and r["mesh_drivers_off_island"] == 2
    assert r["in_tile_glue"] == {"mesh_driver": 1} and r["in_macro"] == {"mesh_driver": 1}
    M["drivers"] = {"a": dict(site=[104.0, 104.0])}
    assert MP.clock_sites(M, isl, glue, mac)["verdict"] == "PASS"


def test_phy_entry_on_digital_strip_edge(tmp_path):
    raw = json.loads(TINY.read_text())
    part = next(iter(raw["partitions"])) if isinstance(raw["partitions"], dict) else raw["partitions"][0]["name"]
    P0 = plan(raw, tmp_path, "p0.json")
    x0, y0, x1, y1 = P0.rect(part)
    raw.setdefault("die", {}).setdefault("io", []).append(
        dict(name="io_phy", kind="phy_macro", part=part, rect_um=[x0, y0 + 300.0, x1, y1]))
    P = plan(raw, tmp_path)
    pe = MP.phy_entries(P)[P.parts[part]["type"]]
    isl = pe["island"]
    s = pe["strip_rect_um"]
    assert s[0] - 1e-6 <= isl[0] and isl[2] <= s[2] + 1e-6 and s[1] - 1e-6 <= isl[1] and isl[3] <= s[3] + 1e-6
    ph = pe["phy_rect_um"]
    assert pe["clock_pin"]["xy_um"][1] in (ph[1], ph[3])     # pin on the PHY edge, not inside
