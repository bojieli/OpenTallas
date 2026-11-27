from copy import deepcopy
import hashlib
import json

import pytest

from bound_station_source import SCHEMA, _type_logic, verify


def test_crop_keeps_station_and_landing_logic():
    original = {
        "outline_um": [100, 100],
        "buses": [{"name": "out", "width": 8, "window_um": [4, 8]}],
        "ft_slots": [],
        "hard_cores": [{"inst": "u_macro", "module": "memory", "origin_um": [20, 30], "lef": "old/memory.lef"}],
        "internal_stations": [{"conn": "bus:out", "regs_um": [[8, 9]], "launch": "core"}],
        "clock": {
            "taps": [{"name": "clk", "xy": [8, 8]}],
            "landing_contract": {
                "bands": {"in": {"rect_um": [4, 6, 10, 20], "ring_place": "ff"}},
                "collector_local_sources": [],
                "pins": [{"port": "fstart", "xy_um": [4, 8]}],
            },
            "landing_local_resets": [{"raw": "rst_rl_7", "xy_um": [5, 8]}],
            "landing_writer_start": {"branches": {}},
        },
    }
    crop = deepcopy(original)
    crop["outline_um"][1] = 60
    crop["internal_stations"][0]["regs_um"] = [[8, 10]]
    crop["hard_cores"][0]["origin_um"] = [15, 15]
    crop["clock"]["landing_contract"]["bands"]["in"]["rect_um"] = [7, 8, 11, 21]
    assert _type_logic(original) == _type_logic(crop)
    deeper = deepcopy(crop)
    deeper["internal_stations"][0]["regs_um"].append([8, 12])
    assert _type_logic(original) != _type_logic(deeper)
    changed_reset = deepcopy(crop)
    changed_reset["clock"]["landing_local_resets"][0]["raw"] = "rst_rl_8"
    assert _type_logic(original) != _type_logic(changed_reset)
    crop["clock"]["macroclk"] = True
    assert _type_logic(original) != _type_logic(crop)


def test_stale_producer_rejected_before_station_work(tmp_path):
    producer = tmp_path / "producer.json"
    prepared = tmp_path / "prepared.json"
    producer.write_text("old producer")
    prepared.write_text("new plan")
    receipt = tmp_path / "scope.json"
    receipt.write_text(json.dumps({
        "schema": SCHEMA,
        "type": "receiver",
        "producer_plan_sha256": "stale",
        "prepared_plan_sha256": hashlib.sha256(prepared.read_bytes()).hexdigest(),
    }))
    with pytest.raises(ValueError, match="stale plan or producer"):
        verify(receipt, prepared, producer, "receiver", tmp_path, "asbuilt.json")
