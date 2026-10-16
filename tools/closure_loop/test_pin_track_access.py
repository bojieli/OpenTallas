"""Catch manual IO pins that passed face-density checks but crashed TT routing."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("track_lint", ROOT / "tools/fp_margin_lint.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


def dump(boxes, direction="VERTICAL", patterns=None):
    return {"layers": [{"name": "M5", "dir": direction, "width": .024,
                        "track_patterns": [[.012, 100, .048]] if patterns is None else patterns}],
            "bterms": [["data", "data", "SIGNAL", "INPUT", boxes]]}


def test_actual_tt_twelve_nm_error_and_corrected_grant():
    # fs4 tag_payload: centre n*0.096, 24nm shape; DEF grid .012+n*.048.
    bad = dump([["M5", [.180, 0, .204, .084]]])
    assert lint.pin_track_access(bad)[1][0][0] == "data"
    good = dump([["M5", [.192, 0, .216, .084]]])
    assert lint.pin_track_access(good) == (1, [])


def test_wide_multishape_and_horizontal_landings():
    assert lint.pin_track_access(dump([["M5", [.180, 0, .228, .084]]])) == (1, [])
    assert lint.pin_track_access(dump([["M5", [.180, 0, .204, .084]],
                                       ["M5", [.192, 1, .216, 1.084]]])) == (1, [])
    assert lint.pin_track_access(dump([["M5", [0, .192, .084, .216]]], "HORIZONTAL")) == (1, [])
    assert lint.pin_track_access(dump([["M5", [0, .180, .084, .204]]], "HORIZONTAL"))[1]


def test_finite_grid_and_unknown_old_dump():
    assert lint.pin_track_access(dump([["M5", [.192, 0, .216, .084]]], patterns=[[.012, 2, .048]]))[1]
    assert lint.pin_track_access(dump([["M5", [.180, 0, .204, .084]]], patterns=[])) == (0, [])
    assert lint.pin_track_access(dump([["M5", [.180, 0, .204, .084]]], patterns=[[.012, 0, .048]]))[1]


def test_real_opendb_dump_preserves_def_grid(tmp_path):
    if not shutil.which("openroad"):
        pytest.skip("actual OpenDB required")
    fixture = ROOT / "tools/closure_loop/testdata/io_flop_at_pins"
    definition = (fixture / "test.def").read_text().replace(
        "COMPONENTS", "TRACKS Y 12 DO 400 STEP 48 LAYER M1 ;\nCOMPONENTS", 1)
    (tmp_path / "test.def").write_text(definition)
    script = f"""read_lef {fixture / 'test.lef'}
read_def {tmp_path / 'test.def'}
source {ROOT / 'tools/fp_margin_lint.tcl'}
ot_fp_lint_dump {tmp_path / 'dump.json'}
exit
"""
    (tmp_path / "run.tcl").write_text(script)
    run = subprocess.run(["openroad", "-exit", "-no_init", str(tmp_path / "run.tcl")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    measured = json.loads((tmp_path / "dump.json").read_text())
    assert measured["layers"][0]["track_patterns"] == [[.012, 400, .048]]
    assert lint.pin_track_access(measured)[0] == 3
