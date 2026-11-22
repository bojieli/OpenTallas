"""FLOW-FLEET-R2 F1: representatives first in the launch order; the load cap uses the host's own factor."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402


def _cfg(**d):
    return {"dies": {"s81": dict({"event": "E1", "_reps_gate": True}, **d)}}


def _picks(*items):
    return [{"item": i, "kind": "type"} for i in items]


def test_siblings_wait_until_the_representative_has_an_attempt(monkeypatch):
    monkeypatch.setattr(KW, "family_of", lambda die, item: "fam")
    cfg = _cfg(family_reps={"fam": "a"})
    ordered, held, meta = KW.family_plan(cfg, {"items": {}}, "s81", _picks("a", "b", "c"))
    assert [r["item"] for r in ordered] == ["a"] and set(held) == {"b", "c"}
    assert all(h.startswith("SIBLING-WAIT fam") for h in held.values())


def test_siblings_launch_once_the_representative_has_a_record(monkeypatch):
    monkeypatch.setattr(KW, "family_of", lambda die, item: "fam")
    cfg = _cfg(family_reps={"fam": "a"})
    st = {"items": {"k": {"die": "s81", "item": "a", "event": "E1", "status": "RUNNING"}}}
    ordered, held, _ = KW.family_plan(cfg, st, "s81", _picks("a", "b", "c"))
    assert {r["item"] for r in ordered} == {"a", "b", "c"} and not held
    st["items"]["k"]["event"] = "E0"                    # a record of an older event does not count
    assert set(KW.family_plan(cfg, st, "s81", _picks("a", "b"))[1]) == {"b"}


def test_opt_out_keeps_the_old_order(monkeypatch):
    monkeypatch.setattr(KW, "family_of", lambda die, item: "fam")
    cfg = _cfg(family_reps={"fam": "a"}, reps_launch_first=False)
    ordered, held, _ = KW.family_plan(cfg, {"items": {}}, "s81", _picks("b", "a"))
    assert [r["item"] for r in ordered] == ["a", "b"] and not held


def test_over_load_cap_uses_the_hosts_own_factor():
    v = {"cores": 100, "load": 130.0}
    assert not KW.over_load_cap(dict(v, load_cap_factor=1.5)) and KW.over_load_cap(dict(v, load_cap_factor=1.2))
    assert KW.over_load_cap({"cores": 100, "load": 160.0}) and not KW.over_load_cap({"cores": 100, "load": 100.0})


def test_gate_is_off_unless_the_fleet_is_loaded(monkeypatch):
    monkeypatch.setattr(KW, "family_of", lambda die, item: "fam")
    cfg = _cfg(family_reps={"fam": "a"}, _reps_gate=False)
    assert not KW.family_plan(cfg, {"items": {}}, "s81", _picks("a", "b"))[1]


def test_fleet_loaded():
    hot, cold = {"cores": 96, "load": 200.0}, {"cores": 96, "load": 40.0}
    assert KW.fleet_loaded({"a": hot, "b": hot, "c": cold}) and not KW.fleet_loaded({"a": hot, "b": cold, "c": cold})
    assert not KW.fleet_loaded({}) and not KW.fleet_loaded({"a": None})
