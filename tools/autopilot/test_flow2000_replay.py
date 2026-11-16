"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-2000 a/b/c): replay of the 11-15 log lines.
(a) the key reads the kit's own spec + normalised error, on every FAIL;  (b) a class the preflight does not test releases only when the die's
inputs change;  (c) one error is one class key (item names, numbers, paths stripped)."""
import json
import kit_wave as KW
import flow_guard as FG

STALE = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: STALE-CORE-VIEW ot_s%dcfg%d_seq_bfp: lib /srv/opentallas-scratch2/claude/x%d/y.lib sha %s != sha 12ab"
SDC = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: sdc_lint.SdcLintError: type slice_station__t%d: constraint.sdc fails sdc_lint (%d): clocks"
ROAM = "FLOW: unclassified failure @kit_rtl (see log): KW_ROAM kit_rtl: ran on %s, outputs copied back to epyc%d"
BIND = "FLOW: unclassified failure @kit_rtl (see log): bind.py: error: unrecognized arguments: --src-tree /srv/opentallas-scratch2/claude/k%d/src"
ATTR = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'gen_phys' has no attribute 'tap_%d'"


def test_c_one_error_is_one_key():
    ks = {FG.norm_class("INFRA", STALE % (i, i + 3, i, "ab%dcdef0123" % i)) for i in range(12)}
    assert len(ks) == 1
    assert len({FG.norm_class("INFRA", SDC % (i, 40 + i)) for i in range(12)}) == 1
    assert len({FG.norm_class("FLOW", ROAM % (h, i)) for h in ("epyc7", "intel1", "epyc9") for i in range(9)}) == 1
    assert len({FG.norm_class("FLOW", BIND % i) for i in range(9)}) == 1
    assert len({FG.norm_class("INFRA", ATTR % i) for i in range(9)}) == 1
    # different errors stay different
    assert len({FG.norm_class("INFRA", STALE % (1, 1, 1, "aabbccdd0011")), FG.norm_class("INFRA", SDC % (1, 1)), FG.norm_class("FLOW", BIND % 1),
                FG.norm_class("FLOW", ROAM % ("epyc7", 1))}) == 4
    assert FG.norm_class("FLOW", ROAM % ("epyc7", 1)).endswith("no error line (progress text only)")
    assert FG.pf_kind(FG.norm_class("INFRA", ATTR % 1)) == "skew"                   # the preflight kinds still read the key


def cfg(src="s1", plan="p"):
    return {"dies": {"d": {"src_sha": src, "plan_sha": plan, "event": "e"}}}


def test_a_key_reads_the_kits_own_spec_and_is_checked_on_every_fail(tmp_path, monkeypatch):
    k = tmp_path / "a1"
    k.mkdir()
    (k / "spec.json").write_text(json.dumps({"src_sha": "kitsrc", "src_overlay": "ov1"}))
    rec = {"die": "d", "item": "i", "dir": str(k), "block_sha": "b1"}
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "hub-1")
    a = KW.infra_key(cfg(), rec, "INFRA", ATTR % 1)
    monkeypatch.setattr(KW, "rt_tools_digest", lambda: "hub-2")                       # the hub runtime changed 7 times: no new key
    assert KW.infra_key(cfg(), rec, "INFRA", ATTR % 5) == a
    (k / "spec.json").write_text(json.dumps({"src_sha": "kitsrc2", "src_overlay": "ov1"}))      # the kit's own src changed: new key
    assert KW.infra_key(cfg(), rec, "INFRA", ATTR % 1) != a
    src = open(KW.__file__).read()
    assert 'cls in ("INFRA", "FLOW") and rec.get("status") in ("RETRY-INFRA", "FAIL")' in src          # read on every FAIL, not only RETRY-INFRA
    st = {}
    assert KW.infra_repeat(st, rec, a) is False and KW.infra_repeat(st, rec, a) is True


def test_b_breaker_releases_only_when_the_dies_inputs_change():
    st = {}
    inp1 = KW.breaker_inputs(cfg(), "d")
    for i in range(10):
        FG.record_fail(st, "d", "it%d" % i, "FLOW", BIND % i, now=1000 + i, legacy=False, stage="kit_rtl", inp=inp1)
    key = FG.held_key(st, "d", "it3")
    assert key.startswith("CLASS d|kit_rtl|")
    assert FG.release_by_preflight(st, {key: [True, True]}, now=2000) == []        # a preflight that does not test this class releases nothing
    assert FG.breaker_tick(st, now=1000 + 10 * FG.BREAKER_COOLDOWN_S, inputs={"d": inp1}) == []     # no cooldown release any more
    assert FG.held_key(st, "d", "it3") == key
    inp2 = KW.breaker_inputs(cfg(src="s2"), "d")
    assert inp2 != inp1
    rel = FG.breaker_tick(st, now=5000, inputs={"d": inp2})
    assert len(rel) == 1 and FG.held_key(st, "d", "it3") == ""


def test_b_replay_19_15_release_would_not_have_happened():
    """the class opened at 18:5x; at 19:15 the old code released it (cooldown / unrelated preflight) and 15 launches failed again"""
    st = {}
    inp = KW.breaker_inputs(cfg(), "d")
    for i in range(10):
        FG.record_fail(st, "d", "q%d" % i, "FLOW", ROAM % ("epyc7", i), now=1000 + i * 60, legacy=False, stage="kit_rtl", inp=inp)
    assert FG.held_key(st, "d", "q0")
    assert FG.breaker_tick(st, now=1000 + 3600, inputs={"d": inp}) == []
    assert FG.held_key(st, "d", "q0")
