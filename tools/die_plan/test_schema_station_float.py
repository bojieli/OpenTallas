"""WIDE-FLOAT-1: internal_stations[].sites="float" (kit_istations.chain_floats) is a schema key, nothing else is."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

_ITEM = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["internal_stations"]["items"]



def test_sites_float_is_declared():
    assert _ITEM["properties"]["sites"] == {"enum": ["float"]}


def test_sites_float_validates_and_other_values_fail():
    base = dict(conn="bus:frame_int_o1", from_um=[0, 0], to_um=[10, 0], regs_um=[[5, 0]])
    ok = dict(base, sites="float")
    bad = dict(base, sites="firm")
    plan = {"partition_types": {"t": {"internal_stations": [ok]}}}
    errs = [e for e in schema.validate(plan) if "internal_stations" in e]
    assert errs == []
    plan["partition_types"]["t"]["internal_stations"] = [copy.deepcopy(bad)]
    errs = [e for e in schema.validate(plan) if "internal_stations" in e]
    assert errs and "sites" in errs[0]
