"""Legacy core recipes retain existing face-guard ring descriptors."""
import json
from pathlib import Path
import sys
import pytest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G
import face_guard as F

def test_legacy_integer_slots_stay_integer():
    assert G.core_land_slot_specs("core", {"z": 4, "a": 8}, ["a", "z"]) == {"a": 8, "z": 4}

def test_hold_mux_descriptor_survives_kit_consumer(tmp_path):
    source = {"data": {"D": 4, "form": "hold_mux"}}
    out = G.core_land_slot_specs("core", source, ["data"])
    path = tmp_path / "land_slots.json"
    path.write_text(json.dumps({"schema": "opentallas.core_land_slots.v1", "buses": out}))
    assert F.kit_land(path) == source
    assert F.land_spec(F.kit_land(path)["data"]) == (4, "hold_mux")

def test_explicit_icg_and_legacy_mix():
    source = {"a": 4, "b": {"D": 8, "form": "icg"}}
    assert G.core_land_slot_specs("core", source, ["a", "b"]) == source

@pytest.mark.parametrize("value", [
    {"D": 4, "form": "waiver"}, {"D": 4, "form": "hold_mux", "skip": True},
    {"D": 1, "form": "hold_mux"}, {"form": "ring_start", "ring": "data"},
    {"form": "origin_start", "origin": "u_origin"}, 1])
def test_invalid_or_non_slot_forms_refused(value):
    with pytest.raises(SystemExit):
        G.core_land_slot_specs("core", {"data": value}, ["data"])

def test_output_or_absent_bus_refused():
    with pytest.raises(SystemExit):
        G.core_land_slot_specs("core", {"out": {"D": 4, "form": "hold_mux"}}, ["data"])
