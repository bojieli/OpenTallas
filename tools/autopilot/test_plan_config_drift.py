import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR
import kit_wave as KW

NEW = ["col_h9_r2__t1", "col_h10_r2__t1", "ser__t1"]
OLD = "col_h9_r2__t1__cl774acf45__pv858fb2ba"


class AP:
    def __init__(self):
        self.logs, self.q = [], []

    def log(self, m):
        self.logs.append(m)

    def coord_append(self, f, t):
        self.q.append(t)


def cfg_for(**kw):
    d = {"enabled": True, "gen_host": "h", "plan": "/p/plan.json", "event": "e", "src": "/t/src",
         "only_items": [OLD, "ser__t1"], "item_env": {OLD: {"A": "1"}}, "hold_items": {OLD + "__*": "x"}}
    d.update(kw)
    return {"dies": {"s81": d}}


def state():
    return {"plans": {"h:/p/plan.json|e": {"types": NEW}}}


def test_drift_lists_plan_items_outside_only_items_and_dead_config_keys():
    dr = KW.plan_config_drift(cfg_for()["dies"]["s81"], NEW)
    assert dr["only"] == ["col_h10_r2__t1", "col_h9_r2__t1"]
    assert dr["only_unmatched"] == [OLD] and dr["env"] == [OLD] and dr["hold"] == [OLD + "__*"]
    assert KW.plan_config_drift({"only_items": ["col_h9_r2__t1", "col_h10_r2__t1", "ser__t1"]}, NEW) == {}
    assert KW.plan_config_drift({"only_items": []}, []) == {}            # plan unknown: no verdict


def test_step_posts_one_alert_per_change_and_names_are_published_for_the_audit():
    ap, st, cfg = AP(), state(), cfg_for()
    KW.plan_drift_step(ap, cfg, st)
    KW.plan_drift_step(ap, cfg, st)
    assert len(ap.q) == 1 and "col_h9_r2__t1" in ap.q[0] and "ALERT [PLAN-CONFIG-DRIFT" in ap.q[0]
    assert cfg["_plan_item_names"]["s81"] == NEW
    cfg["dies"]["s81"]["src"] = "/t/src2"                              # a tree switch changes the signature: one more alert
    KW.plan_drift_step(ap, cfg, st)
    assert len(ap.q) == 2
    cfg["dies"]["s81"].update(only_items=NEW, item_env={}, hold_items={})   # fixed: silent, state cleared
    KW.plan_drift_step(ap, cfg, st)
    assert len(ap.q) == 2 and not st["plan_drift_sig"]


def test_family_extension_is_opt_in_and_in_memory():
    c = cfg_for()
    KW.plan_drift_step(AP(), c, state())
    assert c["dies"]["s81"]["only_items"] == [OLD, "ser__t1"]
    c = cfg_for(only_items_extend_families=True)
    ap = AP()
    KW.plan_drift_step(ap, c, state())
    assert set(c["dies"]["s81"]["only_items"]) == {OLD, "ser__t1", "col_h9_r2__t1"}      # same family col_h9_r2; col_h10_r2 is not listed
    assert any("ONLY-ITEMS-EXTEND" in m for m in ap.logs)
    assert "col_h10_r2__t1" in ap.q[0] and "col_h9_r2__t1" not in ap.q[0].split("outside only_items")[1].split(";")[0]


def test_hold_zero_match_counts_against_the_current_plan_not_state_rows():
    plan = "p" * 64
    c = {"dies": {"s81": {"event": "e", "plan_sha256": plan, "hold_event_items": {plan: [OLD]},
                          "hold_records": [{"id": "old", "plan_sha": plan, "reason": "r", "release": ["result:L:t"], "owner": "L", "cause": "c", "items": [OLD]},
                                           {"id": "new", "plan_sha": plan, "reason": "r", "release": ["result:L:t"], "owner": "L", "cause": "c", "items": ["col_h9_r2__t1"]}]}},
         "_item_names": {"s81": [OLD]}, "_plan_item_names": {"s81": NEW}}
    HR.compile_holds(c)
    zero = {f["id"] for f in HR.audit(c) if f["code"] == "HOLD-ZERO-MATCH"}
    assert zero == {"old"}                                             # the key naming only the old suffixed variant matches nothing in the plan
    c.pop("_plan_item_names")
    HR.compile_holds(c)
    assert not [f for f in HR.audit(c) if f["code"] == "HOLD-ZERO-MATCH"]  # plan names unknown: old behavior


def test_env_drift_uses_the_item_env_entry_rule():
    """BUILD-SETTINGS-AUDIT-1900: a base item_env key whose only plan items are its __pv variants is reported (it applies to none of
    them); a family glob that covers the variants is not, and the variant then inherits the parent env through it"""
    d = {"item_env": {"col_a__t1": {"OT_GEN_M8_GRANT": "1"}, "col_b__t1": {"OT_GEN_M8_GRANT": "1"},
                      "col_b__t1__pv*": {"OT_GEN_M8_GRANT": "1"}}}
    names = ["col_a__t1__pv1", "col_b__t1__pv2"]
    dr = KW.plan_config_drift(d, names)
    assert dr["env"] == ["col_a__t1", "col_b__t1"]
    assert KW.item_env_entry(d, "col_b__t1__pv2") == {"OT_GEN_M8_GRANT": "1"}
    assert KW.item_env_entry(d, "col_a__t1__pv1") == {}
    assert KW.env_key_applies("col_b__t1__pv*", "col_b__t1__pv2") and not KW.env_key_applies("col_a__t1", "col_a__t1__pv1")
