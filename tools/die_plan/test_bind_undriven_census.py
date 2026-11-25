"""UNDRIVEN-CENSUS-1124 (COORD r703, report-only): per-type census of undriven leaf input bits at bind end."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
from test_bind import HAVE_YOSYS  # noqa: E402
from test_bind_open_inputs import audit, binder, tiny  # noqa: E402

PARTS = {"P0": dict(type="A"), "P1": dict(type="A"), "P2": dict(type="B"), "P3": dict(type="C")}


def test_census_counts_open_and_tied_ub_bits_per_type():
    oi = [dict(type="A", partition="P0", n=5, absent=True), dict(type="A", partition="P1", n=3, absent=False),
          dict(type="B", partition="P2", n=2, absent=False, source_leaf=True)]
    c = bind.undriven_census(oi, {"P0": 10, "P2": 7, "P3": 0}, PARTS, {"A": {"dead": 4}},
                             {("B", "m", "x"): [0, 1, 2]})
    a, b = c["types"]["A"], c["types"]["B"]
    assert (a["groups"], a["open_bits"], a["absent_bits"], a["partial_bits"], a["tied_ub_bits"]) == (2, 8, 5, 3, 10)
    assert (a["bits"], a["partitions"], a["bits_max_instance"], a["declared"]["dead"]) == (18, 2, 15, 4)
    assert (b["source_leaf_bits"], b["tied_ub_bits"], b["bits"], b["declared"]["tied"]) == (2, 7, 9, 3)
    assert "C" not in c["types"]
    assert c["report_only"] and (c["types_with_any"], c["bits"], c["open_bits"], c["tied_ub_bits"]) == (2, 27, 10, 17)
    line = bind.undriven_census_line("s81", c)
    assert line.startswith("UNDRIVEN_OPEN_CENSUS die=s81 types=2 bits=27 top=A:18,B:9 open=10 tied_ub=17")


def test_census_empty_die():
    c = bind.undriven_census([], {}, PARTS)
    assert c["types_with_any"] == 0 and c["bits"] == 0
    assert "types=0 bits=0 top=-" in bind.undriven_census_line("kv", c)


def test_audit_records_declared_bits_per_type(tmp_path):
    B = binder(tmp_path, {"clk": [1], "phy_rx": [1] * 1000}, dead=[("phy_rx", i) for i in range(1000, 1043)])
    audit(B)
    assert not B.open_inputs and B.open_inputs_declared["T"]["dead"] == 43
    B = binder(tmp_path, {"clk": [1]})
    audit(B)
    c = bind.undriven_census(B.open_inputs, {}, B.parts, B.open_inputs_declared)
    assert c["types"]["T"]["open_bits"] == c["types"]["T"]["absent_bits"] == 1043


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys")
def test_strict_bind_writes_census_report_only(tmp_path, capsys):
    rc, r, out = tiny(tmp_path)
    oi = json.loads((out / "bind_open_inputs.json").read_text())
    c = oi["census"]
    assert c["report_only"] and c["open_bits"] == oi["n_undriven"] == 8
    assert sum(x["open_bits"] for x in c["types"].values()) == 8
    assert "UNDRIVEN_OPEN_CENSUS die=" in capsys.readouterr().out
