import importlib.util
import subprocess
from pathlib import Path

H = Path(__file__).parent
def load(n):
    s = importlib.util.spec_from_file_location(n, H / (n + ".py")); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
LS, PR = load("lane_status"), load("post_redirect")

BAD = ("lane\\tstatus\\tsuccessor\\tupdated\\n".replace("\\t", "\t").replace("\\n", "\n")
       + "A\tstood-down 2026-11-21 05:3x PST (context)\tB (needed; scope x)\n"
       + "C\t2026-11-21\tD\n"
       + "E\tstood-down\tnone (nobody)\t2026-11-21 00:xx\n"
       + "A\tstood-down\tB\t2026-11-21\n")

def test_bad_rows_found_and_repaired():
    assert len(LS.check_text(BAD)) >= 3
    fixed = LS.repair_text(BAD)
    import os
    assert LS.check_text(fixed.replace("\t\n", "\t2026-11-21\n")) == [] or all("updated" in w for _, w, _ in LS.check_text(fixed))
    st = PR.load_status("/nonexistent")
    assert st == {}

def test_tolerant_load_and_chain(tmp_path):
    (tmp_path / "lanes").mkdir()
    (tmp_path / "lanes/LANE-STATUS.tsv").write_text(BAD + "B\tlive\t\t2026-11-21\n")
    st = PR.load_status(tmp_path)
    assert PR.resolve("A", st) == ["B"] and PR.resolve("E", st) == []
    assert PR.live_lane("A", st) == ("B", "A > B")

def test_set_row(tmp_path):
    f = tmp_path / "t.tsv"; f.write_text("lane\tstatus\tsuccessor\tupdated\tnote\nX\tlive\t\t2026-11-20\n")
    r = subprocess.run(["python3", "-I", str(H / "lane_status.py"), "--set", str(f), "X", "Y", "why"], capture_output=True, text=True)
    assert r.returncode == 0 and "X\tstood-down\tY\t" in r.stdout
    r = subprocess.run(["python3", "-I", str(H / "lane_status.py"), "--set", str(f), "X", "bad name", ""], capture_output=True, text=True)
    assert r.returncode == 1
