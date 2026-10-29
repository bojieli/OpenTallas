#!/usr/bin/env python3
"""CLOCK-128-R7: partition island windows (die_trial kit --island-sites) and straight pin stacks
(die_clock_mesh build --pin-stack).  python3 -m pytest tools/die_plan/test_clock128_r7.py"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as D  # noqa: E402
import die_clock_128 as C  # noqa: E402
import clock_routed as R  # noqa: E402

ND = dict(width=0.16, space=0.08)
TR = {"M8": dict(pitch_um=0.08, offset_um=0.04), "M9": dict(pitch_um=0.08, offset_um=0.04)}


# ----------------------------------------------------------------------------------------------- island windows
def _area(rs):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) - 1e-9 and max(a[1], b[1]) < min(a[3], b[3]) - 1e-9


def test_rect_minus_tiles_outline_minus_holes():
    holes = [(2.0, 2.0, 4.0, 3.0), (3.0, 2.5, 6.0, 5.0), (8.0, 0.0, 10.0, 1.0)]
    free = D.rect_minus(10.0, 8.0, holes)
    union = 2 * 1 + 3 * 2.5 - 1 * 0.5 + 2 * 1           # hole union area
    assert abs(_area(free) - (80.0 - union)) < 1e-9
    assert not any(_overlap(f, h) for f in free for h in holes)
    assert not any(_overlap(a, b) for i, a in enumerate(free) for b in free[i + 1:])
    assert D.rect_minus(5.0, 4.0, []) == [(0.0, 0.0, 5.0, 4.0)]


def test_cut_vertical_splits_pg_stripe_only_where_crossed():
    r = (4.0, 0.0, 4.3, 20.0)
    assert D._cut_vertical(r, [(3.0, 5.0, 6.0, 7.0)]) == [(4.0, 0.0, 4.3, 5.0), (4.0, 7.0, 4.3, 20.0)]
    assert D._cut_vertical(r, [(5.0, 5.0, 6.0, 7.0)]) == [r]


class _Plan:
    """two instances of one type, the second mirrored in x"""
    def __init__(self):
        self.types = {"T": dict(outline_um=[20.0, 10.0], module="t_mod")}
        self.parts = {"a": dict(type="T"), "b": dict(type="T")}
        self.layer_budget = dict(partition_signal_max="M7")

    def rect(self, n):
        return (0.0, 0.0, 20.0, 10.0) if n == "a" else (20.0, 0.0, 40.0, 10.0)

    def to_type(self, n, xy):
        return (xy[0], xy[1]) if n == "a" else (40.0 - xy[0], xy[1])


def test_island_windows_are_type_identical_and_mirrored_instances_share_one_window():
    P = _Plan()
    win, recs = D.island_windows(P, [((5.0, 5.0), "s0"), ((35.0, 5.0), "s1")])
    assert list(win) == ["T"] and len(win["T"]) == 1          # both instances land on one type-frame window
    (x0, y0, x1, y1), = win["T"]
    assert x0 < 5.0 - 1.62 / 2 and x1 > 5.0 + 1.62 / 2 and y0 < 5.0 - 0.27 and y1 > 5.0 + 0.27
    assert abs(x0 / 0.054 - round(x0 / 0.054)) < 1e-6 and abs(y0 / 0.27 - round(y0 / 0.27)) < 1e-6
    assert all(len(r["parts"]) == 1 and not r["parts"][0]["in_core"] for r in recs)


def test_island_over_hard_core_is_not_opened(monkeypatch):
    P = _Plan()
    P.types["T"]["hard_cores"] = [dict(origin_um=[3.0, 3.0], outline_um=[5.0, 5.0], module="core")]
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    win, recs = D.island_windows(P, [((5.0, 5.0), "s0")])
    assert win == {} and recs[0]["parts"][0]["in_core"] == ["core"]


def _abstract(monkeypatch, islands):
    monkeypatch.setattr(D.gen_phys, "type_pins", lambda P, tn: [])
    monkeypatch.setattr(D.gen_phys, "tap_pins", lambda P, tn: [])
    monkeypatch.setattr(D, "core_obs", lambda t: [])
    P = _Plan()
    P.types["T"].update(buses=[], ft_slots=[])
    return D.abstract_lef(P, "T", islands=islands)


def test_abstract_default_byte_identical_and_window_opens_m1_m3_and_cuts_m7(monkeypatch):
    base, st0 = _abstract(monkeypatch, None)
    assert _abstract(monkeypatch, [])[0] == base                       # opt-in: no windows = unchanged bytes
    assert "island_windows" not in st0
    win = [(3.888, 3.78, 6.426, 6.21)]                                 # over the VDD stripe at x = 4.128
    lef, st = _abstract(monkeypatch, win)
    assert st["island_windows"] == 1 and lef != base
    obs = lef.split("  OBS")[1]
    rects = [tuple(float(v) for v in ln.split()[1:5]) for ln in obs.splitlines() if ln.strip().startswith("RECT")]
    assert rects and not any(_overlap(r, win[0]) for r in rects)
    pg = lef.split("  PIN VDD")[1].split("END VDD")[0]
    m7 = [tuple(float(v) for v in ln.split()[1:5]) for ln in pg.splitlines() if ln.strip().startswith("RECT")]
    assert not any(_overlap(r, win[0]) for r in m7) and len(m7) == 3   # stripe 1 cut in two + stripe 2 whole


# -------------------------------------------------------------------------------------------------- pin stacks
def _router(pg=()):
    r = C.TrackRouter(ND, "VSS", TR, 8.64)
    r.reserve(C.pg_shapes(list(pg)))
    return r


def _tree():
    lib = "BUFx24_ASAP7_75t_R"
    cells = {"D": dict(x=10.0, y=20.0, lib=lib), "H1": dict(x=40.0, y=20.0, lib=lib),   # horizontal net D -> H1
             "V1": dict(x=40.0, y=50.0, lib=lib)}                                        # vertical net H1 -> V1
    M = dict(taps=[], meta=dict(root_um=[0.0, 0.0]))
    nets = [dict(name="nh", drv="D", loads=["H1"]), dict(name="nv", drv="H1", loads=["V1"])]
    return M, cells, nets


def test_fixed_wires_default_unchanged_by_pin_stack_option():
    M, cells, nets = _tree()
    a = C.fixed_wires(M, cells, nets, 1.62, 0.27)
    b = C.fixed_wires(M, cells, nets, 1.62, 0.27, pin_stack=False)
    assert a == b and not any(w.get("pin_stack") for w in a)


def test_pin_stack_junction_over_bar_and_m7_riser_in_column():
    M, cells, nets = _tree()
    w = {x["name"]: x for x in C.fixed_wires(M, cells, nets, 1.62, 0.27, router=_router(), pin_stack=True)}
    for x in w.values():
        assert x["pin_stack"]
        for s in x["stacks"]:
            bx = cells[s["cell"]]["x"] + C.PIN_BAR_X["BUFx24_ASAP7_75t_R"][s["pin"]]
            assert abs(s["xy"][0] - bx) < 1e-6 and abs(s["xy"][1] - (cells[s["cell"]]["y"] + 0.135)) < 1e-6
            assert s["riser_from"][0] == s["xy"][0] and 0 < s["riser_um"] <= C.STACK_RISER_MAX_UM
            pts = R.stack_down(s)
            assert {p[1] for p in pts} == {s["xy"][0]}                  # every vertex on the bar column
            assert [p[0] for p in pts] == ["M8", "M7", "M7", "M6", "M5", "M4", "M3", "M2", "M1"]
    h = w["nh"]
    ty = h["segs"][0][2]
    assert all(abs(s["riser_from"][1] - ty) < 1e-9 for s in h["stacks"])   # horizontal: junction on the M8 trunk
    assert not any(g[0] == "M9" for g in h["segs"])                         # no M9 drop at a pin


def test_pin_stack_riser_beyond_island_is_plan_error(monkeypatch):
    M, cells, nets = _tree()
    monkeypatch.setattr(C, "STACK_RISER_MAX_UM", 0.1)
    try:
        C.fixed_wires(M, cells, nets, 1.62, 0.27, router=_router(), pin_stack=True)
    except C.PlanError as e:
        assert {r["kind"] for r in e.rows} == {"no_pin_stack"}
    else:
        raise AssertionError("expected a plan error")


def test_stack_tcl_emits_min_area_pads_and_default_width_below_m8():
    M, cells, nets = _tree()
    ws = C.fixed_wires(M, cells, nets, 1.62, 0.27, router=_router(), pin_stack=True)
    rec = dict(nets=0, pin_stairs=0, port_joins=0, extra_top=[])
    L = []
    for w in ws:
        R._stack_net_tcl(L, w, {}, rec)
    assert rec["nets"] == 2 and rec["pin_stairs"] == 4
    pads = [ln for ln in L if ln.startswith("$e addRect")]
    assert len(pads) == 4 * 5                                           # M2..M6 at each of the 4 pins
    for k, ln in enumerate(L):                                           # a path opened below VIA78 has no NDR rule
        if ln.startswith("$e newPath $jv"):
            assert "[RL" not in ln or "M8" in ln
    shapes = [s for w in ws for s in R.stack_shapes(w)]
    for net, lay, x0, y0, x1, y1 in shapes:
        if lay in C.STACK_PAD:
            assert (x1 - x0) * (y1 - y0) >= {"M2": 0.000666, "M3": 0.000666, "M4": 0.002, "M5": 0.002,
                                             "M6": 0.0021875}[lay] - 1e-9


# ------------------------------------------------------------------------------------------- CLK-AOCV fold fields
def _fold_tree():
    M = dict(meta=dict(regions=[dict(k=0, tag="t0")]),
             taps=[dict(part="p", tap="ck", port="tp0", xy=[30.0, 5.0], region=0)])
    nets = [dict(name="root", drv="port:root", loads=["ckm_n0"]), dict(name="a", drv="ckm_n0", loads=["r1"]),
            dict(name="b", drv="r1", loads=["ckm_n1_t0"]), dict(name="c", drv="ckm_n1_t0", loads=["s"]),
            dict(name="d", drv="s", loads=["port:tp0"])]
    place = {c: dict(x=float(k), y=1.0) for k, c in enumerate(["ckm_n0", "r1", "ckm_n1_t0", "s"])}
    N = {"ckm_n0": (100.0, 98.0, 20.0), "ckm_n1_t0": (300.0, 295.0, 20.0), "s": (400.0, 393.0, 20.0)}
    return M, nets, place, N


def test_aocv_fold_fields_stage_counts_and_node_arrivals(tmp_path):
    M, nets, place, N = _fold_tree()
    taps, nodes = C.aocv_fold_fields(M, nets, place, N)
    assert taps == {"tp0": dict(stages_from_root=4, xy_um=[30.0, 5.0])}
    assert nodes["h"]["stages"] == 1 and nodes["t0"]["stages"] == 3 and nodes["t0"]["late"] == 300.0
    arr = {"tp0": (450.0, 440.0, 30.0)}
    import json
    base = C.write_tap_arrivals(tmp_path / "a.json", M, "TT", arr, {"h": 2.0, "t0": 5.0}, 1)
    assert "node_stages" not in base and "stages_from_root" not in base["taps"][0]    # default: unchanged
    out = C.write_tap_arrivals(tmp_path / "b.json", M, "TT", arr, {"h": 2.0, "t0": 5.0}, 1, fold=(taps, nodes))
    assert out["node_stages"] == {"h": 1, "t0": 3} and out["node_late_ps"]["t0"] == 300.0
    assert out["taps"][0]["stages_from_root"] - out["node_stages"][out["taps"][0]["cppr_node"]] == 1
    assert out["spine_late"] == base["spine_late"]                                   # die_sta layout untouched
    assert json.loads((tmp_path / "b.json").read_text())["node_xy_um"]["t0"] == [2.0, 1.0]


def test_island_site_with_actual_body_size_opens_a_wider_window(tmp_path):
    """QC-IMPORT-1 opt-in: an ot_clock_sites/1 site with cell_um (actual provider body) gets a window sized to
    that body; a site without it keeps the planned clock body (unchanged default)."""
    import json
    f = tmp_path / "s.json"
    f.write_text(json.dumps(dict(schema="ot_clock_sites/1", sites=[
        dict(name="p", kind="partition", xy_um=[5.0, 5.0], cell_um=[4.32, 0.27]),
        dict(name="c", kind="partition", xy_um=[35.0, 5.0])])))
    sites = D.load_island_sites([str(f)])
    assert sites[0][2] == (4.32, 0.27) and len(sites[1]) == 2
    win, _ = D.island_windows(_Plan(), sites[:1])
    (x0, _, x1, _), = win["T"]
    assert x0 < 5.0 - 4.32 / 2 and x1 > 5.0 + 4.32 / 2
    old, _ = D.island_windows(_Plan(), sites[1:])
    (u0, _, u1, _), = old["T"]
    assert (u1 - u0) < (x1 - x0) and u0 > 5.0 - 4.32 / 2
