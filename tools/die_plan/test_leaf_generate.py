"""FP-CONVERGE-S81 S-06: leaf_generate schema test fails on float coordinates, tap names, seats in cores / outside, ANCHORDRY."""
import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_generate as LG  # noqa: E402


def row():
    return {"outline_um": [400, 300],
            "hard_cores": [{"inst": "u_a", "origin_um": [100, 100], "outline_um": [100, 100], "orient": "R0"}],
            "relay_sites": {"u_r/q": [20.0, 20.0]},
            "relay_depth": [{"name": "c_s", "bits": [3, 4]}],
            "clock": {"tap_mode": "grid+explicit", "reach_fix_sinks": [], "landing_contract": {"collector_tree": {"root": [10.0, 10.0], "outs": []}}}}


def plans():
    b = {"partition_types": {"T": row()}}
    return b, copy.deepcopy(b)


def ok_tap(raw, path, tns):
    return {}


def ok_anchor(raw, braw, tns):
    return []


def run(b, n):
    return LG.schema_test(b, n, ["T"], tap_check=ok_tap, anchor_check=ok_anchor)


def test_clean_plan_passes():
    b, n = plans()
    assert run(b, n) == []


def test_float_bits_pair_fails_and_mutant_names_it():
    b, n = plans()
    n["partition_types"]["T"]["relay_depth"][0]["bits"] = [3.0, 4]          # the SCHEMA-INVALID x6 regression
    f = run(b, n)
    assert f and all(x.startswith("FAIL FLOAT") for x in f) and "relay_depth" in f[0]
    b2, n2 = plans()
    n2["partition_types"]["T"]["relay_depth"][0]["bits"] = [3.5, 4]         # a non-integer bits value is also refused
    assert any("FLOAT" in x for x in run(b2, n2))
    b3, n3 = plans()
    n3["partition_types"]["T"]["relay_sites"]["u_r/q"] = [20.5, 20.0]       # a genuine coordinate move stays legal
    assert run(b3, n3) == []


def test_renamed_tap_fails_through_the_bind_check():
    b, n = plans()
    f = LG.schema_test(b, n, ["T"], tap_check=lambda raw, p, t: {"T": "added taps must be [clk_t20 ...]"}, anchor_check=ok_anchor)
    assert f == ["FAIL TAPNAME T: added taps must be [clk_t20 ...]"]


def test_relay_site_in_core_or_outside_fails_reach_fix_no_worse():
    b, n = plans()
    n["partition_types"]["T"]["relay_sites"]["u_r/q"] = [150.0, 150.0]       # inside u_a
    assert any("FAIL SEAT" in x and "in core" in x for x in run(b, n))
    b2, n2 = plans()
    n2["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]["root"] = [500.0, 10.0]
    assert any("outside outline" in x for x in run(b2, n2))
    b3, n3 = plans()
    b3["partition_types"]["T"]["clock"]["reach_fix_sinks"] = [[150.0, 150.0, 1.0]]
    n3["partition_types"]["T"]["clock"]["reach_fix_sinks"] = [[150.0, 150.0, 1.0]]
    assert run(b3, n3) == []                                                 # inherited reach_fix sink in a core is not a new defect
    n3["partition_types"]["T"]["clock"]["reach_fix_sinks"].append([160.0, 160.0, 1.0])
    assert any("reach_fix_sinks" in x for x in run(b3, n3))


def test_anchordry_findings_propagate():
    b, n = plans()
    f = LG.schema_test(b, n, ["T"], tap_check=ok_tap, anchor_check=lambda r, br, t: ["FAIL ANCHORDRY T: 4 anchored reset relay(s) at another depth"])
    assert f == ["FAIL ANCHORDRY T: 4 anchored reset relay(s) at another depth"]


def test_chain_order_and_plan_handover():
    a = argparse.Namespace(base="/b.json", types="T1,T2", out="/o.json", grow=185.76, ft_xcut=246.24, tree="/tree", seed=None,
                           extra_reg=True, no_core_place=False, work=None, dry=True)
    st = LG.steps(a, "/w")
    assert [s[0] for s in st] == ["grow", "core_place", "refresh", "chain_resite", "retap", "anchor"]
    assert st[0][2] == "/b.json" and st[1][2] == "/w/s1_grow.json"
    for prev, nxt in zip(st, st[1:]):
        if nxt[0] != "refresh":
            assert nxt[2] == prev[3]                                         # every step reads the previous step's output
    refresh = st[2][1]
    assert refresh[refresh.index("run") + 1] == "/w/s1_grow.json"            # deltas against the plan core_place started from
    assert "--extra-reg" in st[3][1] and "--obstacle-aware" in st[1][1] and "--repick" in st[5][1]
    a.grow, a.no_core_place, a.extra_reg = 0.0, True, False
    st2 = LG.steps(a, "/w")
    assert [s[0] for s in st2] == ["refresh", "chain_resite", "retap", "anchor"] and "--extra-reg" not in st2[1][1]
