"""P-RUNTIME-MANIFEST (S81-INT-R3-PARAM 11-27): private-spec without --rt defaults to the event's tools_sha and refuses tree tools whose
schema.py is older than the plan."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW                                    # noqa: E402
import private_rt_default as PR                          # noqa: E402
from test_flow_privspec_r1 import D, I, wave_cfg, _no_plan_probe   # noqa: E402,F401

SHA = "b521092f9e17" + "0" * 8


def test_event_rt_reads_the_die_tools_sha():
    assert PR.event_rt({"dies": {"s81": {"tools_sha": "B521092F9E17"}}}, "s81") == "b521092f9e17"
    assert PR.event_rt({"dies": {"s81": {}}}, "s81") == "" and PR.event_rt({"dies": {"s81": {"tools_sha": "zz"}}}, "s81") == ""


def test_tree_tools_refusal_on_old_schema_positive_and_negative():
    old = lambda tree, plan: ["FAIL SCHEMA-UNKNOWN-KEY 'ft_polarity_local_group_by_type' x1 not in T/tools/die_plan/schema.py"]
    ok = lambda tree, plan: ["WARN SCHEMA-JSON-STALE x"]
    sp = {"src": "/t", "plan": "/p.json"}
    assert "RT-PIN refused" in PR.tree_tools_refusal(sp, None, check_schema=old)             # tree tools older than the plan
    assert PR.tree_tools_refusal(sp, None, check_schema=ok) == ""                            # tree schema fits
    assert PR.tree_tools_refusal(dict(sp, tools_sha="a" * 12), None, check_schema=old) == ""  # a declared rt is not the tree's tools
    assert PR.tree_tools_refusal(dict(sp, gen_tools_manifest_sha="h"), None, check_schema=old) == ""   # sealed gen_tools_pin tree
    assert PR.tree_tools_refusal(sp, None, exempt="sealed", check_schema=old) == ""         # explicit exemption


def test_private_spec_defaults_to_the_event_rt(monkeypatch, _no_plan_probe):
    c = wave_cfg()
    c["dies"][D]["tools_sha"] = SHA[:12]
    monkeypatch.setattr(KW, "rt_tools_fields", lambda cfg, die, root=None: {})                # the die runs the tree's own tools
    seen = []
    monkeypatch.setattr(KW, "private_rt_fields", lambda sha, root=None, rt_root=None: (seen.append(sha), {"tools_rt": "/rt/b521092f9e17", "tools_sha": SHA})[1])
    sp = KW.private_spec(c, D, I, "intel2")
    assert seen == [SHA[:12]] and sp["tools_sha"] == SHA and sp["tools_rt"] == "/rt/b521092f9e17"
    assert sp["private"]["rt"]["from"].startswith("event config tools_sha b521092f9e17")


def test_private_spec_explicit_rt_wins_and_missing_snapshot_keeps_tree_tools(monkeypatch, _no_plan_probe):
    c = wave_cfg()
    c["dies"][D]["tools_sha"] = SHA[:12]
    monkeypatch.setattr(KW, "rt_tools_fields", lambda cfg, die, root=None: {})
    def missing(sha, root=None, rt_root=None):
        raise ValueError("no rt snapshot here")
    monkeypatch.setattr(KW, "private_rt_fields", missing)
    sp = KW.private_spec(c, D, I, "intel2")
    assert not sp.get("tools_sha") and "no rt snapshot" in sp["private_rt_default_unavailable"]
