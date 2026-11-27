"""pytest: ADV-PUB-STALE (published collector_tree vs the solved reset tree; C-RST-RELAY-REACH / P-RESET-PUB-STALE)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_pub_stale as A  # noqa: E402


def tree(xy_t0=(110.0, 120.0), taps=2, depth=2):
    return {"root": [0.0, 0.0], "depth": depth, "n_clock_taps": taps, "relays": [
        {"q": "rst_n_a", "xy": [100.0, 100.0], "d": "rst_root_n", "depth": 1},
        {"q": "rst_n_t0", "xy": list(xy_t0), "d": "rst_n_a", "depth": 2},
        {"q": "rst_n_t1", "xy": [1510.0, 120.0], "d": "rst_n_a", "depth": 2}]}


CH = [{"index": 0, "xy_um": [115.0, 125.0], "node": "rst_n_t0"}]


def plan(pub, ch=CH):
    return {"partition_types": {"t": {"clock": {"landing_contract": {"collector_tree": pub, "collector_children": ch}}}}}


def test_identical_publication_is_clean():
    j = A.judge_type(tree(), tree(), CH)
    assert not A.stale(j) and j["relays_same"] == 3 and j["reach"] == []


def test_moved_relay_with_far_collector_ref_is_flagged():
    j = A.judge_type(tree(), tree(xy_t0=(1400.0, 900.0), taps=3), CH)
    assert A.stale(j) and j["relays_same"] == 2 and j["taps_pub"] != j["taps_solved"]
    assert j["reach"] and j["reach"][0][1] == "rst_n_t0" and j["reach"][0][2] > 405


def test_depth_change_is_called_out():
    j = A.judge_type(tree(), tree(depth=3), CH)
    ls = A.findings(plan(tree()), "p", None, solved={"t": tree(depth=3)})
    assert A.stale(j) and "DEPTH 2 -> 3" in ls[0]


def test_missing_node_in_solved_tree():
    s = tree(); s["relays"] = [r for r in s["relays"] if r["q"] != "rst_n_t0"]
    j = A.judge_type(tree(), s, CH)
    assert j["reach"] == [("children[0]", "rst_n_t0", None)]


def test_findings_summary_unsolvable_and_never_raises():
    ls = A.findings(plan(tree()), "p", None, solved={"t": tree(xy_t0=(1400.0, 900.0))})
    assert ls[0].startswith("WARN ADV-PUB-STALE t: published tree") and "summary 1 of 1" in ls[-1]
    ls = A.findings(plan(tree()), "p", None, solved={"t": RuntimeError("boom")})
    assert "not solvable" in ls[0] and "NOT checked" in ls[0]
    assert A.findings(None, "p", None)[0].startswith("WARN ADV-PUB-STALE summary 0 of 0")
    assert A.findings({"partition_types": 5}, "p", None)[0].startswith("WARN ADV-PUB-STALE not checked")


def test_budget_zero_reports_not_checked_not_clean():
    ls = A.findings(plan(tree()), "p", None, solved={})
    assert "1 not checked (budget)" in ls[-1]
