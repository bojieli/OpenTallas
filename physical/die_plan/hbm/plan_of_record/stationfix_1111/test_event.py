"""stationfix_1111: target entries flip core -> face, nothing else changes, idempotent, wrong base fails closed."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("stationfix_event", HERE / "event.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
T = (("q_x", "L1_o", 1, "u_ep.fault"),)


def _plan():
    out = {"conn": "bus:L1_o", "from_um": [80.0, 100.0], "to_um": [20.0, 40.0], "regs_um": [[60.0, 100.0], [20.0, 90.0]],
           "launch": "u_ep.fault", "capture": "face flop", "note": "TYPE-SAFE-2 relay"}
    other = {"conn": "bus:L2_o", "from_um": [100.0, 30.0], "to_um": [10.0, 30.0], "regs_um": [[60.0, 30.0]],
             "launch": "face bus L2_o", "capture": "u_ep.tx"}
    t = {"outline_um": [100.0, 100.0], "buses": [{"name": "L1_o", "dir": "out"}, {"name": "L2_o", "dir": "out"}],
         "internal_stations": [other, out]}
    return {"schema": "s", "partition_types": {"q_x": t, "q_y": {"outline_um": [1, 1]}}}


def test_flip_only_targets_and_idempotent():
    p, rows = ev.apply(_plan(), T)
    e = p["partition_types"]["q_x"]["internal_stations"][1]
    assert e["from_um"] == [20.0, 40.0] and e["to_um"] == [80.0, 100.0]
    assert e["regs_um"] == [[20.0, 90.0], [60.0, 100.0]] and e["note"] == "TYPE-SAFE-2 relay"
    assert p["partition_types"]["q_x"]["internal_stations"][0] == _plan()["partition_types"]["q_x"]["internal_stations"][0]
    assert p["partition_types"]["q_y"] == {"outline_um": [1, 1]} and rows[0]["action"] == "flipped"
    q, rows2 = ev.apply(p, T)
    assert q == p and rows2[0]["action"] == "already_core_first"


def test_keyed_by_bus_and_index_fail_closed():
    p = _plan()
    st = p["partition_types"]["q_x"]["internal_stations"]
    st.reverse()                                      # same bus at another index: refuse, do not guess
    with pytest.raises(SystemExit, match="is not bus:L1_o"):
        ev.apply(p, T)
    p = _plan()
    p["partition_types"]["q_x"]["internal_stations"][1]["launch"] = "face bus L1_o"
    with pytest.raises(SystemExit, match="expected an out bus"):
        ev.apply(p, T)


def test_native_entries_unchanged_by_the_flip():
    """with native_istations.face_first the native source entry is identical before and after the event"""
    import sys
    root = HERE.parents[4]
    sys.path.insert(0, str(root / "tools" / "die_plan"))
    import native_istations as N
    a = _plan()["partition_types"]["q_x"]
    b = ev.apply(_plan(), T)[0]["partition_types"]["q_x"]
    assert N.source_entries(a, {"L1_o"}) == N.source_entries(b, {"L1_o"})


def test_real_targets_match_lint_rows():
    assert len(ev.TARGETS) == 13 and len({(t, b, i) for t, b, i, _ in ev.TARGETS}) == 13
