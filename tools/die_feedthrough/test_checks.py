"""Unit tests for checks.py: GRT log parsing, pin offsets on the track grid, probe DEF, die-probe relay selection."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks  # noqa: E402

LOG = """
[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
M8               1000           600            60.00%             0 /  0 /  0
M9               1000          1200           120.00%             0 /  5 /  300
---------------------------------------------------------------------------------------
Total            2000          1800            90.00%             0 /  5 /  300

[INFO GRT-0018] Total wirelength: 12345 um
"""

SPEC = dict(outline=[100.0, 50.0], master="m", ports=[
    dict(name="ft0_i", path=0, dir="input", face="W", lo=10.0, hi=12.0, layer="M8", bits=8),
    dict(name="ft0_o", path=0, dir="output", face="E", lo=10.0, hi=12.0, layer="M8", bits=8)],
    paths=[dict(path=0, **{"in": "ft0_i", "out": "ft0_o"}, bits=8, stages=2)])


def test_parse_grt():
    r = checks.parse_grt(LOG)
    assert r["total_overflow"] == 300 and r["layers"]["M9"]["overflow"] == 300
    assert r["layers"]["M8"]["usage_pct"] == 60.0 and r["wirelength_um"] == 12345.0


def test_bit_offsets_grid_and_range():
    offs = checks.bit_offsets(10.0, 12.0, 8, 0.08)
    assert len(offs) == 8 and len(set(offs)) == 8
    assert all(abs(o / 0.08 - round(o / 0.08)) < 1e-6 for o in offs)
    assert offs[0] >= 10.0 and offs[-1] <= 12.0


def test_abstract_def_pairs():
    txt = checks.abstract_def(SPEC)
    assert "PINS 16 ;" in txt and "NETS 8 ;" in txt and "- u_blk m + FIXED ( 0 0 ) N ;" in txt
    assert "ROW ROW_0" in txt and "TRACKS Y 80 DO 625 STEP 80 LAYER M8 ;" in txt
    assert "- ftn0_3 ( PIN ft0_i[3] ) ( PIN ft0_o[3] ) + USE SIGNAL ;" in txt


def test_pushed_relays():
    plan = dict(lanes=[dict(keep_channel=False, segments=[{}], relays=["r1", "r2"]),
                       dict(keep_channel=True, segments=[], relays=["r3"]),
                       dict(keep_channel=False, segments=[], relays=["r4"])])
    assert checks.pushed_relays(plan) == ["r1", "r2"]


def test_die_probe_prepares():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "plan.json"
        p.write_text(json.dumps(dict(lanes=[dict(keep_channel=False, segments=[{}], relays=["st_a_0"])])))
        checks.main(["die-probe", "--odb", str(Path(d) / "die.odb"), "--out", d + "/o", "--plan", str(p),
                     "--drop-pushed"])
        tcl = (Path(d) / "o/probe.tcl").read_text()
        assert "odb::dbInst_destroy" in tcl and "global_route" in tcl
        assert (Path(d) / "o/drop_relays.txt").read_text().strip() == "st_a_0"
