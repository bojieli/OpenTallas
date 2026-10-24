"""die_trial.py: build smoke on the tiny plan (no OpenROAD) + hop-table helpers."""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as D  # noqa: E402


def test_build_tiny(tmp_path):
    D.main(["build", str(HERE / "examples" / "tiny_plan.json"), "--out", str(tmp_path)])
    b = json.loads((tmp_path / "build.json").read_text())
    assert b["parts"] == 4 and b["data"]["nets"] > 0
    assert b["clock"]["taps"] == len(json.loads((tmp_path / "clock_tree.json").read_text())["taps"])
    rows = gzip.open(tmp_path / "nets.tsv.gz", "rt").read().splitlines()[1:]
    ft = [r.split("\t") for r in rows if r.split("\t")[1] == "ft"]
    # every ft hop has exactly one launch register and >= 1 capture register
    assert ft and all(r[4] and ";" not in r[4] and r[5] for r in ft)
    lef = next((tmp_path / "abstracts").glob("tq_*mid*.lef")).read_text()
    assert "fx_s0_d[0]" in lef and "fx_s0_q[0]" in lef


def test_interp_and_reach():
    rows = [(0, 700.0, 10.0, 60.0), (1000, 100.0, 50.0, 600.0), (2000, -500.0, 90.0, 1200.0)]
    assert D.interp(rows, 500, 1) == 400.0
    assert D.interp(rows, 3000, 1) == -1100.0
    assert abs(D.reach_of(rows) - 1166.7) < 0.1
