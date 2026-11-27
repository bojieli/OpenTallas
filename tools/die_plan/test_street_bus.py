"""pytest: ADV-FP-STREET-BUS (C-STREET-R3, 11-27): face-bus legs priced as street lanes; HEAD W12f false green (4 placed street failures read 0)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as F  # noqa: E402


def _core(inst, x, y, w, h):
    return {"inst": inst, "origin_um": [x, y], "outline_um": [w, h], "track_offset_um": [0.0, 0.0], "orient": "R0"}


def _shelf(bits, gap=17.0):
    """two big cores with a thin shelf between; bus enters W face, leaf in the lower core (no station row: the old check is blind)."""
    top = 500.0
    return {"outline_um": [600.0, 1000.0],
            "hard_cores": [_core("u_a.core", 50, 0, 500, top), _core("u_b.core", 50, top + gap, 500, 1000 - top - gap)],
            "buses": [{"name": "d_i", "width": bits, "face": "W", "window_um": [700.0, 900.0], "leaf": "u_a.d_i"}],
            "internal_stations": [], "ft_slots": [], "cells": 10}


def test_old_check_blind_bus_check_sees_it(monkeypatch):
    monkeypatch.delenv("OT_STREET_BUS", raising=False)
    t = _shelf(3000)
    assert F.street_worst(t) is None
    f = F.findings({"partition_types": {"T": t}})
    assert not any(x.startswith("WARN ADV-FP-STREET T") for x in f)
    assert any(x.startswith("WARN ADV-FP-STREET-BUS T:") for x in f)
    assert any("(+1 bus-lane model" in x for x in f)


def test_small_bus_not_flagged(monkeypatch):
    monkeypatch.delenv("OT_STREET_BUS", raising=False)
    assert not any("ADV-FP-STREET-BUS" in x for x in F.findings({"partition_types": {"T": _shelf(20)}}))


def test_disable_env(monkeypatch):
    monkeypatch.setenv("OT_STREET_BUS", "0")
    assert not any("ADV-FP-STREET-BUS" in x for x in F.findings({"partition_types": {"T": _shelf(3000)}}))


def test_bus_with_station_row_not_double_counted():
    t = _shelf(3000)
    t["internal_stations"] = [{"launch": "bus d_i", "from_um": [0, 800], "regs_um": [], "to_um": [300, 250], "bits": 3000}]
    assert F.bus_lanes(t) == []


def test_class_tag_unchanged_for_counted_class():
    """class_track matches the exact tag ADV-FP-STREET followed by whitespace: the BUS tag must not be counted as C-STREET."""
    import re
    line = "WARN ADV-FP-STREET-BUS T: lane demand 3.0"
    assert not re.match(r"^(?:WARN|FAIL)\s+" + re.escape("ADV-FP-STREET") + r"\s+(\S+?):?\s", line + " ")


def test_coreless_bus_lane_band(monkeypatch):
    monkeypatch.delenv("OT_STREET_BUS", raising=False)
    t = {"outline_um": [600.0, 2000.0], "hard_cores": [], "buses": [], "internal_stations": [], "ft_slots": [], "cells": 1}
    assert F.bus_lanes(t) == []
    assert not any("STREET-BUS" in x for x in F.findings({"partition_types": {"T": t}}))
