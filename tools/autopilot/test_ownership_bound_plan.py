"""FLOW-FLEET-R1 11-22 (COORD class fix): OWNERS items come from the kit-wave bound plan, not the 10-25..10-29 die_plan.json on main."""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ownership as OWN  # noqa: E402


def test_bound_plans_follow_kit_wave_and_skip_parked(tmp_path):
    kv = tmp_path / "src_kv/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json"
    kv.parent.mkdir(parents=True)
    kv.write_text("{}")
    cfg = {"dies": {"qwen_kvsys": {"plan": str(kv), "src": str(tmp_path / "src_kv"), "event": "KV-D28"},
                    "hbm": {"plan": str(kv), "parked": {"owner": "COORD"}},
                    "s81": {"plan": str(tmp_path / "missing.json")},
                    "not_a_die": {"plan": str(kv)}}}
    b = OWN.bound_plans(cfg)
    assert list(b) == ["qwen_kvsys"] and b["qwen_kvsys"]["event"] == "KV-D28"
    # a new apply only rewrites kit_wave.json: the next tick reads the new plan
    cfg["dies"]["qwen_kvsys"]["event"] = "KV-D29"
    assert OWN.bound_plans(cfg)["qwen_kvsys"]["event"] == "KV-D29"


def test_bound_roots_and_relative_reads(tmp_path):
    src = tmp_path / "src"
    pd = src / "physical/die_plan/s81"
    (pd / "pins").mkdir(parents=True)
    (pd / "pins/c.json").write_text("PINS")
    plan = pd / "events/j7/plan.json"
    plan.parent.mkdir(parents=True)
    (plan.parent / "local.json.gz").write_bytes(gzip.compress(b"GZ"))
    roots = OWN.bound_roots("s81", {"plan": str(plan), "src": str(src)})
    assert roots == [str(pd), str(plan.parent)]
    assert OWN.read_local_rel(roots, "pins/c.json") == "PINS"
    assert OWN.read_local_rel(roots, "local.json") == "GZ"
    assert OWN.read_local_rel(roots, "none.json") is None


def test_plan_items_from_a_bound_plan_names_its_new_types():
    plan = {"partition_types": {"hd_lep0N": {"module": "ot_s81hd_lep0N", "count": 2}, "hd_ctl": {"module": "ot_s81hd_ctl", "count": 1}}}
    assert OWN._json_or_none(json.dumps(plan)) == plan
    assert OWN._json_or_none("{}") is None and OWN._json_or_none("not json") is None
    items = {i["item"] for i in OWN.plan_items("s81_head", plan)}
    assert {"hd_lep0N", "hd_ctl"} <= items


def test_autopilot_wiring():
    src = (Path(__file__).resolve().parent / "autopilot.py").read_text()
    assert 'bound = OWN.bound_plans(json.loads((AP_DIR / "kit_wave.json").read_text()))' in src
    assert "plan_src=plan_src" in src
