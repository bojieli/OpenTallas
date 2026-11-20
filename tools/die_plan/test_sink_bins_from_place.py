"""QC-PLAN-R3 (COORD 11-20, FABLE-CLOSURE lever 4): sink bins rebuilt from a placed kit, in the existing bins form."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sink_bins_from_place as SB  # noqa: E402


def test_bins_are_bin_centres_with_counts():
    got = SB.bins([(0.1, 0.1), (10.0, 5.0), (10.9, 0.2), (21.7, 11.0)], 10.8)
    assert got == [[5.4, 5.4, 2], [16.2, 5.4, 1], [27.0, 16.2, 1]]


def test_cli_writes_the_plan_bins_form(tmp_path):
    t = tmp_path / "s.tsv"
    t.write_text("clk\tu_a\tDFFHQNx1_ASAP7_75t_R\t1.0\t1.0\nclk_t3\tu_b\tDFFHQNx1_ASAP7_75t_R\t2.0\t2.0\n")
    o = tmp_path / "b.json"
    assert SB.main(["bins", str(t), "--type", "x", "--out", str(o)]) == 0
    d = json.loads(o.read_text())
    assert d["n"] == 2 and d["bins"] == [[5.4, 5.4, 2]] and d["bin_um"] == 10.8 and d["type"] == "x"


def test_only_die_clock_nets():
    r = re.compile(SB.NET_RE)
    assert r.match("clk") and r.match("clk_t12")
    assert not r.match("fclk_in_0") and not r.match("clk_c0") and not r.match("clk_t1_buf")
