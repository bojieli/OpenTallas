import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cpsg", HERE / "core_pin_sites_gate.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def P(n, x, y, L="M4"):
    return dict(name=n, layer=L, x=x, y=y)


def test_clean_face_passes():
    r = m.check_pins([P("a[0]", 0.042, 10.0), P("a[1]", 0.042, 10.192), P("clk", 50.0, 50.0, "M5")], 100, 100)
    assert r["verdict"] == "PASS" and r["stacked_pins"] == 0


def test_duplicate_site_fails():   # the l0r r3rt22 GRT-0031/0080 class
    r = m.check_pins([P("r_i[1]", 0.042, 266.844), P("clk", 0.042, 266.844), P("r_f", 0.042, 267.036)], 267.84, 267.84)
    assert r["verdict"] == "FAIL" and r["counts"]["dup_site"] == 1 and r["stacked_pins"] == 2


def test_same_track_different_depth_fails():   # same along-face position, access-extension centre at other depth
    r = m.check_pins([P("a", 0.042, 20.0), P("b", 0.9, 20.0)], 100, 100)
    assert r["verdict"] == "FAIL" and r["counts"]["pitch"] == 1


def test_sub_track_pitch_fails_adjacent_track_passes():
    assert m.check_pins([P("a", 0.042, 20.0), P("b", 0.042, 20.024)], 100, 100)["verdict"] == "FAIL"
    assert m.check_pins([P("a", 0.042, 20.0), P("b", 0.042, 20.048)], 100, 100)["verdict"] == "PASS"


def test_dup_name_and_off_face_fail():
    assert m.check_pins([P("a", 0.042, 20.0), P("a", 0.042, 30.0)], 100, 100)["counts"]["dup_name"] == 1
    assert m.check_pins([P("x", 20.0, 40.0)], 100, 100)["counts"]["off_face"] == 1


def test_cli_exit_codes(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"pins": [P("a", 0.042, 5.0), P("b", 0.042, 5.0)]}))
    good = tmp_path / "good.json"
    good.write_text(json.dumps([P("a", 0.042, 5.0), P("b", 0.042, 5.192)]))   # list form (HBM pin tables)
    cmd = [sys.executable, "-I", str(HERE / "core_pin_sites_gate.py"), "--outline", "10", "10", "--pins"]
    assert subprocess.run(cmd + [str(bad)], capture_output=True).returncode == 1
    assert subprocess.run(cmd + [str(good)], capture_output=True).returncode == 0
