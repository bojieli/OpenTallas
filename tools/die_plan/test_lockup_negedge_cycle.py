"""LOCKUP-NEGEDGE (FABLE-FIX-S81-COL-RANKSEAT 11-22, COORD 20:2x): a relay_depth lockup latch in front of a falling-edge captured
core input is one real cycle; the plan row states it (lockup_cycles: 1) and bind / kit-rtl declare D + 1.
    python3 -m pytest -q tools/die_plan/test_lockup_negedge_cycle.py"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import gen_rtl  # noqa: E402
import kit_relay_depth as KRD  # noqa: E402
import schema  # noqa: E402

LK = re.search(r"(module ot_dp_lk\b.*?\nendmodule\n)", gen_rtl.CELLS, re.S).group(1)
TB = r"""`timescale 1ps/1ps
module path #(parameter LK = 0, parameter NEG = 1, parameter EARLY = 205) (input wire clk, input wire [7:0] src, output reg [7:0] rom_q);
    reg [7:0] st; wire [7:0] pin;
    reg clk_rom = 0; always @(clk) clk_rom <= #(833 - EARLY) clk;          // the core tap: same period, EARLY ps ahead
    always @(posedge clk) st <= #67 src;                                    // relay_depth stage
    generate if (LK) begin : g_lk
        wire [7:0] lq; ot_dp_lk #(.W(8)) u_lk (.clk(clk), .d(st), .q(lq)); assign #40 pin = lq;
    end else begin : g_nl assign #40 pin = st; end
    if (NEG) begin : g_n reg [7:0] n; always @(negedge clk_rom) n <= pin; always @(posedge clk_rom) rom_q <= n;
    end else begin : g_p always @(posedge clk_rom) rom_q <= pin; end endgenerate
endmodule
module tb;
    reg clk = 0; always #416.5 clk = ~clk;
    reg [7:0] src = 0; always @(posedge clk) src <= #1 src + 1;
    wire [7:0] a, b, c, d;
    path #(.LK(0), .NEG(1), .EARLY(`E)) p0 (clk, src, a);  path #(.LK(1), .NEG(1), .EARLY(`E)) p1 (clk, src, b);
    path #(.LK(0), .NEG(0), .EARLY(`E)) p2 (clk, src, c);  path #(.LK(1), .NEG(0), .EARLY(`E)) p3 (clk, src, d);
    initial begin #(833*12 + 700); $display("LAT %0d %0d %0d %0d", src - a, src - b, src - c, src - d); $finish; end
endmodule
"""


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("early", [0, 100, 205, 300])
def test_latch_before_a_falling_edge_capture_is_one_cycle(tmp_path, early):
    (tmp_path / "tb.v").write_text(LK + TB)
    subprocess.run(["iverilog", f"-DE={early}", "-o", str(tmp_path / "tb"), str(tmp_path / "tb.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "tb")], capture_output=True, text=True, check=True).stdout
    # falling-edge capture: no latch 2, latch 3 (+1 cycle); rising-edge capture: 2 and 2 (the latch is 0 cycles)
    assert re.search(r"LAT (\d+) (\d+) (\d+) (\d+)", out).groups() == ("2", "3", "2", "2"), out


def _plan(rows):
    return {"partition_types": {"t": {"relay_depth": rows}}}


def test_bind_reads_the_row_cycle():
    rows = [dict(inst="u_e0.u_w", port="xs_q0", side="sink", D=1, lockup=True, lockup_cycles=1),
            dict(inst="u_e0.u_w", port="go", side="sink", D=1, lockup=True), dict(inst="u_y_x", port="o", D=2)]
    assert bind.relay_depth_lockup_cycles(_plan(rows), "t", "u_e0_u_w", "xs_q0") == 1
    assert bind.relay_depth_lockup_cycles(_plan(rows), "t", "u_e0_u_w", "go") == 0
    assert bind.relay_depth_lockup_cycles(_plan(rows), "t", "u_e9_u_w", "xs_q0") == 0 and bind.relay_depth_lockup_cycles({}, "t", "a", "b") == 0
    with pytest.raises(bind.BindError):
        bind.relay_depth_lockup_cycles(_plan([dict(inst="u_a", port="i", side="sink", D=1, lockup_cycles=1)]), "t", "u_a", "i")
    src = (HERE / "bind.py").read_text()
    assert "+ (relay_depth_lockup_cycles(self.plan, tn, sv_id(r), pn) if rd_ else 0), bit=i_)" in src      # declared with D


BOUND = """module t_bound (
    input wire clk,
    input wire [3:0] a
);
    wire [3:0] w;
    assign w = a;
    core u_c (.clk(clk), .i(w));
endmodule
"""


def test_kit_rtl_receipt_declares_d_plus_one():
    txt, rec = KRD.apply(BOUND, "t", [dict(inst="u_c", port="i", side="sink", D=1, lockup=True, lockup_cycles=1)], lambda s: s, lambda s: s)
    assert "ot_dp_lk #(.W(4)) u_lk_xd_u_c_i_k0_0" in txt and rec["rows"][0]["cycles_added"] == 2 and rec["rows"][0]["lockup_cycles"] == 1
    _, rec = KRD.apply(BOUND, "t", [dict(inst="u_c", port="i", side="sink", D=1, lockup=True)], lambda s: s, lambda s: s)
    assert rec["rows"][0]["cycles_added"] == 1 and "lockup_cycles" not in rec["rows"][0]
    with pytest.raises(ValueError):
        KRD.apply(BOUND, "t", [dict(inst="u_c", port="i", side="sink", D=1, lockup_cycles=1)], lambda s: s, lambda s: s)


def test_schema_has_the_key():
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["relay_depth"]["items"]["properties"]
    assert p["lockup_cycles"] == {"type": "integer", "minimum": 0, "maximum": 1}
