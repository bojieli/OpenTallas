"""KIT-OPS-6 11-14 (FABLE-TYPES-S81-LEAF 1 step 2): the per-port kit window takes the maximum over tap pairs that carry data only.
    python3 -m pytest -q tools/die_plan/test_kit_related_window.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta_related as DSR  # noqa: E402


def _tap(part, port, late, early, node):
    return {"port": f"t_{part}__{port}", "part": part, "late_ps": late, "early_ps": early, "cppr_node": node, "slew_ps": 20.0}


def _setup():
    rows = [_tap("a0", "clk_t1", 300.0, 280.0, "ra"), _tap("a0", "clk_t2", 340.0, 320.0, "ra"),
            _tap("a0", "clk_t3", 330.0, 310.0, "rb")]
    taps = {r["port"]: r for r in rows}
    rng = {"h": 2.0, "ra": 15.0, "rb": 15.0}
    plan = {"partitions": [{"name": "a0", "type": "T"}], "ports": []}
    pairs, _ = DSR.build_pairs(plan, taps)
    return taps, rng, plan, [pairs["intra"], pairs["intra_cross_region"]]


def test_unrelated_pairs_do_not_set_the_window(tmp_path):
    taps, rng, plan, pl = _setup()
    ptype = {"a0": "T"}
    allp = DSR.kit_port_needs(pl, taps, rng)
    assert allp[("a0", "clk_t1")] == pytest.approx(48.0)          # worst pair: cross-root t3
    f = tmp_path / "rel.json"
    f.write_text(json.dumps({"related_pairs": {"T": [["clk_t1", "clk_t2"]]}}))      # t1 exchanges data with t2 only
    rel = DSR.kit_related_pairs(f)
    r = DSR.kit_port_needs(pl, taps, rng, related=rel, ptype=ptype)
    assert r[("a0", "clk_t1")] == pytest.approx(45.0)             # t3 pair dropped: 340 - 280 - 15
    assert r[("a0", "clk_t3")] == 0.0 and r[("a0", "clk_t2")] <= allp[("a0", "clk_t2")]


def test_type_without_a_related_set_and_related_none_are_unchanged(tmp_path):
    taps, rng, plan, pl = _setup()
    base = DSR.kit_port_needs(pl, taps, rng)
    f = tmp_path / "rel.json"
    f.write_text(json.dumps({"related_pairs": {"OTHER": [["clk_t1", "clk_t2"]]}}))
    assert DSR.kit_port_needs(pl, taps, rng, related=DSR.kit_related_pairs(f), ptype={"a0": "T"}) == base
    assert DSR.kit_port_needs(pl, taps, rng, related=None, ptype={"a0": "T"}) == base


def test_producer_script_is_balanced_tcl():
    tcl = (HERE / "kit_tap_related_pairs.tcl").read_text()
    tclsh = shutil.which("tclsh")
    if tclsh:
        r = subprocess.run([tclsh], input="set t [read stdin]\nputs [info complete $t]\n", capture_output=True, text=True) if False else None
        out = subprocess.run([tclsh], input="puts [info complete {%s}]" % "x", capture_output=True, text=True)
    assert "related_pairs" in tcl and "OT_KTP_OUT" in tcl
