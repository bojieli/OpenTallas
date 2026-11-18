"""WAVE-PILOT-FIX 11-18 (OWNER r703, FABLE-FLOW-0600 class A): the code default is stops_off ON for every die but hbm; stops_off false is the opt-out."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402


def test_default_is_on_for_every_die_but_hbm():
    assert FG.STOPS_OFF_DEFAULT is True
    for die in ("s81", "qwen_compute", "qwen_kvsys", "s81_head"):
        assert FG.stops_off_die({}, die)
    assert not FG.stops_off_die({}, "hbm")


def test_explicit_false_opts_out_and_exclude_overrides():
    assert not FG.stops_off_die({"stops_off": False}, "s81")
    assert FG.stops_off_die({"stops_off": True, "stops_off_exclude": []}, "hbm")


def test_a_config_without_the_key_holds_nothing():
    plan = "p" * 64
    c = {"dies": {"s81": {"event": "E1", "plan": "/x/E1.json", "plan_sha256": plan, "hold_event_items": {plan: ["a"]},
                          "hold_records": [{"id": "r", "plan_sha": plan, "reason": "x", "release": ["event_adopt:E2"], "keys": ["a"], "migrated": True}]}}}
    HR.compile_holds(c)
    assert (c["dies"]["s81"].get("hold_items") or {}) == {}
    c["stops_off"] = False
    HR.compile_holds(c)
    assert list(c["dies"]["s81"]["hold_items"]) == ["a"]


def test_retry_probe_follows_the_default():
    assert KW.retry_probe_defer({"dies": {"s81": {}}}, {"items": {}}, "s81", {"item": "x"}) == ""
