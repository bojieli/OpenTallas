"""Tests for gen_plan.ft_fracs measured cells (FTFR-1110) and the delta_ftfr_1110 plan event (DIE-QC-97)."""
import copy, json, os, sys, types
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_plan as GP  # noqa: E402
import delta_ftfr_1110 as ev  # noqa: E402

W, H = 613.44, 1339.2
A = W * H


def _cells_for(fill, upc):
    return int(round(fill * GP.UTIL * A / upc))


def _ev(tmp_path, rows):
    p = tmp_path / "ev.json"
    p.write_text(json.dumps({"schema": "qc_cells_evidence.v1", "cells_per_type": rows}))
    return [str(p)]


def _meas(c):
    return {"basis": "measured yosys synth_stat (kit of this type)", "cells": c}


def test_thresholds_and_note():
    assert GP.ft_frac_of(0.02) == 0.5 and GP.ft_frac_of(0.1034) == 0.4 and GP.ft_frac_of(0.25) is None
    assert GP.CELL_UM2 == 0.52 and GP.FT_STD_UM2 == 0.135
    # sle_hc1: measured 381,548 cells on 613.44 x 1339.2 -> ~0.10 (COORD expectation)
    assert abs(GP.ft_fill(381548, GP.FT_STD_UM2, W, H) - 0.1045) < 1e-3
    assert GP.ft_note(0.02, 0.5) == "est. std-cell fill 0.02 at util 0.6: 50% of M4-M7 to ft"
    assert "FTFR-1110" in GP.ft_note(0.1, 0.4, 381548)


def _P(cells):
    P = GP.Plan()
    for tn, c in cells.items():
        P.add_type(tn, (W, H), "m_" + tn, [], cells=c)
        P.add_part("p_" + tn, tn, 0, 0)
    P.add_type("hardx", (W, H), "mh", [], hard=True, cells=10)
    P.add_part("p_hardx", "hardx", 0, 0)
    return P


def test_ft_fracs_measured_and_fallback(tmp_path):
    est = _cells_for(0.02, GP.CELL_UM2)            # old plan estimate -> fill 0.02
    P = _P({"sle_hc1": est, "slw_x": est, "sle_y": est})
    evid = _ev(tmp_path, {"sle_hc1__claaaa": _meas(_cells_for(0.30, GP.FT_STD_UM2)),
                          "sle_y": {"basis": "plan estimate plan_notes.json (no measured kit synth yet)", "cells": 9}})
    GP.ft_fracs(P, evid)
    t = P.types
    assert "ft_track_frac" not in t["sle_hc1"]                       # measured cohort: fill 0.30 -> G0 default
    assert t["slw_x"]["ft_track_frac"] == 0.5                        # no evidence: historic rule, byte-same note
    assert t["slw_x"]["note"] == "est. std-cell fill 0.02 at util 0.6: 50% of M4-M7 to ft"
    assert t["sle_y"]["ft_track_frac"] == 0.5 and t["sle_y"]["note"].startswith("est. ")   # plan-estimate row ignored
    assert "ft_track_frac" not in t["hardx"]


def _plan(entries):
    """entries: {type: (old_frac_or_None, old_fill_or_None, extra)}"""
    pt, parts = {}, []
    for tn, (fr, fill, extra) in entries.items():
        t = {"module": "m_" + tn, "outline_um": [W, H], "contents": [{"inst": "u", "module": "x"}],
             "buses": [{"name": "b", "face": "N", "window_um": [1.0, 2.0]}], "verilog_defines": ["D"],
             "note": "slice region partition " + tn}
        if fr is not None:
            t["ft_track_frac"] = fr
            t["note"] += f"; est. std-cell fill {fill:.2f} at util 0.6: {fr:.0%} of M4-M7 to ft;clock landing cohort"
        t.update(extra)
        pt[tn] = t
        parts.append({"name": "p_" + tn, "type": tn, "origin_um": [0, 0], "orient": "R0"})
    return {"schema": "opentallas.die_plan.v1", "die": {"name": "qc"}, "partition_types": pt, "partitions": parts,
            "lanes": [{"x": 1}]}


def _tree_diff(a, b, path=""):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = []
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out += _tree_diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        return sum((_tree_diff(x, y, f"{path}[{i}]") for i, (x, y) in enumerate(zip(a, b))), [])
    return [] if a == b else [path]


def test_event_rewrites_only_affected(tmp_path):
    raw = _plan({"hc1": (0.5, 0.02, {}), "stm": (None, None, {}), "same": (0.5, 0.02, {}), "unk": (0.4, 0.12, {}),
                 "dense": (0.5, 0.03, {}), "hardy": (None, None, {"hard": True})})
    evid = _ev(tmp_path, {"hc1": _meas(_cells_for(0.1034, GP.FT_STD_UM2)),
                          "stm": _meas(_cells_for(0.06, GP.FT_STD_UM2)),
                          "same": _meas(_cells_for(0.05, GP.FT_STD_UM2)),
                          "dense": _meas(_cells_for(0.40, GP.FT_STD_UM2)),
                          "hardy": _meas(10)})
    orig = copy.deepcopy(raw)
    new, ch = ev.apply(raw, evid)
    assert set(ch) == {"hc1", "stm", "dense"}
    assert new["partition_types"]["hc1"]["ft_track_frac"] == 0.4
    assert new["partition_types"]["stm"]["ft_track_frac"] == 0.5
    assert "ft_track_frac" not in new["partition_types"]["dense"]
    assert new["partition_types"]["dense"]["note"] == "slice region partition dense;clock landing cohort"
    n = new["partition_types"]["hc1"]["note"]
    assert n.startswith("slice region partition hc1; std-cell fill 0.10 at util 0.6 (measured ") and \
        n.endswith("FTFR-1110): 40% of M4-M7 to ft;clock landing cohort")
    assert ch["hc1"]["old_layers"] == {L: 0.5 for L in ev.LAYERS} and ch["hc1"]["new_layers"]["M7"] == 0.4
    d = _tree_diff(orig, new)
    assert sorted(d) == sorted(["/partition_types/hc1/ft_track_frac", "/partition_types/hc1/note",
                                "/partition_types/stm/ft_track_frac", "/partition_types/stm/note",
                                "/partition_types/dense/ft_track_frac", "/partition_types/dense/note"])
    for tn in ("same", "unk", "hardy"):
        assert json.dumps(orig["partition_types"][tn]) == json.dumps(new["partition_types"][tn])
    with pytest.raises(SystemExit, match="re-application"):
        ev.apply(new, evid)


def test_event_lower_only(tmp_path):
    raw = _plan({"hc1": (0.5, 0.02, {}), "stm": (None, None, {}), "hc0": (0.4, 0.21, {})})
    evid = _ev(tmp_path, {"hc1": _meas(_cells_for(0.1034, GP.FT_STD_UM2)),
                          "stm": _meas(_cells_for(0.06, GP.FT_STD_UM2)),
                          "hc0": _meas(_cells_for(0.09, GP.FT_STD_UM2))})
    _, ch = ev.apply(raw, evid, lower_only=True)
    assert set(ch) == {"hc1"}


def test_event_refusals(tmp_path):
    evid = _ev(tmp_path, {"a": _meas(_cells_for(0.05, GP.FT_STD_UM2))})
    with pytest.raises(SystemExit, match="nothing to change"):
        ev.apply(_plan({"a": (0.5, 0.02, {})}), evid)
    raw = _plan({"a": (None, None, {"ft_track_frac": 0.6})})          # foreign frac (no ft_fracs fragment)
    with pytest.raises(SystemExit, match="foreign"):
        ev.apply(raw, evid)


def test_check_catches_netlist_change():
    raw = _plan({"a": (0.5, 0.02, {})})
    new = copy.deepcopy(raw)
    new["partition_types"]["a"]["verilog_defines"] = ["E"]
    with pytest.raises(SystemExit):
        ev.check(raw, new, {"a"})
    new = copy.deepcopy(raw)
    new["lanes"][0]["x"] = 2
    with pytest.raises(SystemExit, match="lanes"):
        ev.check(raw, new, {"a"})
