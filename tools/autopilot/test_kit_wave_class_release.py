"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 C): fail keys are released only by the input parts their failure class depends on."""
import kit_wave as KW


def cfg(src="s"):
    return {"dies": {"kv": {"src_sha": src, "_src_overlay": "o", "_plan_sha": "p", "event": "e", "enabled": True,
                            "_prov_deps": {"w": ["m"]},
                            "prov_view_sources": {"m": [{"host": "h", "dir": "/d", "detailed_receipt": "r.json"}]}}}}


def setup(monkeypatch, stage, why, cls="PLAN"):
    state = {"v": "v1"}
    monkeypatch.setattr(KW, "view_sha", lambda host, p, **k: state["v"] if p.endswith("r.json") else "same")
    monkeypatch.setattr(KW, "stage_tools_digest", lambda root=None, group="", files=None: "t")
    st = {}
    KW.note_fail_key(cfg(), st, {"die": "kv", "item": "w", "block_sha": "b", "stage": stage}, cls, why)
    return st, state


def test_views_release_a_prov_views_failure(monkeypatch):
    st, state = setup(monkeypatch, "prov_views", "PROV_FAIL m: detailed abstract not accepted")
    assert KW.fail_key_gate(cfg(), st, "kv", "w", "b")[0]
    state["v"] = "v2"
    assert KW.fail_key_gate(cfg(), st, "kv", "w", "b")[2] == ["views"]


def test_views_release_a_bind_abstract_failure_only(monkeypatch):
    st, state = setup(monkeypatch, "bind", "abstract m.lef has no pin", "RTL")
    state["v"] = "v2"
    assert KW.fail_key_gate(cfg(), st, "kv", "w", "b")[2] == ["views"]
    st2, state2 = setup(monkeypatch, "bind", "unresolved module foo", "RTL")
    state2["v"] = "v2"
    assert KW.fail_key_gate(cfg(), st2, "kv", "w", "b")[0]          # a bind failure that names no view: views do not release it


def test_a_cell_cap_failure_is_not_released_by_views_but_by_the_design(monkeypatch):
    st, state = setup(monkeypatch, "cells", "773818 cells")
    state["v"] = "v2"
    bl, why, chg = KW.fail_key_gate(cfg(), st, "kv", "w", "b")
    assert bl and chg == []
    assert KW.fail_key_gate(cfg("s2"), st, "kv", "w", "b")[2] == ["src"]
    assert KW.fail_key_gate(cfg(), st, "kv", "w", "b2")[2] == ["block"]


def test_other_classes_ignore_views(monkeypatch):
    st, state = setup(monkeypatch, "place", "OT_FLOW placement diverged", "FLOW")
    state["v"] = "v2"
    assert KW.fail_key_gate(cfg(), st, "kv", "w", "b")[0]
    assert KW.release_parts({"stage": "unknown_stage", "why": ""}) is not None and "views" not in KW.release_parts({"stage": "x", "why": ""})
