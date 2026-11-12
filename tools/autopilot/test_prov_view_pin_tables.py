"""KW-FIX-45 11-11: module_pin_tables() exposes instances of one module whose pin tables differ (one provisional view per module
cannot serve them); a type whose instances share one table is unaffected."""
import json
from pathlib import Path
import prov_view as PV


def plan_with(tmp_path, tables):
    cores = []
    for i, (name, rows) in enumerate(tables):
        (tmp_path / f"{name}.json").write_text(json.dumps(rows))
        cores.append({"inst": f"u{i}", "module": "ot_bank", "pins_file": f"{name}.json", "outline_um": [10, 10], "origin_um": [0, 0]})
    return {"partition_types": {"T": {"hard": False, "hard_cores": cores}}}


def rows(layer):
    return [{"name": "a", "layer": layer, "x": 1.0, "y": 2.0}, {"name": "b", "layer": layer, "x": 3.0, "y": 4.0}]


def test_same_table_instances_are_one_group(tmp_path):
    plan = plan_with(tmp_path, [("t1", rows("M4")), ("t2", rows("M4"))])
    got = PV.module_pin_tables(plan, "T", str(tmp_path))
    assert list(got) == ["ot_bank"] and len(got["ot_bank"]) == 1


def test_canon_vs_weight_e_tables_are_two_groups(tmp_path):
    plan = plan_with(tmp_path, [("t1", rows("M4")), ("t2", rows("M5"))])      # E M4 -> N M5 style layer difference
    got = PV.module_pin_tables(plan, "T", str(tmp_path))
    assert len(got["ot_bank"]) == 2
    assert sorted(len(v) for v in got["ot_bank"].values()) == [1, 1]
