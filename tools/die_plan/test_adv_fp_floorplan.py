"""pytest: ADV-FP-FLOORPLAN (FP-CONVERGE-KV): one passing plan and one mutant per class must fail."""
import copy
import os
import sys

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
