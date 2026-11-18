"""RCK-REBALANCE-1 (FABLE-FIX-S81-SERDES2 11-18): branch-level rebalance plan on extracted arrivals."""
import json
from pathlib import Path

import rck_rebalance as R

HERE = Path(__file__).resolve().parent

TREE = """K\tPORT\tb0
K\tb0\tbL
K\tb0\tbR
K\tbR\tbR1
K\tbR\tbR2
S\tbL\tfa/CLK\t2000.00
S\tbL\tfb/CLK\t1990.00
S\tbR1\tfc/CLK\t1850.00
S\tbR1\tfd/CLK\t1856.00
S\tbR2\tmem/clk\t1900.00
X\tbR\t100\t200
X\tbR1\t110\t210
X\tbR2\t120\t220
"""


def _plan(tmp_path, **kw):
    t = tmp_path / "tree.tsv"
    t.write_text(TREE)
    kids, sinks, loc = R.load_tree(t)
    return R.plan(kids, sinks, **kw), kids, sinks


def test_whole_branch_is_padded_before_its_leaves(tmp_path):
    pl, _, _ = _plan(tmp_path, stage=24.0, tol=8.0)
    # bR latest sink 1900: gap 100 - 8 = 92 -> 3 pairs (72) on the whole branch; then bR1 (1856 + 72 = 1928): gap 64 -> 2 pairs
    assert pl["pads"] == {"bR": 3, "bR1": 2}
    assert pl["add"] == {"fa/CLK": 0.0, "fb/CLK": 0.0, "fc/CLK": 120.0, "fd/CLK": 120.0, "mem/clk": 72.0}
    assert pl["before"] == (1850.0, 2000.0) and pl["after"] == (1970.0, 2000.0)
    assert pl["target"] == 2000.0 and not pl["capped"]


def test_no_sink_is_made_later_than_the_target_and_the_cap_holds(tmp_path):
    pl, _, sinks = _plan(tmp_path, stage=24.0, tol=0.0)
    arr = {p: a for n in sinks for p, a in sinks[n]}
    assert max(arr[p] + pl["add"][p] for p in arr) <= pl["target"]
    capped, _, _ = _plan(tmp_path, stage=24.0, tol=8.0, max_pads=4)
    assert sum(capped["pads"].values()) == 4 and capped["capped"]
    one, _, _ = _plan(tmp_path, stage=24.0, tol=8.0, max_per_node=1)
    assert one["pads"] == {"bR": 1, "bR1": 1, "bR2": 1}


def test_reprice_moves_setup_and_hold_in_opposite_directions():
    add = {"fa": 0.0, "fc": 120.0, "mem": 72.0}
    rows = [("max", -100.0, "fa", "fc/D"), ("min", 5.0, "fa", "fc/D"), ("max", -10.0, "fc", "mem/wd_in[3]"),
            ("max", -5.0, "x", "y/D")]
    out = R.reprice(rows, add)
    assert out[0][:3] == ("max", -100.0, 20.0)         # capture 120 later: setup gains 120
    assert out[1][:3] == ("min", 5.0, -115.0)          # the same shift costs hold
    assert out[2][:3] == ("max", -10.0, -58.0)         # launch +120, capture +72
    assert len(out) == 3                               # a path outside the tree is left out


def test_cli_writes_the_plan_and_the_prediction(tmp_path):
    (tmp_path / "tree.tsv").write_text(TREE)
    (tmp_path / "cen.tsv").write_text("max\t-100.00\tfa\tfc/D\tck\tck\nmin\t30.00\tfc\tfa/D\tck\tck\n")
    assert R.main(["plan", str(tmp_path / "tree.tsv"), "--paths", str(tmp_path / "cen.tsv"), "--out", str(tmp_path / "o")]) == 0
    res = json.loads((tmp_path / "o" / "plan.json").read_text())
    assert res["pad_pairs"] == 5 and res["span_before_ps"] == 150.0 and res["span_after_ps"] == 30.0
    assert (tmp_path / "o" / "pads.tsv").read_text().splitlines()[0] == "bR\t3\t100\t200"
    assert res["paths"][0]["worst_after_ps"] == 20.0 and res["paths"][0]["below_gate_after"] == 0
    assert res["paths"][1]["worst_after_ps"] == 150.0  # hold: launch 120 later


def test_dump_script_reuses_the_balance_tree_walk_and_only_reads():
    t = (HERE / "rck_tree_dump.tcl").read_text()
    assert "subtree_balance.tcl" in t and "set ::env(OT_STB) 0" in t and "stb::build" in t and "stb::arr" in t
    assert "array names ::stb::kids \"$" not in t           # no glob on the port name (bus brackets)
    code = "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#"))
    for banned in ("_create", "_destroy", "write_db", "detailed_placement", "connect"):
        assert banned not in code, banned


def test_escaped_bus_names_match_the_census_spelling(tmp_path):
    (tmp_path / "t.tsv").write_text("K\tPORT\tb\nS\tb\tu.o\\[441\\]$_DFF_/CLK\t10.00\t9.00\n")
    _, sinks, _ = R.load_tree(tmp_path / "t.tsv")
    assert sinks["b"] == [("u.o[441]$_DFF_/CLK", 10.0)]


def test_startpoint_given_as_the_clock_pin_is_priced_too():
    out = R.reprice([("min", 10.0, "fa/CLK", "fc/D"), ("max", 0.0, "fc/CLK", "fa/D")], {"fa": 0.0, "fc": 48.0})
    assert out[0][2] == -38.0 and out[1][2] == -48.0
