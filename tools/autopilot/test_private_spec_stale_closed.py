"""FLOW-OPS-0900 (COORD 11-21): private-spec staleness check fails closed and finds the die in the hub config when the local one lacks it."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402

SP = {"die": "qwen_compute", "item": "cbn_q00", "hub": "intel2", "private": {"wave_env": {"OT_FLOW_TAG": "t1"}}}


def _cfg(dies):
    return json.dumps({"dies": dies})


def test_local_config_without_die_falls_back_to_hub(monkeypatch):
    monkeypatch.setattr(KW, "wave_gen_env", lambda c, d, i: {"OT_FLOW_TAG": c["dies"][d]["flow_tag"]})
    texts = {False: _cfg({"s81": {"flow_tag": "x"}}), True: _cfg({"qwen_compute": {"flow_tag": "t1"}})}
    assert KW.private_spec_stale(SP, loader=lambda hub_only: texts[hub_only]) == ""
    texts[True] = _cfg({"qwen_compute": {"flow_tag": "t2"}})
    assert "stale private spec" in KW.private_spec_stale(SP, loader=lambda hub_only: texts[hub_only])


def test_no_config_anywhere_refuses_instead_of_passing(monkeypatch):
    why = KW.private_spec_stale(SP, loader=lambda hub_only: "")
    assert why.startswith("private spec staleness not checked, refused") and "qwen_compute" in why

    def boom(c, d, i):
        raise KeyError(d)
    monkeypatch.setattr(KW, "wave_gen_env", boom)
    why = KW.private_spec_stale(SP, loader=lambda hub_only: _cfg({"qwen_compute": {}}))
    assert "refused" in why and "KeyError" in why


def test_loader_exception_and_missing_die_item_refuse():
    def bad(hub_only):
        raise OSError("ssh down")
    assert "refused" in KW.private_spec_stale(SP, loader=bad)
    assert "not checkable" in KW.private_spec_stale({"private": {}})
