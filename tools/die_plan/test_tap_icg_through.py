"""CORES-EARLY-10 (BF G2 CTS 10-29): tap_balance.tb_sinks walks THROUGH integrated clock gates.

Measured on the BF G2 3_5_place_dp.odb (1252 ICGx1): the old walk returned 2091 sinks of which 1252 were ICG CLK
pins (no clock-to-Q arc -> clock_family 'missing unique active clock edge', CTS stopped); the ICG-through walk returns
53852 sinks == all_registers -clock_pins (0 ICG), and ot_cf_wire measures them.  Static check of the clause."""
import re
from pathlib import Path

TCL = Path(__file__).with_name("tap_balance.tcl").read_text()
CLAUSE = '[string match "ICG*" [[$i getMaster] getName]] && [[$it getMTerm] getName] eq "CLK"'


def _tb_sinks():
    m = re.search(r"proc tb_sinks \{net\} \{(.*?)\n\}\n", TCL, re.S)
    assert m, "tb_sinks not found"
    return m.group(1)


def test_icg_clk_is_a_tree_node():
    body = _tb_sinks()
    i = body.find(CLAUSE)
    assert i >= 0
    clause = body[i:body.find("continue", i)]
    # followed through its outputs, never appended as a sink
    assert "lappend todo [$o getNet]" in clause and "lappend out" not in clause
    # decided before the buffer / sink branch
    assert i < body.find("[tb_is_buf $i]")


def test_only_icg_clk_pin_is_followed():
    # ENA / SE pins of an ICG on a clock net still fall to the sink branch (fail closed in clock_family)
    assert _tb_sinks().count('getName] eq "CLK"') == 1
