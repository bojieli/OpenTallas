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
    ("PASS", "flat-windows", "NOT RUN"), ("PASS", M.FLAT_MODE, "NOT RUN"),     # F4: an unbound PASS (no parent DEF / deck sha) never counts; bound PASS: test_f4_f5_f6
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


# ---- FABLE-INDEP re-review 11-27: findings F1-F7 --------------------------------------------------------------------------------------------------------------------------------
import argparse
import ast
import hashlib

PYA = Path(__file__).resolve().parent / "merged_gds_drc_pya.py"


def _pya_functions(*names):
    """exec the named helper functions of the klayout script against klayout.db (skipped where the module is absent; the docker selftest covers the same geometry)"""
    db = pytest.importorskip("klayout.db")
    tree = ast.parse(PYA.read_text())
    ns = {"pya": db, "SHORT_GROW_DBU": 1}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            exec(compile(ast.Module([node], []), str(PYA), "exec"), ns)
    return [ns[n] for n in names]


def test_f1_zero_gap_abutment_is_a_short():
    (short_overlap,) = _pya_functions("short_overlap")
    db = pytest.importorskip("klayout.db")
    core = db.Region(db.Box(0, 0, 1000, 100))
    none = db.Region()
    assert short_overlap(db.Region(db.Box(1000, 0, 1400, 100)), core, none).is_empty() is False     # zero-gap abutment
    assert short_overlap(db.Region(db.Box(1002, 0, 1400, 100)), core, none).is_empty()              # 2 dbu gap is spacing, not a short
    assert short_overlap(db.Region(db.Box(400, 0, 800, 100)), core, none).is_empty() is False       # overlap
    pins = db.Region(db.Box(900, 0, 1000, 100))
    assert short_overlap(db.Region(db.Box(900, 0, 1400, 100)), core, pins).is_empty()               # legal landing inside the core pin


def test_f2_shorts_cover_layers_above_m7():
    text = PYA.read_text()
    for layer in ("M8=80", "V7=75", "V8=85", "M9=90", "V9=95"):
        assert layer in text


def test_f3_nested_empty_cells_are_reported():
    (nested_empty_cells,) = _pya_functions("nested_empty_cells")
    db = pytest.importorskip("klayout.db")
    import re
    ly = db.Layout()
    top = ly.create_cell("CORE")
    for name in ("SRAM_A", "VIA_x", "FILL_DEF_FILL", "KEEP"):
        top.insert(db.CellInstArray(ly.create_cell(name).cell_index(), db.Trans()))
    ly.cell("KEEP").shapes(ly.layer(1, 0)).insert(db.Box(0, 0, 10, 10))
    assert nested_empty_cells(top) == ["SRAM_A"]
    assert nested_empty_cells(top, re.compile("SRAM")) == []


def _verdict_dir(tmp_path, **over):
    parent = tmp_path / "6_final.def"
    parent.write_text("DEF")
    kit = tmp_path / "kit"
    directory = kit / "merged_gds_drc"
    directory.mkdir(parents=True)
    core = tmp_path / "core.gds"
    core.write_bytes(b"GDS")
    v = dict(verdict="PASS", mode=M.FLAT_MODE, parent_def_sha256=hashlib.sha256(b"DEF").hexdigest(), deck_sha256=M.PINNED_BEOL_DECK_SHA256,
             deck="beol", halo_um=1.0, allow_empty="ROM", tool_sha256=M.tool_sha256(), core_sha256={"core": hashlib.sha256(b"GDS").hexdigest()})
    v.update(over)
    (directory / "verdict.json").write_text(json.dumps(v))
    return kit, dict(required=True, gated=["x.lef"], parent_def=str(parent), allow_empty="ROM", cores=[("core", str(core))])


@pytest.mark.parametrize("over,expected", [
    ({}, "PASS"),
    ({"parent_def_sha256": "0" * 64}, "NOT RUN"),          # F4: verdict of another parent DEF
    ({"parent_def_sha256": None}, "NOT RUN"),
    ({"deck_sha256": "e3b0c44298fc"}, "NOT RUN"),          # F6: not the pinned deck
    ({"deck_sha256": None}, "NOT RUN"),
    ({"deck": "full"}, "NOT RUN"),
    ({"halo_um": -100.0}, "NOT RUN"),                      # F5
    ({"allow_empty": ".*"}, "NOT RUN"),
    ({"tool_sha256": "0" * 64}, "NOT RUN"),                # N2: tool changed since the run
    ({"tool_sha256": None}, "NOT RUN"),
    ({"core_sha256": {"core": "0" * 64}}, "NOT RUN"),      # N2: core re-signed since the run
    ({"core_sha256": {}}, "NOT RUN"),
    ({"verdict": "FAIL"}, "FAIL"),
])
def test_f4_f5_f6_gate_binds_verdict_to_inputs(tmp_path, monkeypatch, over, expected):
    kit, kp = _verdict_dir(tmp_path, **over)
    monkeypatch.setattr(M, "kit_plan", lambda _: kp)
    assert M.gate_check(kit)["verdict"] == expected


def test_f4_run_removes_stale_verdict_and_crash_is_error(tmp_path, monkeypatch):
    parent = tmp_path / "p.def"
    parent.write_text("DEF")
    out = tmp_path / "out"
    out.mkdir()
    (out / "verdict.json").write_text(json.dumps(dict(verdict="PASS", mode=M.FLAT_MODE)))

    def boom(*_a, **_k):
        raise MemoryError("simulated crash")
    monkeypatch.setattr(M.subprocess, "call", boom)
    ns = argparse.Namespace(parent_def=str(parent), design="T", core=[], lef=[], allow_empty="", halo_um=1.0, out=str(out), hier=False,
                            image="x", mem_gb=1, local=True, deck="beol")
    assert M.run(ns) == 2
    v = json.loads((out / "verdict.json").read_text())
    assert v["verdict"] == "ERROR"


def test_f4_verdict_crash_is_error_not_stale_pass(tmp_path):
    (tmp_path / "verdict.json").write_text(json.dumps(dict(verdict="PASS", mode=M.FLAT_MODE)))
    assert M.verdict(argparse.Namespace(out=str(tmp_path))) == 2           # no parent_cells.json: crash
    assert json.loads((tmp_path / "verdict.json").read_text())["verdict"] == "ERROR"


@pytest.mark.parametrize("halo", [-100.0, -0.1, 5.5, 1e9])
def test_f5_halo_validated(halo):
    ns = argparse.Namespace(halo_um=halo, allow_empty="", deck="beol")
    with pytest.raises(SystemExit):
        M.validate_run_args(ns, ["core"])
    M.validate_run_args(argparse.Namespace(halo_um=1.0, allow_empty="ROM_.*", deck="beol"), ["core"])


@pytest.mark.parametrize("regex", ["(", "core", ".*", "co"])
def test_f5_allow_empty_validated(regex):
    with pytest.raises(SystemExit):
        M.validate_run_args(argparse.Namespace(halo_um=1.0, allow_empty=regex, deck="beol"), ["core"])


def test_f5_needs_gate_fails_closed(tmp_path):
    assert M.needs_gate(str(tmp_path / "does_not_exist.lef")) is True


def test_f6_deck_pin_in_script_and_verdict(tmp_path):
    line = M.deck_pin_line("/out")
    assert M.PINNED_BEOL_DECK_SHA256 in line and "DECK_SHA_MISMATCH" in line and "exit 5" in line
    a = argparse.Namespace(out=str(tmp_path), deck="beol", hier=False, lef=[], parent_def="p.def", design="T", allow_empty="", halo_um=1.0)
    (tmp_path / "x").write_text("")
    script = M.build_script(a, [], dict(out="/out", tool="/tool", lefs="/lefs", pdef="/pdef"))
    assert M.PINNED_BEOL_DECK_SHA256 in script
    # an empty deck (awk cut matched nothing) gives a different sha: _bind records it and the PASS is refused
    (tmp_path / "beol.lydrc").write_text("")
    v = M._bind(dict(verdict="PASS"), tmp_path)
    assert v["deck_sha256"] != M.PINNED_BEOL_DECK_SHA256


def test_f7_unchecked_bbox_comes_from_lef_outline():
    text = PYA.read_text()
    assert "LEF_BBOX" in text and "inst.dtrans * LEF_BBOX[nm]" in text


def test_n3_n4_verdict_needs_complete_run_and_binding(tmp_path):
    (tmp_path / "run_meta.json").write_text("{}")
    (tmp_path / "parent_cells.json").write_text("{}")
    assert M.verdict(argparse.Namespace(out=str(tmp_path))) == 2           # run_meta without run_complete: stale-evidence risk
    assert "did not complete" in json.loads((tmp_path / "verdict.json").read_text())["problems"][0]


def test_n4_legacy_dir_pass_is_not_bound(tmp_path):
    win = tmp_path / "win"
    win.mkdir()
    meta = [{"i": 0, "master": "core", "bbox": [-5, -5, 15, 15]}]
    for kind in ("merged", "parent_only", "macros_only"):
        (win / f"{kind}_windows.json").write_text(json.dumps(meta))
        (win / f"{kind}_0.lyrdb").write_text("<report-database><items/></report-database>")
    (win / "shorts_0.json").write_text("{}")
    (tmp_path / "parent_cells.json").write_text(json.dumps({"hard_core_insts": [{"master": "core", "bbox": [0, 0, 10, 10]}], "dbu": 0.00025}))
    M.verdict(argparse.Namespace(out=str(tmp_path)))
    assert json.loads((tmp_path / "verdict.json").read_text())["verdict"] == "NOT-BOUND"
