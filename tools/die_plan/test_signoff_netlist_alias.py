"""signoff.evaluate re-reads the exported 6_final.v: an alias cycle is reported as netlist_alias FAIL (SPEPRD3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff  # noqa: E402

BAD = "module b (o);\n output o;\n wire n;\n HB4xp67_ASAP7_75t_R u (.A(o),\n    .Y(n));\n assign o = n;\nendmodule\n"
GOOD = "module b (o);\n output o;\n wire n, x;\n HB4xp67_ASAP7_75t_R u (.A(x),\n    .Y(n));\n assign o = n;\nendmodule\n"


def _rec(v):
    return dict(corners={}, inputs=dict(final_v=str(v)), route={})


def test_evaluate_netlist_alias_fail_and_pass(tmp_path):
    v = tmp_path / "6_final.v"
    v.write_text(BAD)
    rec = _rec(v)
    signoff.evaluate(rec)
    assert rec["checks"]["netlist_alias"]["verdict"] == "FAIL" and rec["checks"]["netlist_alias"]["problems"] == 1
    assert any(r.startswith("netlist_alias: FAIL") for r in rec["reasons"]) and rec["verdict"] == "NOT SIGNED"
    v.write_text(GOOD)
    rec = _rec(v)
    signoff.evaluate(rec)
    assert rec["checks"]["netlist_alias"]["verdict"] == "PASS"
    assert not any(r.startswith("netlist_alias") for r in rec["reasons"])


def test_evaluate_without_final_v_adds_no_check():
    rec = dict(corners={}, inputs={}, route={})
    signoff.evaluate(rec)
    assert "netlist_alias" not in rec["checks"]


def test_bundle_ships_the_checker():
    assert "netlist_alias_check.py" in signoff.SIGNOFF_BUNDLE
    assert "netlist_alias_check.py" in signoff.KIT_TOOL_DEPENDENCIES["die_sta.py"]
