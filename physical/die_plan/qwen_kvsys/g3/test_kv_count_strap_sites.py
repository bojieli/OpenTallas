#!/usr/bin/env python3
"""tests for kv_count_strap_sites.py (run: python3 test_kv_count_strap_sites.py)."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kv_count_strap_sites as K   # noqa: E402


def plan():
    return {"partition_types": {"t": {
        "outline_um": [200.0, 100.0],
        "contents": [{"inst": "m", "origin_um": [60.0, 0.0], "outline_um": [20.0, 20.0]}],
        "clock": {"keepouts_um": [[120.0, 0.0, 125.0, 10.0]]},
        "count_straps": [{"name": "strap_ca_efall", "width": 1}, {"name": "strap_ca_k_x", "width": 30}]}}}


def test_assign_on_track_clear_and_idempotent():
    P = plan()
    pins = [{"name": "a[0]", "layer": "M4", "x": 21.92, "y": 4.32}]
    r = K.assign(P, "t", "M7", pins)
    assert r["bits"] == 31 and r["changed"]
    s = [xy for c in P["partition_types"]["t"]["count_straps"] for xy in c["sites_um"]]
    assert len(s) == 31 and len({tuple(v) for v in s}) == 31
    for x, y in s:
        assert abs(((x - 0.032) / 0.064) - round((x - 0.032) / 0.064)) < 1e-6        # on an M7 track
        assert not (55.68 <= x <= 84.32 and y <= 24.32)                               # macro + 4.32
        assert not (118.0 <= x <= 127.0 and y <= 12.0)                                # keepout + 2
        assert not (abs(x - 21.92) < 1.0 and abs(y - 4.32) < 1.0)                     # existing pin
    assert len(P["partition_types"]["t"]["count_straps"][0]["sites_um"]) == 1
    Q = copy.deepcopy(P)
    r2 = K.assign(Q, "t", "M7", pins)
    assert not r2["changed"] and Q == P                                              # idempotent


def test_partial_fails_closed():
    P = plan()
    P["partition_types"]["t"]["count_straps"][0].update(layer="M7", sites_um=[[1.0, 1.0]])
    try:
        K.assign(P, "t", "M7", [])
    except SystemExit:
        return
    raise AssertionError("partial assignment accepted")


if __name__ == "__main__":
    test_assign_on_track_clear_and_idempotent()
    test_partial_fails_closed()
    print("2 PASS")
