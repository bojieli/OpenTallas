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
