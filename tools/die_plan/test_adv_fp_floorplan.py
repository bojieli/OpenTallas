"""pytest: ADV-FP-FLOORPLAN (FP-CONVERGE-KV): one passing plan and one mutant per class must fail."""
import copy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as F  # noqa: E402


def _core(name, x, y, w=300.0, h=300.0):
    return {"name": name, "origin_um": [x, y], "outline_um": [w, h]}


def _type(bits=64, gap=100.0, cells=1000):
    # two cores side by side with a vertical street of width `gap`; one internal lane crosses the street
    a, b = _core("a", 0.0, 0.0), _core("b", 300.0 + gap, 0.0)
    st = [{"launch": "bus x", "from_um": [100.0, 150.0], "regs_um": [[300.0 + gap / 2, 150.0]], "to_um": [500.0, 150.0]}]
    return {"outline_um": [700.0 + gap, 600.0], "hard_cores": [a, b], "buses": [{"name": "x", "width": bits}],
            "internal_stations": st, "ft_slots": [], "cells": cells}


def _lines(t):
    return F.findings({"partition_types": {"T": t}})


def test_clean_plan_passes():
    out = _lines(_type())
    assert not [x for x in out if "ADV-FP-STREET" in x or "ADV-FP-OVERSIZE" in x or "ADV-FP-OVERLAP" in x]
    assert out[-1].startswith("WARN ADV-FP-FLOORPLAN summary 0 type(s)")


def test_street_mutant_fails():
    out = _lines(_type(bits=100000, gap=10.0))
    assert any(x.startswith("WARN ADV-FP-STREET T:") for x in out)


def test_oversize_mutant_fails():
    assert any("ADV-FP-OVERSIZE T:" in x for x in _lines(_type(cells=998239)))


def test_overlap_mutant_fails():
    t = _type()
    t["hard_cores"][1]["origin_um"] = [250.0, 0.0]
    assert any("ADV-FP-OVERLAP T:" in x for x in _lines(t))
    t2 = copy.deepcopy(_type())
    t2["hard_cores"][1]["origin_um"] = [900.0, 0.0]
    assert any("1 core(s) outside" in x for x in _lines(t2))


def test_block_env_makes_fail_lines(monkeypatch):
    monkeypatch.setenv("OT_FP_BLOCK", "1")
    assert any(x.startswith("FAIL ADV-FP-OVERSIZE") for x in _lines(_type(cells=500000)))


def test_malformed_never_raises():
    out = F.findings({"partition_types": {"bad": {"outline_um": [10, 10], "hard_cores": [{"origin_um": "x", "outline_um": [1, 1]}]}}})
    assert out and out[-1].startswith("WARN ADV-FP-FLOORPLAN summary")
    assert F.findings(None)[-1].startswith("WARN") if F.findings(None) else True


def _cross_type(y1):
    # one tall core leaving 20 um streets above and below; lane 1 at y1 (inside the core when 300), lane 2 on the upper street
    core = {"name": "c", "origin_um": [0.0, 20.0], "outline_um": [300.0, 560.0]}
    lane = lambda y, nm: {"launch": "bus " + nm, "from_um": [100.0, y], "regs_um": [[250.0, y]], "to_um": [500.0, y]}
    return {"outline_um": [600.0, 600.0], "hard_cores": [core], "buses": [{"name": "a", "width": 400}, {"name": "b", "width": 400}],
            "internal_stations": [lane(y1, "a"), lane(590.0, "b")], "ft_slots": [], "cells": 1000}


def test_core_crossing_leg_loads_both_streets():
    # lane a runs through the core interior: its 400 bits also load the 20 um street that lane b uses (800 bits > 578 tracks)
    w = F.street_worst(_cross_type(300.0))
    assert w and w[0] > 1.0
    # lane a kept in the lower street: 400 bits per street, no crossing
    ok = F.street_worst(_cross_type(10.0))
    assert ok and ok[0] < 1.0


def test_ft_crosses_core_is_report_only():
    out = _lines(_cross_type(300.0))
    assert any(x.startswith("WARN ADV-FT-CROSSES-CORE T:") and "a>c:800b" in x for x in out)
    assert not any("ADV-FT-CROSSES-CORE" in x for x in _lines(_cross_type(10.0)))



def test_exact_internal_bit_width_takes_precedence_over_shared_bus_width():
    t = _cross_type(300.0)
    t["internal_stations"][0]["bits"] = 150
    assert F.street_worst(t)[4] == 550
    assert F.street_worst(t)[0] < 1


def test_face_only_ft_loads_full_width_wall_without_explicit_centres():
    t = {"outline_um": [600, 500],
         "hard_cores": [_core("wall", 140, 0, 300, 500)],
         "ft_slots": [{"name": "bring", "width": 256, "in_face": "W", "out_face": "E",
                       "in_window_um": [20, 30], "out_window_um": [20, 30]}]}
    worst = F.street_worst(t)
    assert worst[:6] == (float("inf"), "H", 290, [0, 0], 256, 0)


def test_street_assignment_uses_the_cut_intersection_not_segment_center():
    t = {"outline_um": [1000, 900], "hard_cores": [_core("divider", 80, 150, 40, 550)],
         "internal_stations": [{"conn": "core:g", "bits": 64, "from_um": [0, 50], "to_um": [1000, 830]}]}
    assert F.street_worst(t)[:5] == (64 / (150 * F.TH * F.USABLE), "H", 100, [0, 150], 64)


def test_cut_and_overlap_use_signed_placed_macro_box():
    t = {"outline_um": [600, 500],
         "hard_cores": [dict(_core("wall", 140, -0.54, 500, 300), orient="R90",
                              track_offset_um=[0, 0.54])],
         "ft_slots": [{"name": "bring", "width": 256, "in_face": "W", "out_face": "E",
                       "in_window_um": [20, 30], "out_window_um": [20, 30]}]}
    assert F.street_worst(t)[:6] == (float("inf"), "H", 290, [0, 0], 256, 0)
    assert F.overlaps(t) == ([], [])
    t["hard_cores"][0]["track_offset_um"] = [0, 0]
    assert F.overlaps(t) == ([], ["wall"])


def test_roundoff_seam_is_closed_and_outside_boxes_add_no_capacity():
    assert F._free([(-60, 200.0), (200.0 + 1e-12, 500.0 - 1e-12)], 500.0) == []
    assert F._free([(-60, -2), (550, 580)], 500.0) == [(0.0, 500.0)]
    assert F._free([(-60, 200), (200.005, 510)], 500.0) == [(200, 200.005)]


def _flat_lines(t, cache=None, growth=None, flat=True):
    old = {k: os.environ.get(k) for k in ("OT_FP_OVERSIZE_FLAT", "OT_FP_OVERSIZE_REPAIR_GROWTH")}
    try:
        for k in old:
            os.environ.pop(k, None)
        if flat:
            os.environ["OT_FP_OVERSIZE_FLAT"] = "1"
        if growth:
            os.environ["OT_FP_OVERSIZE_REPAIR_GROWTH"] = str(growth)
        raw = {"die": {"name": "d"}, "partition_types": {"T": t}}
        return F.findings(raw, cells_cache={"cells": {"d": cache or {}}})
    finally:
        for k, v in old.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_flag_off_is_byte_identical():
    t = _type(cells=998239)
    exp = "WARN ADV-FP-OVERSIZE T: 998239 cells > 400000 single-run cap; fix: split the type"
    assert exp in _lines(t)
    # cells_cache / growth knobs without the flag change nothing
    assert _flat_lines(t, cache={"T": {"last": {"cells": 1, "t0": 1}}}, growth=9, flat=False) == _lines(t)


def test_flat_hierarchical_type_is_not_oversize():
    t = _type(cells=998239)                       # two hard cores: plan cells include their content
    kit = {"T": {"last": {"cells": 294275, "t0": time.time() - 86400, "stage": "place"}}}
    out = _flat_lines(t, cache=kit)
    assert not any("ADV-FP-OVERSIZE" in x for x in out)
    assert out[-1].startswith("WARN ADV-FP-FLOORPLAN summary 0 type(s)") and " 0 over 400000" in out[-1]


def test_flat_repair_growth_projects_over_cap():
    t = _type(cells=998239)
    kit = {"T": {"last": {"cells": 333341, "t0": time.time() - 86400, "stage": "geom"}}}      # lepw_mus_C: 333k synth, >400k after TD repair
    assert not any("ADV-FP-OVERSIZE" in x for x in _flat_lines(t, cache=kit, growth=1.15))
    hit = [x for x in _flat_lines(t, cache=kit, growth=1.25) if "ADV-FP-OVERSIZE" in x]
    assert hit and "flat 333,341" in hit[0] and "2 hard core(s)" in hit[0]


def test_flat_soft_type_over_cap_still_flagged():
    t = _type(cells=500000)
    t["hard_cores"] = []
    assert any("ADV-FP-OVERSIZE T:" in x for x in _flat_lines(t))


def test_flat_stale_kit_is_ignored():
    t = _type(cells=998239)
    stale = {"T": {"last": {"cells": 5000000, "t0": time.time() - 6 * 86400, "stage": "place"}}}   # svc 11-20 flat kits predate the cores
    assert not any("ADV-FP-OVERSIZE" in x for x in _flat_lines(t, cache=stale))

def test_colocated_station_spans_price_each_active_rank_once(monkeypatch):
    from adv_fp_floorplan import aligned_edge_rank_worst, findings

    # Actual fe96 P2 geometry in the type frame, excluding unrelated cores.
    kind = "col_h9_r0_p2__fixture"
    typed = {
        "outline_um": [1442.88, 1278.72],
        "buses": [{"name": "frame_int_o0", "width": 1167}, {"name": "frame_int_i0", "width": 261}],
        "internal_stations": [
            {"conn": "bus:frame_int_o0", "from_um": [1410.744, 604.854],
             "regs_um": [[1410.744, 951.265], [1391.788, 1278.72], [1045.377, 1278.72],
                         [698.966, 1278.72], [352.555, 1278.72]], "to_um": [132.946, 1278.72]},
            {"conn": "bus:frame_int_i0", "from_um": [288.174, 1278.72],
             "regs_um": [[591.179, 1278.72], [894.183, 1278.72], [1197.188, 1278.72]],
             "to_um": [1352.232, 1130.759]},
        ],
    }
    raw_plan = {"partition_types": {kind: typed}}
    row = aligned_edge_rank_worst(typed, {}, kind)
    assert row["bits"] == 1168 + 262
    assert row["span_um"] == (288.174, 1197.188)
    assert row["span_um"][0] < 1007.5 < row["span_um"][1]
    assert round(row["ratio"], 3) == 2.485
    assert any(line.startswith("WARN ADV-FP-STREET ") for line in findings(raw_plan, None))
    monkeypatch.setenv("OT_FP_BLOCK", "1")
    assert any(line.startswith("FAIL ADV-FP-STREET ") for line in findings(raw_plan, None))
    assert aligned_edge_rank_worst(typed, {}, "other_fixture") is None
    separated = copy.deepcopy(typed)
    for site in separated["internal_stations"][0]["regs_um"][1:]:
        site[1] -= 27
    assert aligned_edge_rank_worst(separated, {}, kind) is None
    typed["internal_stations"][0]["sites"] = "float"
    assert aligned_edge_rank_worst(typed, {}, kind) is None
