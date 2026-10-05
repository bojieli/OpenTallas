import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_allmeasured as A
from decode_critical_path import Graph


def fork():
    g = Graph()
    g.add("input", [], layer=0)
    g.add("left", ["input"], layer=0, issue=10e-6)
    g.add("right", ["input"], layer=0, issue=9e-6)
    g.add("token.return", ["left", "right"], layer=0, issue=1e-6)
    return g


def candidate(name="left", us=2, **extra):
    return dict(lever="test", exact=True, nodes={name:dict(us=us, source="measured test", **extra)})


def test_critical_path_switch_is_not_a_sum_of_savings():
    g = fork()
    assert g.solve()["token.return"] == pytest.approx(11e-6)
    A.apply_candidate(A.Patcher(g), candidate())
    assert g.solve()["token.return"] == pytest.approx(10e-6)
    assert g.path("token.return") == ["input", "right", "token.return"]


@pytest.mark.parametrize("record", [candidate("missing"), candidate(us=float("nan")),
    candidate(us=-1), candidate(us=0), dict(lever="test",exact=False,nodes={})])
def test_missing_negative_or_unmeasured_cost_refused(record):
    with pytest.raises(ValueError):
        A.apply_candidate(A.Patcher(fork()), record)


def test_clock_kind_is_explicit_and_does_not_change_the_lever_record():
    record=candidate(kind="fused_fast")
    before=json.dumps(record,sort_keys=True)
    g=fork()
    A.apply_candidate(A.Patcher(g),record)
    assert g.nodes["left"]["kind"] == "fused_fast"
    assert json.dumps(record,sort_keys=True) == before


def test_no_zero_rate_for_missing_SU_and_no_preliminary_adoption():
    d=json.loads((ROOT/"results/rtl/dsrom_recovery_20261004/decision_gate/model.json").read_text())
    assert d["scenarios"]["baseline"]["conditional_cost"]["AR_us"] == 620.078
    assert d["scenarios"]["baseline"]["conditional_cost"]["MTP"]["MTP_tok_s"] == 4462.1
    assert d["scenarios"]["field_only"]["conditional_cost"]["AR_us"] == 514.638
    for name in ("SU_only","both"):
        assert d["scenarios"][name]["conditional_cost"] is None
        assert d["scenarios"][name]["composition_complete"] is False
    assert d["field"]["isolated_overlap_gain_us"] is None
    assert d["hardware_build_admitted"] is False
    assert all(v["adoption"] is False for v in d["scenarios"].values())


def test_matched_snapshot_pins_and_HBM_gap_are_consistent():
    import hashlib
    d=json.loads((ROOT/"results/rtl/dsrom_recovery_20261004/decision_gate/model.json").read_text())
    for path, expected in d["inputs"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, path
    c=d["comparison"]
    assert c["after_preliminary_field_additional_exposed_us"] == pytest.approx(54.59291558172703)
    assert c["HBM_exposed_expert_weight_fetch_us"] == pytest.approx(40*.13031)
    assert d["bounds_and_next"]["top_follow_on"]["actual_gain_us"] is None
    assert d["bounds_and_next"]["top_follow_on"]["RTL_admitted"] is False


def test_cold_norm_boundaries_are_not_warmed_or_all_layer_credit():
    d=json.loads((ROOT/"results/rtl/dsrom_recovery_20261004/decision_gate/model.json").read_text())
    n=d["measured_norm_subset"]
    assert n["gain_cycles"] == [6,7,8,9,10]
    assert (n["go_cycle"], n["final_registered_landing_cycle"]) == (16,294)
    assert n["cold_cycles"] == 288
    assert n["cold_us"] == pytest.approx(.240)
    assert n["warm_cycles"] == 278
    assert n["finite_consumer_credits"] is None
    assert n["physical_SS_FF"] is None
    assert d["scenarios"]["SU_only"]["conditional_cost"] is None


def test_selected_HCPOST_reject_not_alternative_lane_transfer():
    d=json.loads((ROOT/"results/rtl/dsrom_recovery_20261004/decision_gate/model.json").read_text())
    p=d["selected_SU_physical"]
    assert p["verdict"] == "REJECT_SS"
    assert p["SS_setup_ps"] == -52.47
    assert p["FF_hold_ps"] == 5.70
    assert p["alternative"]["qualifies_selected_M5A4_or_full_NG256"] is False
    for name in ("SU_only", "both"):
        assert d["scenarios"][name]["verdict"] == "REJECT_SELECTED_HCPOST_SS"
        assert d["scenarios"][name]["conditional_cost"] is None
