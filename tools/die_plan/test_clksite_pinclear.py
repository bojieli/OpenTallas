"""clksite_pinclear.py (KV face-pin vs die clock-site class, kit_pin_site_check main a137683011): rows move to the shortest legal
site whose obstructions clear every same-layer pin access corridor; opposite-face, multi-window and corner rows; re-check 0."""
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import clksite_pinclear as PC  # noqa: E402
import clksite_points as CP  # noqa: E402
import clksite_resite as RS  # noqa: E402
import gen_phys as G  # noqa: E402


def _row(rect, stack=None):
    r = dict(kind="die_clock_tree", rect_um=list(rect), route_layers="M1-M2")
    if stack:
        r.update(stack_layers="M3-M7", stack_um=[list(s) for s in stack])
    else:
        r["route_layers"] = "M1-M7"
    return r


def _plan(w, h, rows, cores=()):
    t = dict(outline_um=[w, h], clock=dict(reserved_sites_um=rows))
    if cores:
        t["hard_cores"] = [dict(origin_um=list(o), outline_um=list(s)) for o, s in cores]
    return dict(partition_types=dict(T=t), partitions={"p0": dict(type="T", origin_um=[1000.0, 2000.0], orient="R0")})


@pytest.fixture
def pins(monkeypatch):
    box = {}
    monkeypatch.setattr(G, "type_pins", lambda P, tn: box["pins"])
    return box


def _run(raw, **kw):
    led = PC.run(None, raw, G, RS, CP, **kw)
    return led, PC.recheck(None, raw, G)


def test_east_face_pins_under_a_seam_site_move_inward_clear_of_the_corridor(pins):
    # io_cor_v1 class: ft11_i[2..7] M5 east-face pins under the site 1276.99-1278.72 x 517.86-518.94 (type 1278.72 wide)
    pins["pins"] = [("ft11_i", b, "M5", 1278.72, 517.92 + 0.144 * b, "E") for b in range(6)]
    raw = _plan(1278.72, 1036.8, [_row((1276.992, 517.86, 1278.72, 518.94))])
    led, left = _run(raw)
    assert left == {} and len(led) == 1 and led[0]["kind"] == "inward", led
    dx, dy = led[0]["move_um"]
    assert dy == 0 and dx < 0 and abs(round(dx / RS.SITE_UM) * RS.SITE_UM - dx) < 1e-6
    assert led[0]["new"][2] <= 1278.72 - 2.0 + 1e-6          # every obstruction >= clear-um from the east face
    assert led[0]["new"][2] > 1278.72 - 2.0 - RS.SITE_UM      # and no further than one site past it
    assert led[0]["die_centre_um"]["p0"][0] == pytest.approx(1000.0 + (led[0]["new"][0] + led[0]["new"][2]) / 2)
    assert sorted(led[0]["pins_cleared"]) == [f"ft11_i[{b}]" for b in range(6)]


def test_row_between_opposite_face_pins_slides_along_the_faces(pins):
    # a 3-um-wide type: no inward move clears both E and W corridors; a slide in y past the pins does
    pins["pins"] = [("a", 0, "M4", 3.0, 10.0, "E"), ("b", 0, "M4", 0.0, 10.1, "W")]
    raw = _plan(3.0, 40.0, [_row((0.0, 9.72, 3.0, 10.53))])
    led, left = _run(raw)
    assert left == {} and led[0]["kind"] == "slide", led
    assert led[0]["move_um"][0] == 0 and led[0]["move_um"][1] != 0
    n = led[0]["new"]
    assert n[1] >= 10.1 + G.LAYER_W["M4"] / 2 + 0.1 - 1e-6 or n[3] <= 10.0 - G.LAYER_W["M4"] / 2 - 0.1 + 1e-6


def test_multi_window_row_moves_rect_and_every_stack_window_together(pins):
    # the M1-M2 rect is clear of the M6 pin; one of two M3-M7 stack windows covers it
    pins["pins"] = [("x", 0, "M6", 50.0, 20.0, "E")]
    rect = (48.0, 19.0, 50.0, 21.0)
    raw = _plan(50.0, 50.0, [_row(rect, stack=[(48.2, 19.1, 48.6, 19.5), (49.6, 19.8, 50.0, 20.2)])])
    led, left = _run(raw)
    assert left == {} and led[0]["kind"] == "inward", led
    dx = led[0]["move_um"][0]
    r = raw["partition_types"]["T"]["clock"]["reserved_sites_um"][0]
    assert r["stack_um"][0] == pytest.approx([48.2 + dx, 19.1, 48.6 + dx, 19.5])
    assert r["stack_um"][1][2] <= 50.0 - 2.0 + 1e-6
    G.stack_rects("T", r)                                     # windows still inside the moved rect


def test_corner_row_takes_the_diagonal_when_neither_axis_clears(pins):
    # E pins over the top 20 um and N pins over the right 20 um: no x-only / y-only move within 8 um clears both
    pins["pins"] = ([("e", b, "M5", 30.0, 10.0 + 0.2 * b, "E") for b in range(101)]
                    + [("n", b, "M5", 10.0 + 0.2 * b, 30.0, "N") for b in range(101)])
    raw = _plan(30.0, 30.0, [_row((29.0, 29.19, 30.0, 30.0))])
    led, left = _run(raw, max_move=8.0)
    assert left == {} and led[0]["kind"] == "inward", led
    dx, dy = led[0]["move_um"]
    assert dx < 0 and dy < 0 and sorted(led[0]["faces"]) == ["E", "N"]


def test_no_legal_site_in_reach_is_reported_not_moved(pins):
    # a hard core (+ halo) fills the inside and the face is pinned densely: nothing within 20 um
    pins["pins"] = [("p", b, "M5", 40.0, 0.1 * b, "E") for b in range(400)]
    raw = _plan(40.0, 40.0, [_row((39.0, 19.98, 40.0, 20.25))], cores=[((0.0, 0.0), (37.5, 40.0))])
    led, left = _run(raw)
    assert led[0]["new"] is None and "no legal" in led[0]["why"]
    assert left == {"T": len(led[0]["pins"])}
    assert raw["partition_types"]["T"]["clock"]["reserved_sites_um"][0]["rect_um"] == [39.0, 19.98, 40.0, 20.25]


def test_rows_without_pin_hits_and_other_kinds_are_untouched(pins):
    pins["pins"] = [("p", 0, "M5", 40.0, 5.0, "E")]
    rows = [_row((10.0, 10.26, 11.08, 11.07)), dict(kind="landing_ring_bank", rect_um=[38.0, 4.0, 40.0, 6.0])]
    raw = _plan(40.0, 40.0, rows)
    led, left = _run(raw)
    assert led == [] and left == {}
    assert raw["partition_types"]["T"]["clock"]["reserved_sites_um"] == rows


def _landing(raw, pins_):
    raw["partition_types"]["T"]["clock"]["landing_contract"] = dict(pins=pins_)
    return raw


def test_landing_pin_escape_corridor_moves_a_cluster_4um_west_of_the_pin(pins):
    # C-CLKSITE-LANDPIN (kv3_phy_v1 fclk_out_cland_up[0]): M7 pin 2.1 um inside the east face, cluster 4 um west of it with a
    # M3-M7 window: no face-pin rect/2-um corridor is touched, but the 8-um escape corridor is
    pins["pins"] = []
    rect = (848.77, 760.86, 857.74, 764.37)
    raw = _landing(_plan(864.0, 1520.64, [_row(rect, stack=[rect])]),
                   [dict(name="fclk_out_cland_up", layer="M7", dir="out", kind="clock", xy_um=[861.856, 761.952]),
                    dict(name="cland_up_ready", layer="M7", dir="out", kind="ctl", xy_um=[861.856, 763.392])])
    assert PC.recheck(None, raw, G) == {"T": 4}                   # 2 pins x (M7, M6): the stack window covers M3-M7 corridors
    raw0 = _landing(_plan(864.0, 1520.64, [_row(rect, stack=[rect])]), raw["partition_types"]["T"]["clock"]["landing_contract"]["pins"])
    led, left = _run(raw0)
    assert left == {} and len(led) == 1 and led[0]["kind"] == "inward", led
    assert sorted(led[0]["pins_cleared"]) == ["cland_up_ready", "fclk_out_cland_up"]
    assert led[0]["new"][2] <= 861.856 - 8.0 - PC.LAND_MARGIN_UM + 1e-6   # obstruction ends >= 8 um + stand-off from the pin
    r = raw0["partition_types"]["T"]["clock"]["reserved_sites_um"][0]
    assert max(w[2] for w in r["stack_um"]) <= 861.856 - 10.0 + 1e-6      # every M3-M7 window, not just the rect
    assert not any(w[3] > 761.952 - 0.216 - 2.1 and w[1] < 761.952 + 0.216 + 2.1 and w[2] > 861.856 - 10.0 for w in r["stack_um"])


def test_landing_corridor_is_class_wide_and_can_be_switched_off(pins):
    pins["pins"] = []
    for face_xy, w, h in (([2.0, 50.0], 40.0, 100.0), ([20.0, 97.0], 40.0, 100.0)):     # west-face pin, north-face pin
        rect = (face_xy[0] + 4.0, face_xy[1] - 1.0, face_xy[0] + 6.0, face_xy[1] + 1.0) if face_xy[0] < 5 else \
            (face_xy[0] - 1.0, face_xy[1] - 7.0, face_xy[0] + 1.0, face_xy[1] - 5.0)
        raw = _landing(_plan(w, h, [_row(rect)]), [dict(name="cland_up_fault", layer="M7", xy_um=face_xy)])
        raw["partition_types"]["T"]["clock"]["reserved_sites_um"][0]["route_layers"] = "M1-M7"
        led, left = _run(raw)
        assert left == {} and led[0]["new"] is not None, led
        raw = _landing(_plan(w, h, [_row(rect)]), [dict(name="cland_up_fault", layer="M7", xy_um=face_xy)])
        raw["partition_types"]["T"]["clock"]["reserved_sites_um"][0]["route_layers"] = "M1-M7"
        assert PC.run(None, raw, G, RS, CP, land_clear=0.0) == []     # off = the old behaviour
