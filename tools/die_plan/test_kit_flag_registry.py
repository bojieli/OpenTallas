"""P-FLAG-SCHEMA-UNREGISTERED (STATION-BITORDER 11-27): one schema test lists every kit flag the generators read.

  - every os.environ OT_* key gen_phys reads is in kit_flags.KIT_FLAGS or the frozen LEGACY_GEN_ENV (a new flag needs a registry line)
  - every budgets key gen_phys reads is declared in schema.py (else PRE refuses the plan: SCHEMA-UNKNOWN-KEY) and in die_plan.schema.json
  - every registered flag names real plan keys, a config.mk export the generator writes and a flow reader that consumes it
  - OT_FT_LANE_MONO is settable per die / type from the plan or the kit env, and the kit env provenance records the export
    python3 -m pytest -q tools/die_plan/test_kit_flag_registry.py"""
import json
import re
import sys
from pathlib import Path

import pytest

import gen_phys
import kit_flags
import schema

HERE = Path(__file__).resolve().parent
GEN = (HERE / "gen_phys.py").read_text()
BUDGET_PROPS = schema.SCHEMA["properties"]["budgets"]["properties"]


def _gen_env_keys():
    return set(re.findall(r'environ(?:\.get\(|\[)\s*"(OT_[A-Z0-9_]+)"', GEN))


def _gen_budget_keys():
    return set(re.findall(r'budgets(?:\.get\(|\[)\s*"([a-z0-9_]+)"', GEN))


def test_every_generator_env_key_is_registered():
    known = set(kit_flags.KIT_FLAGS) | set(kit_flags.LEGACY_GEN_ENV)
    missing = sorted(_gen_env_keys() - known)
    assert not missing, f"unregistered generator env keys (add a kit_flags.KIT_FLAGS entry): {missing}"
    assert not set(kit_flags.LEGACY_GEN_ENV) & set(kit_flags.KIT_FLAGS)


def test_every_generator_budgets_key_is_in_the_schema():
    missing = sorted(_gen_budget_keys() - set(BUDGET_PROPS))
    assert not missing, f"budgets keys read by gen_phys but not in schema.py (PRE SCHEMA-UNKNOWN-KEY): {missing}"
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())["properties"]["budgets"]["properties"]
    assert not sorted(_gen_budget_keys() - set(on_disk)), "die_plan.schema.json is stale (python3 schema.py dump-schema)"


def test_registered_flags_are_wired_end_to_end():
    for name, f in kit_flags.KIT_FLAGS.items():
        assert set(f) >= {"set", "budgets", "config", "consumer", "default"}, name
        for k in f["budgets"]:
            assert k in BUDGET_PROPS, (name, k)
            assert f'"{k}"' in GEN, (name, k)
        cfg = f["config"]
        assert ("export " + cfg) in GEN or (chr(34) + cfg + chr(34)) in GEN, name
        reader = (HERE / f["consumer"]).read_text()
        assert re.search(r"::env\(%s\)" % re.escape(f["config"]), reader), (name, f["consumer"])


def test_flow_script_readers_of_lane_mono_are_registered():
    tcl = (HERE / "face_flops.tcl").read_text()
    keys = set(re.findall(r"::env\((OT_FT_LANE_MONO[A-Z_]*)\)", tcl))
    assert keys and keys <= set(kit_flags.KIT_FLAGS), keys


def test_lane_mono_setting_per_plan_type_and_kit_env(monkeypatch):
    monkeypatch.delenv("OT_FT_LANE_MONO", raising=False)
    assert gen_phys._ft_lane_mono_exports({}, "t3") == []
    assert gen_phys._ft_lane_mono_exports({"ft_lane_mono": True}, "t3") == ["export OT_FT_LANE_MONO = 1"]
    b = {"ft_lane_mono_types": ["ot_s81sl_kv_leaf"]}
    assert gen_phys._ft_lane_mono_exports(b, "ot_s81sl_kv_leaf__t3")          # unsplit base name
    assert not gen_phys._ft_lane_mono_exports(b, "ot_s81sl_other__t3")
    monkeypatch.setenv("OT_FT_LANE_MONO", "1")                                # kit env (item_env) per die / item
    assert gen_phys._ft_lane_mono_exports({}, "t3") == ["export OT_FT_LANE_MONO = 1"]
    monkeypatch.setenv("OT_FT_LANE_MONO", "0")                                # forced off beats the plan
    assert gen_phys._ft_lane_mono_exports({"ft_lane_mono": True}, "t3") == []


def test_lane_mono_tuning_knobs_travel_only_with_the_flag(monkeypatch):
    monkeypatch.delenv("OT_FT_LANE_MONO", raising=False)
    monkeypatch.setenv("OT_FT_LANE_MONO_RING_UM", "25")
    monkeypatch.setenv("OT_FT_LANE_MONO_FILL", "0.4")
    assert gen_phys._ft_lane_mono_exports({}, "t3") == []
    assert gen_phys._ft_lane_mono_exports({"ft_lane_mono": True}, "t3") == [
        "export OT_FT_LANE_MONO = 1", "export OT_FT_LANE_MONO_RING_UM = 25", "export OT_FT_LANE_MONO_FILL = 0.4"]
    monkeypatch.setenv("OT_FT_LANE_MONO_FILL", "-1")
    with pytest.raises(ValueError):
        gen_phys._ft_lane_mono_exports({"ft_lane_mono": True}, "t3")


def test_plan_keys_pass_the_schema():
    props = {"ft_lane_mono": True, "ft_lane_mono_types": ["a"], "ft_polarity_local": True, "relay_mid_fit_types": ["a"],
             "relay_fallback_max_frac": None}
    for k, v in props.items():
        assert k in BUDGET_PROPS
    import jsonschema
    jsonschema.validate({k: v for k, v in props.items()}, {"type": "object", "properties": BUDGET_PROPS, "additionalProperties": False})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"ft_lane_mono": "yes"}, {"type": "object", "properties": BUDGET_PROPS})


def test_kit_env_provenance_records_the_export():
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    import env_provenance as EP
    cfg = "export OT_PGCAP = 3\nexport OT_FT_LANE_MONO = 1\nexport OT_FT_LANE_MONO_FILL = 0.4\n"
    got = EP.config_ot(cfg)
    assert got["OT_FT_LANE_MONO"] == "1" and got["OT_FT_LANE_MONO_FILL"] == "0.4"
    # the gen env of the kit is recorded as "env" and compared with the wave env: a flag set in only one of them is a diff
    assert EP.env_diff({}, {"OT_FT_LANE_MONO": "1"}) == ["OT_FT_LANE_MONO"]
