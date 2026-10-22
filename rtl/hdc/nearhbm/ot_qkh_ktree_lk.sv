`timescale 1ns/1ps
// KV-DCAL2 10-19 (K.STA.ECTL KPV_LOCKSTEP, ROOT: no blanket lockstep admission; misc_b fold applied in a hard tile).
// ot_qkh_ktree with every lane's registered q-valid read: the K-tree reduction still runs on lane 0's valid (kpv_in[0],
// unchanged timing / data path / cycles), and any lane whose kpv differs from lane 0 in the same edge is a lane fault folded
// into the existing per-lane fault input ahead of the tile's gf_r input register (XOR16 + OR, 2 gate levels, pins still land
// on flops).  The 16 independently clocked / reset lanes are therefore CHECKED in hardware every edge instead of assumed equal:
// a lane released from reset late, a lane valid lost or duplicated, a clock-crossing slip of one lane -> g_f two edges later
// (gf_r -> g_f), the same latency as a lane's own gf.  +0 schedule cycles, +0 flops (gf_r exists), 15 new N-face pins.
// Bench: tools/qwen_kv_die/ktree_lk_bench.sh (rtl/test/qwen_kv_die/tb_qkh_ktree_lk.sv): lockstep miter vs ot_qkh_ktree +
// per-lane skew injection; MUT 1 (lanes 1..15 ignored = the old kpv_in[0]-only wiring) must FAIL.
module ot_qkh_ktree_lk #(
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  kp_in,
    input  wire [15:0]   kpv_in,
    input  wire [15:0]   gf_in,
    output wire [31:0]   sc_d,
    output wire          sc_f,
    output wire          g_f
);
    wire [15:0] lk = (MUT == 1) ? 16'd0 : ({16{kpv_in[0]}} ^ kpv_in);
    // gate lk1 (FAIL reset_landing: rst_n reached the 17-region relay's 19 flops directly): land rst_n at the face in 2
    // registered stages (async assert, synchronous release) and feed the closed relay from the landed net only.
    // +2 release edges on this tile's reset (reset window only; no data / schedule cycle).
    (* keep *) reg rst_l0, rst_l1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_l0 <= 1'b0; rst_l1 <= 1'b0; end
        else begin rst_l0 <= 1'b1; rst_l1 <= rst_l0; end
    ot_qkh_ktree #(.ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .SCALE(SCALE)) u_kt (
        .clk(clk), .rst_n(rst_l1), .kp_in(kp_in), .kpv_in(kpv_in[0]), .gf_in(gf_in | lk),
        .sc_d(sc_d), .sc_f(sc_f), .g_f(g_f));
endmodule
