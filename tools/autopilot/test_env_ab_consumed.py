"""AB-CONSUMED-1122 (FLOW-OPS-R2, COORD): an A/B env override that config.mk does not export is refused before place."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_provenance as EP  # noqa: E402

WAVE = {"OT_KEEP_WIRES": "a", "OT_FLOW_TAG": "t"}


def rec(env, keys, **ab):
    return {"source": "private-spec", "die": "qwen_compute", "item": "coll_core", "wave_env": WAVE, "env": env,
            "ab": dict(keys=keys, why="A/B split", **ab)}


def test_dropped_override_refused():
    r = rec(dict(WAVE, OT_KEEP_WIRES="b", OT_TAP_RESET_SPLIT="1"), ["OT_KEEP_WIRES", "OT_TAP_RESET_SPLIT"])
    ok, lines = EP.judge(r, "export OT_KEEP_WIRES = b\nexport OT_FLOW_TAG = t\n")
    assert not ok and any("A/B override not consumed" in ln and "OT_TAP_RESET_SPLIT=1 (config.mk <unset>)" in ln for ln in lines)
    assert not any("OT_KEEP_WIRES=" in ln for ln in lines if "not consumed" in ln)


def test_consumed_unset_env_only_and_placed():
    r = rec(dict(WAVE, OT_TAP_RESET_SPLIT="1"), ["OT_TAP_RESET_SPLIT"])
    assert EP.judge(r, "export OT_TAP_RESET_SPLIT = 1\n")[0]
    r2 = rec({"OT_FLOW_TAG": "t"}, ["OT_KEEP_WIRES"])                         # unset A/B: nothing to consume
    assert EP.judge(r2, "export OT_FLOW_TAG = t\n")[0]
    r3 = rec(dict(WAVE, OT_X="1"), ["OT_X"], env_only=["OT_X"])
    assert EP.judge(r3, "")[0]
    ok, lines = EP.judge(rec(dict(WAVE, OT_TAP_RESET_SPLIT="1"), ["OT_TAP_RESET_SPLIT"]), "", placed=True)
    assert ok and any("WARN" in ln and "not consumed" in ln for ln in lines)
    assert EP.ab_not_consumed(rec(dict(WAVE, OT_A="2"), ["OT_A"]), {"OT_A": "3"}) == [("OT_A", "2", "3")]


def test_list_value_extended_by_generator_is_consumed():
    r = rec(dict(WAVE, OT_KEEP_WIRES="a:q b:q"), ["OT_KEEP_WIRES"])
    assert EP.ab_not_consumed(r, {"OT_KEEP_WIRES": "a:q b:q c:q"}) == []
    assert EP.ab_not_consumed(r, {"OT_KEEP_WIRES": "a:q"}) == [("OT_KEEP_WIRES", "a:q b:q", "a:q")]
