"""S81-SVC-H8W 11-20: lp.py evaluates macro parameter defaults (H = `OT_SVC_HV) under the spec defines and carries the
source's directive preamble into the generated parent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lp  # noqa: E402

SRC = """`timescale 1ns/1ps
`ifndef OT_SVC_HV
`ifdef OT_SVC_H8
`define OT_SVC_HV 8
`else
`define OT_SVC_HV 16
`endif
`endif
module p #(parameter integer H = `OT_SVC_HV) (input wire [H*132+19:0] g);
endmodule
"""


def test_macro_default_follows_define():
    assert lp.source_macros([SRC], [])["OT_SVC_HV"] == "16"
    assert lp.source_macros([SRC], ["OT_SVC_H8"])["OT_SVC_HV"] == "8"
    m = lp.source_macros([SRC], ["OT_SVC_H8"])
    assert lp.eval_width("[H*132+19:0]", {"H": lp.macro_expand("`OT_SVC_HV", m)}) == 1076


def test_spec_value_wins_and_preamble_kept():
    assert lp.source_macros([SRC], ["OT_SVC_HV=4"])["OT_SVC_HV"] == "4"
    pre = lp.source_preamble(SRC, "p")
    assert pre.startswith("`ifndef OT_SVC_HV") and pre.count("`endif") == 2 and "timescale" not in pre
