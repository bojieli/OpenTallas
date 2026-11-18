"""FLOW-HEALTH-1 11-15 (FABLE-FLOWCLASS-RETRY-2030 P2 P3 P4, COORD r220): one fail key checked at the launch gate on every path, relaunch on fix,
family-wide breaker released by a probe launch, class keys without type names; replay of the 11-15 log."""
import collections
import os
import re
import time

import flow_guard as FG
import kit_wave as KW

ATTR = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'gen_phys' has no attribute 'tap_%d'"
SDC = "INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: sdc_lint.SdcLintError: type slice_station__t%d__cl%x: constraint.sdc fails (43)"


def cfg(src="s1", overlay="o1", plan="p1"):
    return {"dies": {"s81": {"src_sha": src, "_src_overlay": overlay, "_plan_sha": plan, "event": "e", "enabled": True}}}


def rec_of(item, block="b1"):
    return {"die": "s81", "item": item, "block_sha": block, "stage": "gen"}


def test_p2_same_key_blocks_every_path_and_a_changed_digest_relaunches_on_fix():
    st = {}
    KW.note_fail_key(cfg(), st, rec_of("slice_station__t17"), "INFRA", SDC % (17, 0xabc123))
    # the same inputs: blocked, whatever path asks (one function)
    bl, why, chg = KW.fail_key_gate(cfg(), st, "s81", "slice_station__t17", "b1")
    assert bl and "same fail key" in why and chg == []
    # each input that can fix the cause releases it, and says which
    for kw, name in ((dict(src="s2"), "src"), (dict(overlay="o2"), "overlay"), ):
        bl, why, chg = KW.fail_key_gate(cfg(**kw), st, "s81", "slice_station__t17", "b1")
        assert not bl and chg == [name]
    bl, why, chg = KW.fail_key_gate(cfg(), st, "s81", "slice_station__t17", "b2")        # new plan block
    assert not bl and chg == ["block"]
    # no stored key (first launch): free
    assert KW.fail_key_gate(cfg(), st, "s81", "other_item", "b1") == (False, "", [])


def test_p2_host_and_stopped_fails_never_make_a_key():
    st = {}
    for why in ("INFRA: infra (unit stopped from outside / disk floor wait: no design result) @gen: x",
                "INFRA: infra (ot-run: interrupted (signal 15 from pid 123)) @gen: x", "INFRA: no host qualifies: epyc2: scratch disk 35 GB free",
                "INFRA: copy-back failed @place: rsync"):
        assert KW.note_fail_key(cfg(), st, rec_of("a"), "INFRA", why) is None
    assert st.get("fail_keys") in (None, {})


def test_p2_repeat_counts_and_the_key_ignores_type_names():
    st = {}
    k1 = KW.note_fail_key(cfg(), st, rec_of("slice_station__t17"), "INFRA", SDC % (17, 1))
    k2 = KW.note_fail_key(cfg(), st, rec_of("slice_station__t17"), "INFRA", SDC % (18, 2))        # other type name, same error
    assert k1 == k2 and st["fail_keys"]["s81|slice_station__t17"]["n"] == 2


def test_launch_goes_through_the_gate(monkeypatch):
    class AP:
        logs = []
        log = staticmethod(lambda m: AP.logs.append(m))
    monkeypatch.setattr(KW, "scheduler_current", lambda ap: True)
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a, **k: False, raising=False)
    st = {"items": {}}
    c = cfg()
    KW.note_fail_key(c, st, rec_of("slice_station__t17"), "INFRA", SDC % (17, 1))
    assert KW.launch(AP, c, st, "s81", {"item": "slice_station__t17", "block_sha": "b1"}, "hub") is None
    assert any("LAUNCH-REFUSED" in m and "same fail key" in m for m in AP.logs)


def test_p3_rearm_digest_is_the_stage_closure_not_the_whole_tools_tree():
    src = open(KW.__file__).read()
    assert "cur = stage_tools_digest()" in src and "cur = rt_tools_digest()\n    seen = led.get(k)" not in src


def test_p4_family_breaker_holds_unfailed_siblings_and_releases_by_probe():
    st = {}
    inp1 = "digest-1"
    for i in range(10):
        FG.record_fail(st, "s81", "slice_station__t%d" % i, "INFRA", SDC % (i, i), now=1000 + i * 60, legacy=False, stage="gen", inp=inp1)
    key = FG.held_key(st, "s81", "slice_station__t3")
    assert key.startswith("CLASS s81|gen|")
    assert FG.held_key(st, "s81", "slice_station__t99")                             # same family, never failed: held too
    assert FG.held_key(st, "s81", "serdes__t4") == ""                               # another family: free
    assert FG.held_key(st, "kv", "slice_station__t3") == ""                         # another die: free
    # no time or text release
    assert FG.breaker_tick(st, now=1000 + 99999, inputs={"s81": inp1}) == []
    assert FG.release_by_preflight(st, {key: [True]}, now=5000) == []
    # inputs change: probe window, ONE item of the family may launch
    rel = FG.breaker_tick(st, now=6000, inputs={"s81": "digest-2"})
    assert rel and "PROBE" in rel[0][1]
    assert FG.held_key(st, "s81", "slice_station__t7", claim=True) == ""             # probe 1 of 3 (WAVE-PILOT-FIX: three probes per class)
    assert FG.held_key(st, "s81", "slice_station__t8", claim=True) == ""             # probe 2
    assert FG.held_key(st, "s81", "slice_station__t5", claim=True) == ""             # probe 3
    assert FG.held_key(st, "s81", "serdes__t4") == ""                                # another family: free
    assert FG.held_key(st, "s81", "slice_station__t6", claim=True)                   # the rest of the family waits
    # every claimed probe fails again at the same stage: shut until the inputs change again
    FG.probe_result(st, "s81", "slice_station__t7", "gen", passed=False)
    out = FG.probe_result(st, "s81", "slice_station__t8", "gen", passed=False)           # the second failed probe shuts the class (WAVE-PILOT-FIX 11-18)
    assert out and FG.held_key(st, "s81", "slice_station__t6")
    assert FG.breaker_tick(st, now=7000, inputs={"s81": "digest-2"}) == []           # same inputs as the failed probe: still shut
    FG.breaker_tick(st, now=8000, inputs={"s81": "digest-3"})
    assert FG.held_key(st, "s81", "slice_station__t9", claim=True) == ""
    out = FG.probe_result(st, "s81", "slice_station__t9", "place", passed=True)       # got past gen
    assert any("released" in w for _, w in out)
    assert FG.held_key(st, "s81", "slice_station__t8") == ""                         # the family is open
    assert FG.held_key(st, "s81", "slice_station__t3") == ""
    assert not st["flow_guard"]["open"]                                              # no family left: the class is closed


def test_p4_stage_rank_orders_gen_before_place():
    assert FG.stage_rank("gen") < FG.stage_rank("place") < FG.stage_rank("route") < FG.stage_rank("unknown-stage")
    assert FG.family_of("slice_station__t17") == "slice_station" and FG.family_of("cbn_q01__clab6e67f2") == "cbn_q01"


LOG = os.path.expanduser("~/coord/autopilot/log.txt")


def test_replay_of_the_day_blocks_the_repeats():
    """replay of the 11-15 KIT-WAVE LAUNCH / FAIL / ENQUEUE lines: with inputs unchanged between attempts (the log shows no plan or src change for these rows)
    the key gate refuses every launch whose previous non-HOST fail has the same key; HOST fails and passes stay justified"""
    if not os.path.exists(LOG):
        return
    pat = re.compile(r"AUTOPILOT: KIT-WAVE (LAUNCH|FAIL|ENQUEUE) (\S+?)/(\S+)(?: (\S+):)? ?(.*)$")
    last = {}
    launches = blocked = justified = host = prevfail = 0
    seen = set()
    with open(LOG, errors="replace") as f:
        for ln in f:
            if not ln.startswith("2026-11-15 "):
                continue
            m = pat.search(ln.rstrip("\n"))
            if not m:
                continue
            kind, die, item, cls, why = m.groups()
            k = (die, item)
            if kind == "LAUNCH":
                if k in seen:
                    launches += 1
                    prev = last.get(k)
                    if prev is None or prev[0] == "pass" or prev[0] == "host":
                        justified += 1
                    else:
                        prevfail += 1
                seen.add(k)
                last.setdefault(k, None)
                last[("launch", k)] = last.get(k)
            elif kind == "FAIL":
                if KW.is_host_fail(cls, why or ""):
                    last[k] = ("host", None)
                else:
                    key = FG.norm_class(cls or "", why or "")
                    prev = last.get(k)
                    if prev and prev[0] == "fail" and prev[1] == key:
                        blocked += 1                   # this relaunch repeated the previous key: the gate would have refused it
                    last[k] = ("fail", key)
            elif kind == "ENQUEUE":
                last[k] = ("pass", None)
    assert launches > 500
    share = blocked / launches
    print("replay: relaunches %d; repeat-key relaunches the gate refuses %d (%.0f%%); after a PASS or a HOST/STOPPED fail (justified) %d (%.0f%%); "
          "after a design / tool fail with a different key %d (%.0f%%: the gate lets them out only when plan block, src, overlay or the stage tools changed)"
          % (launches, blocked, share * 100, justified, justified * 100 / launches, prevfail - blocked, (prevfail - blocked) * 100 / launches))
    assert share >= 0.25


def test_native_kit_failure_key_tracks_measured_context_not_paths(tmp_path, monkeypatch):
    import json, shutil
    monkeypatch.setattr(KW, "stage_tools_digest", lambda *a, **k: "same-stage-tools")
    old, new, moved = [tmp_path / x for x in ("old", "new", "moved")]
    for p in (old, new, moved):
        p.mkdir()
    for p, text in ((old, '{"map_file":"/published/map.json"}'), (new, '{"map_file":"../published/map.json"}')):
        (p / "ab.json").write_text(text)
        (p / "native_topology.json").write_text(json.dumps({"asbuilt_sha256": text}))
    for name in ("ab.json", "native_topology.json"):
        shutil.copyfile(old / name, moved / name)
    def context(p):
        return dict(mode="bind", asbuilt=str(p / "ab.json"), bind_out=str(p))
    c = cfg()
    c["dies"]["s81"]["kit_rtl"] = context(old)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "spec.json").write_text(json.dumps(dict(src_sha="s1", src_overlay="o1", kit_rtl=context(old))))
    r = dict(rec_of("hub_C"), stage="kit_rtl", dir=str(attempt), started=1)
    st = {"items": {"failed": r}}
    KW.note_fail_key(c, st, r, "FLOW", "manifest absolute map_file @kit_rtl")
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]
    c["dies"]["s81"]["kit_rtl"] = context(moved)
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]  # bytes unchanged: no path-only release
    c["dies"]["s81"]["kit_rtl"] = context(new)
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1") == (False, "", ["bind_context"])
    # Actual legacy key migration uses the exact failed attempt spec, not current config.
    del st["fail_keys"]["s81|hub_C"]["parts"]["bind_context"]
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1") == (False, "", ["bind_context"])
    st["items"] = {}
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]  # unmeasured legacy context cannot release
    st["items"] = {"failed": r}
    c["dies"]["s81"]["kit_rtl"] = context(tmp_path / "unreadable")
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]
    # A shared bind change does not change an item's explicit private bind.
    c["dies"]["s81"]["kit_rtl"] = context(new)
    c["dies"]["s81"]["item_inputs"] = {"hub_C": {"kit_rtl": context(old)}}
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]
    c["dies"]["s81"]["item_inputs"]["hub_C"]["kit_rtl"] = context(new)
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1") == (False, "", ["bind_context"])
    # A metadata repair is not a timing/route redesign release.
    c["dies"]["s81"]["kit_rtl"] = context(new)
    st["fail_keys"]["s81|hub_C"]["stage"] = "route"
    assert KW.fail_key_gate(c, st, "s81", "hub_C", "b1")[0]
