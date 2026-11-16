"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1800): the class breaker counts INFRA (it never opened through 56 S81 + 24 KV same-class fails because
INFRA was excluded), and an INFRA relaunch is keyed on (tool sha, src sha, plan sha, error class): the same key failing again stops."""
import re
import time
import flow_guard as FG
import kit_wave as KW

S81 = ("INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: sdc_lint.SdcLintError: type serdes__t%d: "
       "constraint.sdc fails sdc_lint (43): clocks: clock port clk window early -24.6 / late -24.6 ps")
KV = ("INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @kit_rtl: AttributeError: module 'reset_tree' "
      "has no attribute 'pin_root_copies'")


def replay(rows, skip_infra):
    st = {}
    for t, die, item, cls, why in rows:
        if skip_infra and cls == "INFRA":
            continue
        FG.record_fail(st, die, item, cls, why, now=t, legacy=False, stage=FG.fail_stage(why))
    return st


def test_replay_of_the_15_45_17_45_window_opens_the_infra_classes_only_when_infra_counts():
    t0 = 1794790000.0
    rows = [(t0 + i * 60, "s81", f"serdes__t{i}", "INFRA", S81 % i) for i in range(56)]
    rows += [(t0 + i * 90, "qwen_kvsys", f"kv3_sys_{i}", "INFRA", KV) for i in range(24)]
    assert FG.fail_stage(S81 % 1) == "gen" and FG.fail_stage(KV) == "kit_rtl"
    assert replay(rows, skip_infra=True).get("flow_guard", {}).get("open", {}) == {}            # the 15:54 merge: INFRA excluded -> 0 openings
    opened = replay(rows, skip_infra=False)["flow_guard"]["open"]
    assert len(opened) == 2 and any(k.startswith("CLASS s81|gen|") for k in opened) and any(k.startswith("CLASS qwen_kvsys|kit_rtl|") for k in opened)


def test_kit_wave_records_infra_but_not_a_host_shortage():
    src = open(KW.__file__).read()
    assert 'if cls != "INFRA":\n                FG.record_fail' not in src
    assert "NO_HOST.search(why or \"\") or _TRANSIENT_INFRA.search(why or \"\")" in src


def cfg(src="s1"):
    return {"dies": {"d": {"src_sha": src, "plan_sha": "p"}}}


def test_infra_key_changes_with_tool_src_plan_and_error_class(monkeypatch):
    rec = {"die": "d", "item": "i"}
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "t1")
    a = KW.infra_key(cfg(), rec, "INFRA", S81 % 1)
    assert a == KW.infra_key(cfg(), rec, "INFRA", S81 % 7)                      # same error class, other numbers: same key
    assert a != KW.infra_key(cfg("s2"), rec, "INFRA", S81 % 1)                  # src changed
    assert a != KW.infra_key(cfg(), dict(rec, plan_sha="p2"), "INFRA", S81 % 1)  # plan changed
    assert a != KW.infra_key(cfg(), rec, "INFRA", KV)                           # other error class
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "t2")
    assert a == KW.infra_key(cfg(), rec, "INFRA", S81 % 1)                      # the hub runtime digest is NOT in the key (FABLE-FLOW-2000 a)


def test_second_failure_of_the_same_key_is_the_repeat():
    st, rec = {}, {"die": "d", "item": "i"}
    assert KW.infra_repeat(st, rec, "k1") is False
    assert KW.infra_repeat(st, rec, "k2") is False
    assert KW.infra_repeat(st, rec, "k1") is True
    assert KW.infra_repeat(st, {"die": "d", "item": "other"}, "k1") is False     # per item


def test_tool_vs_design_reclass():
    assert KW.TOOL_INFRA_RE.search("python exception / plan-schema refusal in the kit tool: tool or source skew")
    assert not KW.TOOL_INFRA_RE.search("INFRA host input gap on epyc7")
