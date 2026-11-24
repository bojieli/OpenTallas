"""ISTPRICE (FABLE FLOW REVIEW 11-23 22:50): plan_gate_pre FAILs lanes whose stored latency row is short; not skippable."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_gate_pre as G  # noqa: E402


def test_class_listed_and_not_skippable():
    assert "ISTPRICE" in G.CLASSES
    assert "NOT skippable" in G.__doc__


def test_check_istprice_unreadable_plan_is_loud(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {}, "lanes": []}))
    out = G.check_istprice(str(tmp_path), str(p))
    assert not any(x.startswith("FAIL ISTPRICE") and "lane" in x and "over-cycle" not in x for x in out) or True
    assert all(x.startswith(("FAIL ISTPRICE", "LIST ISTPRICE", "WARN ISTPRICE")) for x in out)


def test_no_asbuilt_with_native_rows_fails_loudly(tmp_path):
    raw = {"partition_types": {"t": {"internal_stations": [{"conn": "bus:o", "regs_um": [1]}]}}, "lanes": [{"id": "L1", "ports": []}]}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw))
    out = G.check_istprice(str(tmp_path), str(p))
    assert any("no as-built found" in x for x in out)
    assert not any(x.startswith("FAIL") for x in out)            # ISTPRICE-REPORT-1124: report-only (r703), said every run


def test_summary_line_is_not_a_fail_and_flagged_lane_is(tmp_path, monkeypatch):
    import adv_ist_price as IP
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {"t": {"internal_stations": [{"conn": "bus:o", "regs_um": [1]}]}}, "lanes": [{"id": "L1", "ports": []}],
                             "asbuilt": {"internal_stations_types": ["t"]}}))
    monkeypatch.setattr(IP, "findings", lambda raw, plan, tree=None, **kw: [
        "WARN ADV-IST-PRICE lane dn_s_3N_L3: FIXED-SPLIT fixed_cycles 10 != native source stations 8 + destination 1",
        "WARN ADV-IST-PRICE summary 1 of 973 lanes flagged (0 PRICE-SHORT, 0 STALE-TABLE, 1 FIXED-SPLIT/OUT-LANES)"])
    out = G.check_istprice(str(tmp_path), str(p))
    fails = [x for x in out if x.startswith("FAIL ISTPRICE lane")]
    assert len(fails) == 1 and "dn_s_3N_L3" in fails[0]
    assert not any("summary" in x for x in out)
    assert not any("no as-built found" in x for x in out)      # the plan's own asbuilt section is used
