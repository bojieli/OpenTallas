"""AB-CONSUMED-1122 (FLOW-OPS-R2, COORD): an A/B env override that config.mk does not export is refused before place."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_provenance as EP  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def tree(tmp_path, monkeypatch):
    """a source tree: OT_TAP_RESET_SPLIT read by a flow tcl only, OT_GEN_X by a generator, OT_KEEP_WIRES by both"""
    (tmp_path / "tools" / "die_plan").mkdir(parents=True)
    (tmp_path / "tools" / "die_plan" / "clock_taps.tcl").write_text("if {$::env(OT_TAP_RESET_SPLIT) eq 1} {}\nputs $::env(OT_KEEP_WIRES)\n")
    (tmp_path / "tools" / "die_plan" / "gen_phys.py").write_text('a = os.environ.get("OT_GEN_X")\ncfg.append("export OT_TAP_RESET_SPLIT = 1")\n')
    (tmp_path / "tools" / "die_plan" / "keep.py").write_text('K = "OT_KEEP_WIRES"\n')
    real = EP.key_readers
    monkeypatch.setattr(EP, "key_readers", lambda keys, root=None: real(keys, str(tmp_path)))
    realf = EP.config_forms
    monkeypatch.setattr(EP, "config_forms", lambda root=None: realf(str(REPO)))

REPO = Path(__file__).resolve().parents[2]
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


def test_gen_read_key_consumed_unread_key_warns():
    r = rec(dict(WAVE, OT_GEN_X="1", OT_LABEL="z", OT_TAP_RESET_SPLIT="1"), ["OT_GEN_X", "OT_LABEL", "OT_TAP_RESET_SPLIT"])
    ok, lines = EP.judge(r, "export OT_FLOW_TAG = t\n")
    fail = [ln for ln in lines if "not consumed" in ln]
    assert not ok and len(fail) == 1 and "OT_TAP_RESET_SPLIT" in fail[0] and "OT_GEN_X" not in fail[0]
    assert any("WARN" in ln and "read by nothing" in ln and "OT_LABEL" in ln for ln in lines)
    r2 = rec(dict(WAVE, OT_GEN_X="1", OT_LABEL="z"), ["OT_GEN_X", "OT_LABEL"])
    assert EP.judge(r2, "export OT_FLOW_TAG = t\n")[0]


def test_translated_knob_checked_in_its_config_form():
    """COORD 11-22: H9R0-R4 kit C, OT_GRT_CONG_ITERS=50 written as GLOBAL_ROUTE_ARGS ... -congestion_iterations 50"""
    forms = EP.config_forms(str(REPO))
    assert "OT_GRT_CONG_ITERS" in forms
    r = rec(dict(WAVE, OT_GRT_CONG_ITERS="50"), ["OT_GRT_CONG_ITERS"])
    ok, lines = EP.judge(r, "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 50\n")
    assert ok and not any("not consumed" in ln for ln in lines)
    ok, lines = EP.judge(r, "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 10\n")
    assert not ok and any("not consumed" in ln and "OT_GRT_CONG_ITERS" in ln for ln in lines)
    assert EP.judge(rec(dict(WAVE, OT_GRT_CONG_ITERS="30"), ["OT_GRT_CONG_ITERS"]), "")[0]      # the default writes no line


def test_gen_phys_writes_the_declared_form(monkeypatch):
    import re
    import sys as _s
    _s.path.insert(0, str(REPO / "tools" / "die_plan"))
    import gen_phys as GP
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "50")
    line = "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose" + f" -congestion_iterations {GP._grt_cong_iters()}"
    assert re.search(GP.ENV_CONFIG_FORMS["OT_GRT_CONG_ITERS"]["re"].replace("{v}", "50"), line, re.M)
    assert EP.config_forms(str(REPO)) == GP.ENV_CONFIG_FORMS
