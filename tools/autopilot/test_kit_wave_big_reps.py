"""FLEET-WATCH-R4 11-21: over-400k families admit one representative, siblings held SIBLING-BIG until it passes; a named representative wins; INFRA rows inherit no older class hold."""
import kit_wave as KW


def cfg(flags=None, **kw):
    d = {"event": "E1", "_plan_flags": flags or {}, **kw}
    return {"dies": {"qc": d}}


def picks(*names):
    return [{"item": n, "kind": "type"} for n in names]


def test_big_family_holds_siblings():
    c = cfg({"slw_a_v1": "split"})
    ordered, held, meta = KW.family_plan(c, {"items": {}}, "qc", picks("slw_a_v1", "slw_a_v2", "slw_a_v3"))
    assert len(ordered) == 1 and len(held) == 2 and all(v.startswith("SIBLING-BIG") for v in held.values())


def test_small_family_unchanged():
    ordered, held, meta = KW.family_plan(cfg({}), {"items": {}}, "qc", picks("slw_a_v1", "slw_a_v2"))
    assert not held and len(ordered) == 2


def test_passed_rep_releases_siblings():
    st = {"items": {"qc|slw_a_v1|b1": {"die": "qc", "item": "slw_a_v1", "event": "E1", "status": "PASS"}}}
    ordered, held, meta = KW.family_plan(cfg({"slw_a_v1": "split"}), st, "qc", picks("slw_a_v2", "slw_a_v3"))
    assert not held


def test_running_rep_holds_all_picks():
    st = {"items": {"qc|slw_a_v1|b1": {"die": "qc", "item": "slw_a_v1", "event": "E1", "status": "RUNNING"}}}
    ordered, held, meta = KW.family_plan(cfg({"slw_a_v1": "split"}), st, "qc", picks("slw_a_v2", "slw_a_v3"))
    assert len(held) == 2 and not ordered


def test_named_representative_wins():
    c = cfg({"slw_a_v1": "split"}, family_reps={KW.family_of("qc", "slw_a_v1"): "slw_a_v3"})
    ordered, held, meta = KW.family_plan(c, {"items": {}}, "qc", picks("slw_a_v1", "slw_a_v2", "slw_a_v3"))
    assert [r["item"] for r in ordered] == ["slw_a_v3"] and set(held) == {"slw_a_v1", "slw_a_v2"}


def test_opt_out():
    c = cfg({"slw_a_v1": "split"}, big_reps_first=False)
    assert not KW.family_plan(c, {"items": {}}, "qc", picks("slw_a_v1", "slw_a_v2"))[1]


def test_infra_row_inherits_no_class_hold():
    c = {"dies": {"s81": {"event": "E1"}}}
    st = {"items": {"k": {"die": "s81", "item": "x", "event": "E1", "status": "RETRY-INFRA", "class": "INFRA", "updated": 0}},
          "flow_guard": {"open": {"K": {"state": "open"}}, "last": {"s81/x": "K"}}}
    out = KW.name_stuck_retry_infra(None, c, st, now=99999)
    assert "HELD" not in out and st["items"]["k"]["retry_stop"] != "HELD:K"
