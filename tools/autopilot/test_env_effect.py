"""LAUNCH-GUARD 11-23: requested OT_* knobs must reach the kit's effective config.mk (env_effect.py, kit_wave.env_effect_refusal)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env_effect as EE  # noqa: E402
import kit_wave as KW  # noqa: E402

KNOWN = {"OT_TAP_GRT_PRE", "OT_PLACE_MAX_FANOUT", "OT_KEEP_WIRES", "OT_TT_SETUP_REPAIR", "OT_CLAND_STRIP_DENS"}
CFG_BLANK = "export DESIGN_NAME = x\nexport OT_TAP_GRT_PRE =\nexport OT_PLACE_MAX_FANOUT = 32\n"


def test_gen_switch_blank_in_config_is_a_mismatch():
    """FAM-S81-MISC kit 1: OT_GEN_TAP_GRT_PRE=1 with the config key written blank"""
    mm = EE.mismatches({"OT_GEN_TAP_GRT_PRE": "1", "OT_PLACE_MAX_FANOUT": "32"}, CFG_BLANK, KNOWN)
    assert mm == [("OT_GEN_TAP_GRT_PRE", "1", "OT_TAP_GRT_PRE", "")]
    assert "OT_GEN_TAP_GRT_PRE='1'" in EE.describe(mm)


def test_absent_key_wrong_value_and_ok_values():
    assert EE.mismatches({"OT_PLACE_MAX_FANOUT": "48"}, CFG_BLANK, KNOWN)[0][3] == "32"
    assert EE.mismatches({"OT_TT_SETUP_REPAIR": "both"}, CFG_BLANK, KNOWN)[0][3] is None
    assert EE.mismatches({"OT_CLAND_STRIP_DENS": "1.0"}, "export OT_CLAND_STRIP_DENS = 1\n", KNOWN) == []
    assert EE.mismatches({"OT_GEN_TAP_GRT_PRE": "1"}, "export OT_TAP_GRT_PRE = 1\n", KNOWN) == []
    assert EE.mismatches({"OT_GEN_TAP_GRT_PRE": "0"}, "x = 1\n", KNOWN) == []          # off requested, absent = off


def test_gen_time_only_keys_and_comments_are_not_checked():
    assert EE.mismatches({"OT_PG_DIE_PHASE": "1", "OT_FLOW_TAG": "f", "OT_GEN_M8_GRANT": "1"}, "", KNOWN) == []
    assert EE.mismatches({"OT_PLACE_MAX_FANOUT": "32"}, "# export OT_PLACE_MAX_FANOUT = 32\n", KNOWN)[0][3] is None


def test_list_knob_is_a_subset_and_last_assignment_wins():
    cm = "export OT_KEEP_WIRES = a:q b:r\nexport OT_PLACE_MAX_FANOUT = 16\nexport OT_PLACE_MAX_FANOUT = 32\n"
    assert EE.mismatches({"OT_KEEP_WIRES": "b:r", "OT_PLACE_MAX_FANOUT": "32"}, cm, KNOWN) == []
    assert EE.mismatches({"OT_KEEP_WIRES": "ot_dp_dly:r"}, cm, KNOWN)[0][0] == "OT_KEEP_WIRES"


def test_plan_field_maps_to_its_config_key():
    assert EE.mismatches({}, CFG_BLANK, KNOWN, {"clock.tap_grt_pre": True})[0][2] == "OT_TAP_GRT_PRE"
    assert EE.mismatches({}, "export OT_TAP_GRT_PRE = 1", KNOWN, {"clock.tap_grt_pre": True}) == []


def test_known_keys_come_from_the_current_generators():
    k = EE.known_keys()
    assert "OT_TAP_GRT_PRE" in k and "OT_PLACE_MAX_FANOUT" in k and "OT_PG_DIE_PHASE" not in k


def _runner(cfg_text):
    calls = []

    def run(stage, argv, timeout=None, idempotent=False):
        calls.append(stage)
        return (0, "KW_STAGE noise\n" + KW.ENV_EFFECT_MARK + "\n" + cfg_text) if cfg_text is not None else (0, "")
    return run, calls


def test_run_item_refusal_reads_the_kit_config(monkeypatch):
    sp = {"gen_env": {"OT_GEN_TAP_GRT_PRE": "1"}}
    run, calls = _runner(CFG_BLANK)
    assert "OT_TAP_GRT_PRE" in KW.env_effect_refusal(sp, run, lambda c: ["sh", c], "/k")
    assert calls == ["env_effect"]
    run, _ = _runner("export OT_TAP_GRT_PRE = 1\n")
    assert KW.env_effect_refusal(sp, run, lambda c: ["sh", c], "/k") == ""
    run, _ = _runner(None)                                                     # no config.mk (core freeze.json kit)
    assert KW.env_effect_refusal(sp, run, lambda c: ["sh", c], "/k") == ""
    run, calls = _runner(CFG_BLANK)
    assert KW.env_effect_refusal(dict(sp, env_effect_check=False), run, lambda c: ["sh", c], "/k") == "" and calls == []
    monkeypatch.setenv("OT_ENV_EFFECT_CHECK", "0")
    assert KW.env_effect_refusal(sp, run, lambda c: ["sh", c], "/k") == ""


def test_scan_lists_running_wave_and_live_private_kits(tmp_path):
    d = tmp_path / "a2"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_env": {"OT_GEN_TAP_GRT_PRE": "1"}}))
    st = {"items": {"x": {"die": "s81", "item": "t5", "attempt": 2, "status": "ENQUEUED", "q_status": "RUNNING", "kit": "epyc9:/k/t5", "dir": str(d)},
                    "y": {"die": "s81", "item": "t6", "attempt": 1, "status": "FAIL", "kit": "epyc9:/k/t6", "dir": str(d)}}}
    (tmp_path / "kit_wave_state.json").write_text(json.dumps(st))
    p = tmp_path / "private_specs" / "LANE" / "s81_t5_1"
    p.mkdir(parents=True)
    (p / "spec.json").write_text(json.dumps({"gen_env": {"OT_GEN_TAP_GRT_PRE": "1"}, "gen_host": "epyc9", "work": "/w", "item": "t5"}))
    (p / "run_item.log").write_text("x")
    q = tmp_path / "private_specs" / "LANE" / "s81_t5_0"
    q.mkdir(parents=True)
    (q / "spec.json").write_text("{}")
    (q / "run_item.log").write_text("x")
    (q / "result.json").write_text("{}")
    got = EE.running_kits(tmp_path)
    assert [(g[0], g[2], g[3]) for g in got] == [("wave s81/t5@2", "epyc9", "/k/t5"), ("private LANE/s81_t5_1", "epyc9", "/w/gen/t5")]
