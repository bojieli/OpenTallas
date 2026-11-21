"""TAP-GRID-R3 11-21 (COORD ruling): tap caps count only the registers on the tap's own clock net, read from the netlist
(tap_resolve --dump clock_root), never inferred from a register's position (e.g. inside a landing band)."""
import json
from pathlib import Path
import pytest
import schema
import taps
import check
import tap_resolve as TR


def test_trace_root_port_direct():
    assert TR.trace_root("ck", lambda n: ("port", "clk")) == "clk"


def test_trace_root_through_buffers_and_icg():
    g = {"ff/CLK": ("next", "buf/A"), "buf/A": ("next", "icg/CLK"), "icg/CLK": ("port", "fclk_in_ft12_i")}
    assert TR.trace_root("ff/CLK", g.__getitem__) == "fclk_in_ft12_i"


def test_trace_root_stop_and_loop():
    assert TR.trace_root("a", lambda n: ("stop", "AND2x2_ASAP7_75t_R")) == "unresolved:AND2x2_ASAP7_75t_R"
    assert TR.trace_root("a", {"a": ("next", "b"), "b": ("next", "a")}.__getitem__) == "unresolved:loop"
    assert TR.trace_root("a", lambda n: ("next", n + "x"), max_depth=5) == "unresolved:depth"


def _dump():
    cells = [["u_a", 0, 0, 1, 1, "DFFHQNx1_ASAP7_75t_R"], ["u_b", 0, 0, 1, 1, "DFFHQNx1_ASAP7_75t_R"],
             ["u_ring_w", 0, 0, 1, 1, "DFFHQNx1_ASAP7_75t_R"], ["u_ring_r", 0, 0, 1, 1, "DFFHQNx1_ASAP7_75t_R"],
             ["u_x", 30, 30, 31, 31, "DFFHQNx1_ASAP7_75t_R"], ["u_buf", 0, 0, 1, 1, "BUFx2_ASAP7_75t_R"]]
    return {"outline": [0, 0, 100, 100], "cells": cells,
            "clock_root": ["clk", "clk_t3", "fclk_in_ft12_i", "clk", "unresolved:drivers2", "clk"]}


def test_bins_tap_net_keeps_only_tap_roots():
    b = taps.bins_from_dump(_dump(), bin_um=10.8, tap_net=True)
    assert b["basis"] == "tap_net" and b["n"] == 3          # u_a, u_b, u_ring_r (co-located with the forwarded writer)
    assert b["bins"] == [[5.4, 5.4, 3]]
    assert b["excluded"] == 2 and b["excluded_roots"] == {"fclk_in_ftN_i": 1, "unresolved:drivers2": 1}


def test_bins_default_unchanged_and_tap_net_needs_roots():
    d = _dump()
    b = taps.bins_from_dump(d, bin_um=10.8)
    assert b["n"] == 5 and "basis" not in b
    del d["clock_root"]
    with pytest.raises(ValueError):
        taps.bins_from_dump(d, tap_net=True)


def test_g0_tap_sink_loads_counts_tap_net_inventory(tmp_path):
    f = tmp_path / "bins.json"
    f.write_text(json.dumps(taps.bins_from_dump(_dump(), bin_um=10.8, tap_net=True)))
    r = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())
    r["partition_types"]["src"]["clock"].update(tap_mode="grid+explicit", added_taps=[], tap_max_sinks=2,
                                                sink_bins_file=str(f))
    P = schema.Plan(r)
    rows, st = check.tap_sink_loads(P)
    assert st["tap_net_types"] == 1
    src = [q for q in rows if q[0] == "src"]
    assert sum(q[2] for q in src) >= 3 and max(q[2] for q in src) <= 3   # the forwarded writer is not on any tap
