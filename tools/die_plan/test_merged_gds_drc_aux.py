"""Flat-window DRC categories and location matching."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merged_gds_drc as M


@pytest.mark.parametrize("category", [
    "M4.AUX.3", "M5.AUX.3", "V4.AUX.1", "V5.AUX.1", "V3.M4.AUX.2",
    "V4.M5.AUX.2", "V5.M6.AUX.2", "V3.W.1", "M3.S.6",
])
def test_every_hard_core_category_gates(category):
    compare = dict(mode=M.FLAT_MODE, per_category={category: {"HARDCORE": 3}})
    verdict = M.judge(compare, {})
    assert verdict["verdict"] == "FAIL"
    assert verdict["gating_categories"] == {category: 3}


def test_match_uses_all_edges_at_one_dbu_and_same_category():
    reference = ("AUX", (100, 200, 300, 400))
    nearest = ("AUX", (99, 201, 301, 399))
    different_extent = ("AUX", (100, 200, 302, 400))
    different_location = ("AUX", (102, 201, 301, 399))
    different_category = ("VIA", (100, 200, 300, 400))
    assert list(M.subtract([nearest, different_extent, different_location, different_category],
                           [reference])) == [different_extent, different_location, different_category]


def test_window_capture_and_missing_baseline(tmp_path):
    windows = tmp_path / "win"
    windows.mkdir()
    meta = [{"i": 0, "master": "core", "bbox": [-5, -5, 15, 15]}]
    cells = {"hard_core_insts": [{"master": "core", "bbox": [0, 0, 10, 10]}], "dbu": 0.00025}
    first = "polygon: (1.00025,2;2,3)"
    second = "edge-pair: (1.00025,2;3,3)/(1,2;3,3)"
    for kind, values in (("merged", (first, second)), ("parent_only", (first,)), ("macros_only", ())):
        (windows / f"{kind}_windows.json").write_text(json.dumps(meta))
        items = "".join(f"<item><category>'V6.S.1-2-3'</category><values><value>{value}</value>"
                        "</values></item>" for value in values)
        (windows / f"{kind}_0.lyrdb").write_text(f"<report-database><items>{items}</items></report-database>")
    (windows / "shorts_0.json").write_text("{}")
    compare = M.window_compare(tmp_path, cells)
    assert compare["new_hardcore"] == 1
    mark = json.loads((tmp_path / compare["locations"]).read_text())
    assert mark["bbox_dbu"] == [4000, 8000, 12000, 12000]
    assert mark["category"] == "V6.S.1-2-3"
    (windows / "parent_only_windows.json").write_text("[]")
    with pytest.raises(ValueError, match="windows must match"):
        M.window_compare(tmp_path, cells)


@pytest.mark.parametrize("verdict,mode,expected", [
    ("PASS", "legacy", "NOT RUN"), ("PASS-PROVISIONAL", "legacy", "NOT RUN"),
    ("PASS", "flat-windows", "NOT RUN"), ("PASS", M.FLAT_MODE, "PASS"),
    ("FAIL", "legacy", "FAIL"),
])
def test_gate_requires_location_mode(tmp_path, monkeypatch, verdict, mode, expected):
    directory = tmp_path / "merged_gds_drc"
    directory.mkdir()
    (directory / "verdict.json").write_text(json.dumps(dict(verdict=verdict, mode=mode)))
    monkeypatch.setattr(M, "kit_plan", lambda _: dict(required=True, gated=["x.lef"]))
    assert M.gate_check(tmp_path)["verdict"] == expected


def test_duplicate_window_cannot_hide_another_core(tmp_path):
    directory = tmp_path / "win"
    directory.mkdir()
    cells = {"hard_core_insts": [{"master": "A", "bbox": [0, 0, 10, 10]},
                                {"master": "B", "bbox": [40, 0, 50, 10]}], "dbu": 0.00025}
    duplicate = {"i": 0, "master": "A", "bbox": [-5, -5, 15, 15]}
    for kind in ("merged", "parent_only", "macros_only"):
        (directory / f"{kind}_windows.json").write_text(json.dumps([duplicate, duplicate]))
    with pytest.raises(ValueError, match="every hard-core"):
        M.window_compare(tmp_path, cells)


@pytest.mark.parametrize("report", [
    "<other><items/></other>",
    "<report-database/>",
    "<report-database><items><item><category>V6.S</category><values><value>text: no geometry</value>"
    "</values></item></items></report-database>",
])
def test_incomplete_native_report_does_not_pass(tmp_path, report):
    path = tmp_path / "test.lyrdb"
    path.write_text(report)
    with pytest.raises(ValueError):
        list(M.parse_lyrdb(path, 0.00025))
