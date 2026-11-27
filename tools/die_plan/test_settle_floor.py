"""START-SETTLE / P-STALE-TABLE (QC-R3-TREERTL 11-27): root_settle_cycles is derived from the bound plan's collector ready bound."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clock_landing_plan as CLP  # noqa: E402
import plan_gate_pre as G  # noqa: E402


def _side(settle, ready, raw=464):
    return {"count_aligned": {"root_settle_cycles": settle} if settle is not None else {"root": "r0"},
            "collector": {"root": "r", "boot_budget": {"raw_reset_release_max_cycles": raw, "ring_train_max_cycles": 21,
                                                        "ready_at_glue_max_cycles": ready}}}


def test_settle_raised_to_plan_ready_bound():
    s = _side(64, 1734)
    assert CLP.settle_floor(s) == 1734 and s["count_aligned"]["root_settle_cycles"] == 1734


def test_settle_default_and_larger_kept():
    assert CLP.settle_floor(_side(None, 300)) == 300
    assert CLP.settle_floor(_side(64, 20)) == 64            # 64 is only a floor
    assert CLP.settle_floor(_side(2000, 1734)) == 2000     # a larger recorded settle is never lowered


def test_settle_none_without_table_or_budget():
    assert CLP.settle_floor({"collector": {"boot_budget": {}}}) is None
    assert CLP.settle_floor({"count_aligned": {"root_settle_cycles": 64}}) is None


def test_derived_settle_passes_pre_check(tmp_path):
    import json
    ss = {"count_aligned": {"root_settle_cycles": 64},
          "collector": {"root": "r", "boot_budget": {"ring_train_max_cycles": 21, "raw_reset_release_max_cycles": 464,
                                                      "local_registered_depths": {"r": 21, "a": 5}},
                        "edges": [{"src": "a", "dst": "r", "seam": True, "boot_transport_extra_cycles": 3}]}}
    ss["collector"]["boot_budget"]["ready_at_glue_max_cycles"] = G.start_settle_bound(ss, 464)
    sc = tmp_path / "sc.json"
    sc.write_text(json.dumps(ss))
    assert any(w.startswith("FAIL START-SETTLE") for w in G.check_startsettle(str(tmp_path), "u", str(sc), None, max_release=464))
    CLP.settle_floor(ss)
    sc.write_text(json.dumps(ss))
    assert G.check_startsettle(str(tmp_path), "u", str(sc), None, max_release=464) == []
