from copy import deepcopy
import hashlib
import json

import pytest

from bound_station_source import (FAMILY_SCHEMA, SCHEMA, _bf_col3_c_pg_predecessor, _family_type_logic,
                                  _m5_grid_change, _type_logic, verify)


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


@pytest.mark.parametrize("receipt_schema", (SCHEMA, FAMILY_SCHEMA))
def test_stale_producer_rejected_before_station_work(tmp_path, receipt_schema):
    producer = tmp_path / "producer.json"
    prepared = tmp_path / "prepared.json"
    producer.write_text("old producer")
    prepared.write_text("new plan")
    receipt = tmp_path / "scope.json"
    receipt.write_text(json.dumps({
        "schema": receipt_schema,
        "type": "receiver",
        "producer_plan_sha256": "stale",
        "prepared_plan_sha256": hashlib.sha256(prepared.read_bytes()).hexdigest(),
    }))
    with pytest.raises(ValueError, match="stale plan or producer"):
        verify(receipt, prepared, producer, "receiver", tmp_path, "asbuilt.json")


def test_family_geometry_keeps_edge_and_collector_role():
    old = {
        "outline_um": [100, 100],
        "buses": [],
        "ft_slots": [],
        "hard_cores": [],
        "internal_stations": [],
        "clock": {"edge_clocks": [{"name": "source_clk", "tap_um": [12, 4]}]},
    }
    prepared = deepcopy(old)
    prepared["clock"]["edge_clocks"][0]["tap_um"] = [12, 5]
    prepared["clock"]["landing_contract"] = {"collector_tree": {"capture": True}}
    assert _family_type_logic(old) == _family_type_logic(prepared)
    prepared["clock"]["edge_clocks"][0]["name"] = "other_clk"
    assert _family_type_logic(old) != _family_type_logic(prepared)



def test_reviewed_pg_predecessor_accepts_one_literal_selected_type_change(tmp_path):
    prior = {"partition_types": {"receiver": {}, "peer": {}}}
    path = tmp_path / "individual-predecessor.json"
    path.write_text(json.dumps(prior))
    proof = {"prior_plan": {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
    current = deepcopy(prior)
    current["partition_types"]["receiver"]["core_pg_connect"] = True
    assert _bf_col3_c_pg_predecessor(current, "receiver", proof) == (path, prior)
    current["partition_types"]["peer"]["core_pg_connect"] = True
    with pytest.raises(ValueError, match="only the selected type"):
        _bf_col3_c_pg_predecessor(current, "receiver", proof)
    current["partition_types"]["peer"].clear()
    current["partition_types"]["receiver"]["core_pg_connect"] = 1
    with pytest.raises(ValueError, match="explicit grid"):
        _bf_col3_c_pg_predecessor(current, "receiver", proof)


def test_reviewed_pg_grid_preserves_named_M5_M6_membership_and_all_other_code():
    first, second = r"{^u_bound\.left$}", r"{^u_bound\.right$}"
    targets = first + " " + second
    grid = "define_pdn_grid -macro -name {core_pg_M5} -instances "
    tail = " -voltage_domains {CORE} -halo {0}\nadd_pdn_connect -grid {core_pg_M5} -layers {M5 M6}\n"
    before = grid + "{{^old$}}" + tail + "global_connect\n"
    after = grid + "{" + first + " {^old$} " + second + "}" + tail + "global_connect\n"
    assert _m5_grid_change(before, after, targets)[1:] == (1, 3)
    with pytest.raises(ValueError, match="M5 to M6"):
        _m5_grid_change(before.replace("M5 M6", "M5 M7"), after.replace("M5 M6", "M5 M7"), targets)
    with pytest.raises(ValueError, match="outside the two approved"):
        _m5_grid_change(before, after.replace("^old$", "^foreign$"), targets)
    with pytest.raises(ValueError, match="grid options"):
        _m5_grid_change(before, after.replace("-halo {0}", "-halo {1}"), targets)
    with pytest.raises(ValueError, match="unrelated executable PDN"):
        _m5_grid_change(before, after + "add_pdn_connect -grid {core_pg_M7} -layers {M7 M8}\n", targets)
