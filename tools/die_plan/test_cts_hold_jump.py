import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cts_hold_jump as J  # noqa: E402


def log(*n):
    return "".join(f"[INFO RSZ-0032] Inserted {x} hold buffers.\n" for x in n) + "[INFO CTS-0098] done\n"


def test_chunks_are_summed():
    assert J.count_hold_buffers(log(2001, 2001, 483)) == 4485
    assert J.count_hold_buffers(log("16,494")) == 16494
    assert J.count_hold_buffers("nothing") == 0


def test_headseg44_shape_is_flagged():
    r = J.compare(16494, 5000)
    assert r["flag"] and r["verdict"] == "JUMP" and r["ratio"] > 3


def test_two_x_boundary_and_floor():
    assert J.compare(2000, 1000)["flag"] and not J.compare(1999, 1000)["flag"]
    assert not J.compare(9, 3)["flag"]               # tiny kit: below the floor
    assert J.compare(0, 100)["verdict"] == "OK"


def test_no_baseline_never_flags():
    for prev in (None, 0):
        assert J.compare(5000, prev)["verdict"] == "NO_BASELINE" and not J.compare(5000, prev)["flag"]


def test_cli_report_json_and_strict(tmp_path):
    cur, prev = tmp_path / "cur.log", tmp_path / "prev.log"
    cur.write_text(log(8000, 8494))
    prev.write_text(log(3000))
    out = tmp_path / "r.json"
    cmd = [sys.executable, "-I", str(HERE / "cts_hold_jump.py"), str(cur), str(prev), "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0 and "FLAG" in r.stdout
    assert json.loads(out.read_text())["current"] == 16494
    assert subprocess.run(cmd + ["--strict"], capture_output=True, text=True).returncode == 3
    # the report json is a valid previous form for the next run
    cur.write_text(log(16000))
    r = subprocess.run([sys.executable, "-I", str(HERE / "cts_hold_jump.py"), str(cur), str(out)], capture_output=True, text=True)
    assert "OK" in r.stdout and "FLAG" not in r.stdout


def test_missing_previous_is_not_an_error(tmp_path):
    cur = tmp_path / "c.log"
    cur.write_text(log(500))
    r = subprocess.run([sys.executable, "-I", str(HERE / "cts_hold_jump.py"), str(cur), str(tmp_path / "none.log")], capture_output=True, text=True)
    assert r.returncode == 0 and "NO_BASELINE" in r.stdout
