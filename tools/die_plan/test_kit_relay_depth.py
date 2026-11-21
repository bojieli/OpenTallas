"""KIT-RD-1 (FABLE-FIX-S81-LEPE 11-20): bind.py kit-rtl honours sink-side relay_depth on hard-core input pins and refuses
any relay_depth row it cannot apply, naming the row (S81 proof6: 4 k_li_r rows were dropped silently)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import kit_relay_depth as KRD  # noqa: E402

BOUND = """module s81p_t_bound (
    input  wire clk,
    input  wire arst_n,
    output wire [3:0] o
);
    wire [0:0] w_u_lep_li0_r;
    wire [3:0] w_u_lep_v;
    wire [1:0] w_u_lnl0_k;
    ot_lep u_u_lep (
        .clk(clk),
        .li0_r(w_u_lep_li0_r),
        .v(w_u_lep_v)
    );
    ot_lnl u_u_lnl0 (
        .ck_k(clk),
        .k_li_r(w_u_lep_li0_r[0]),
        .k_v(w_u_lep_v),
        .k_x({w_u_lep_v[0], w_u_lep_li0_r[0]}),
        .k_o(w_u_lnl0_k)
    );
    assign o = {w_u_lnl0_k, w_u_lnl0_k};
endmodule
"""
CELLS = """module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
  reg [W-1:0] r [0:D-1]; integer i;
  always @(posedge clk) for (i = 0; i < D; i = i + 1) r[i] <= (i == 0) ? d : r[i-1];
  assign q = r[D-1];
endmodule
module ot_lep (input wire clk, output wire [0:0] li0_r, output wire [3:0] v); assign li0_r = 1'b1; assign v = 4'h5; endmodule
module ot_lnl (input wire ck_k, input wire k_li_r, input wire [3:0] k_v, input wire [1:0] k_x, output wire [1:0] k_o);
  assign k_o = {k_li_r, k_v[1]}; endmodule
"""


def leaf(inst):
    return bind.short_id("u_" + bind.sv_id(inst), 90)


def run(rows):
    return KRD.apply(BOUND, "t", rows, leaf, bind.sv_id)


def test_absent_rows_byte_identical():
    assert run(None) == (BOUND, None) and run([]) == (BOUND, None)


def test_sink_row_on_hard_core_input_is_staged():
    txt, rec = run([{"inst": "u_lnl0", "port": "k_li_r", "side": "sink", "D": 1},
                    {"inst": "u_lnl0", "port": "k_v", "side": "sink", "bits": [1, 2], "D": 2}])
    assert rec["applied"] == 2 and rec["bound"] == 0
    assert ".k_li_r(rdk_u_lnl0_k_li_r_k0_out[0])" in txt
    assert "ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_lnl0_k_li_r_k0_0 (.clk(clk), .d(rdk_u_lnl0_k_li_r_k0_in[0:0])" in txt
    assert ".k_v(rdk_u_lnl0_k_v_k1_out)" in txt
    assert len(re.findall(r"u_y_xd_u_lnl0_k_v_k1_\d \(", txt)) == 2           # D 2 = two single-stage relay instances
    assert "assign rdk_u_lnl0_k_v_k1_out[3:3] = rdk_u_lnl0_k_v_k1_in[3:3];" in txt
    assert "assign rdk_u_lnl0_k_v_k1_out[0:0] = rdk_u_lnl0_k_v_k1_in[0:0];" in txt
    assert txt.index("wire [0:0] rdk_u_lnl0_k_li_r_k0_out") < txt.index("u_u_lnl0 (")    # declared before the sink uses it
    assert [r["cycles_added"] for r in rec["rows"]] == [1, 2]
    if shutil.which("iverilog"):
        d = Path(__file__).resolve().parent
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "t.sv"
            f.write_text(CELLS + txt.replace("s81p_t_bound", "top"))
            r = subprocess.run(["iverilog", "-g2012", "-o", str(Path(td) / "a"), str(f)], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr


def test_rows_the_bind_already_emitted_are_left_alone():
    pre = BOUND.replace("    assign o", "    ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_lnl0_k_li_r_0_0 (.clk(clk), .d(w_u_lep_li0_r), .q(x));\n"
                                      "    assign o")
    txt, rec = KRD.apply(pre, "t", [{"inst": "u_lnl0", "port": "k_li_r", "side": "sink", "D": 1},
                                    {"inst": "u_lep", "port": "li0_r", "D": 1}], leaf, bind.sv_id)
    assert txt == pre and rec["applied"] == 0 and rec["bound"] == 2


@pytest.mark.parametrize("row, why", [
    ({"inst": "u_lep", "port": "v", "D": 1}, "row u_lep.v (source side, D 1) is not in the bound module"),
    ({"inst": "u_lnl9", "port": "k_li_r", "side": "sink", "D": 1}, "row u_lnl9.k_li_r: sink instance u_u_lnl9 is not in"),
    ({"inst": "u_lnl0", "port": "k_zz", "side": "sink", "D": 1}, "row u_lnl0.k_zz: u_u_lnl0 has no connection .k_zz"),
    ({"inst": "u_lnl0", "port": "k_v", "side": "sink", "bits": [2, 4], "D": 1}, "row u_lnl0.k_v: bits [2, 4] outside the 4-bit"),
])
def test_rows_it_cannot_apply_are_refused_by_name(row, why):
    with pytest.raises(ValueError) as e:
        run([row])
    assert why in str(e.value)


def test_kit_rtl_runs_it_and_reports_it():
    src = (Path(__file__).resolve().parent / "bind.py").read_text()
    i = src.index("def cmd_kit_rtl")
    body = src[i:src.index("\ndef ", i + 10)]
    assert "kit_relay_depth.apply(btxt, tn, t.get(\"relay_depth\")" in body
    j = body.index("except ValueError as exc:", body.index("kit_relay_depth.apply"))      # the same try: ValueError -> BindError
    assert "raise BindError" in body[j:j + 120] and "try:" not in body[body.index("kit_relay_depth.apply"):j]
    assert "kit_relay_depth.json" in body and "(kit_rd_rep or {}).get(\"applied\")" in body


def test_relay_branch_copies_must_be_bound():
    rows = [{"inst": "u_lep", "copies": [{"name": "u_lnl0", "sinks": ["x"], "D": 0}]}]
    assert KRD.check_branch(BOUND, "t", rows, leaf) == 1
    rows[0]["copies"].append({"name": "u_lep_c1", "sinks": ["y"], "D": 0})
    with pytest.raises(ValueError, match="row u_lep copy u_lep_c1 is not in the bound module"):
        KRD.check_branch(BOUND, "t", rows, leaf)
    src = (Path(__file__).resolve().parent / "bind.py").read_text()
    assert "kit_relay_depth.check_branch(btxt, tn, t.get(\"relay_branch\")" in src


def test_concatenation_of_plain_items_is_staged():
    # RESET-RELAY-GEN-1530 11-21: {a[0], b[0]} (an S81 lane pad .d({eb, b})) is a stageable connection: bits of it get stages
    txt, rec = run([{"inst": "u_lnl0", "port": "k_x", "side": "sink", "bits": [0, 0], "D": 2}])
    assert rec["applied"] == 1 and rec["rows"][0]["bits"] == [0, 0]
    assert "assign rdk_u_lnl0_k_x_k0_in = {w_u_lep_v[0], w_u_lep_li0_r[0]};" in txt
