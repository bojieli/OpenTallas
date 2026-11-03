"""A repeated instance name in another partition must not select the wrong pin view."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("kv_wave_pinview", Path(__file__).with_name("kv_core_wave.py"))
wave = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wave)


def fixture(tmp_path, both=True):
    (tmp_path / "r0.json").write_text('{"orientation":"R0"}')
    (tmp_path / "mx.json").write_text('{"orientation":"fMX"}')
    def core(inst, pins):
        return dict(inst=inst, module="pair", pins_file=pins)
    slots = [core("p0", "mx.json")]
    if both:
        slots.append(core("p1", "r0.json"))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(dict(partition_types={
        "actual": dict(hard_cores=slots),
        "other": dict(hard_cores=[core("p0", "r0.json")]),
    })))
    cj = dict(module="pair", type="actual", inst="p0")
    view = dict(view="pair@" + wave.sha12(tmp_path / "r0.json"), insts=["p0", "p1"])
    return cj, view, plan


def test_alias_in_another_type_cannot_select_wrong_view(tmp_path):
    cj, view, plan = fixture(tmp_path)
    assert wave.plan_inst_for_view(cj, view, plan) == "p1"
    cj["inst"] = "p1"
    assert wave.plan_inst_for_view(cj, view, plan) == "p1"


def test_view_missing_in_actual_type_fails_closed(tmp_path):
    cj, view, plan = fixture(tmp_path, both=False)
    with pytest.raises(SystemExit, match="NO_RECIPE pair: requested pin view .* has no slot in core type actual"):
        wave.plan_inst_for_view(cj, view, plan)


def test_pair_uses_existing_pv_two_mode_recipe():
    assert wave.module_recipe("kv3_pv_pair") == wave.module_recipe("ot_qwen_tp8_pv_join_t")
    assert "--two-mode-grt" in wave.module_recipe("kv3_pv_pair")
