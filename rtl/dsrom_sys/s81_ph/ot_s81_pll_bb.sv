`timescale 1ns/1ps
// ot_s81_pll_bb (CLAUDE S81-PH, 2026-10-06): the S81 die PLL -- analog hard IP, a BLACK BOX in synthesis and P&R
// (physical/s81_ph_views/macros/ot_s81_pll_bb: an outline + pin reservation, no timing claim).  Clocking contract
// (rtl/common/ot_ratio_cdc_fifo.sv header): VCO 3.6 GHz, /3 -> ck_stream 1.2 GHz, /4 -> ck_serial 0.9 GHz (related,
// edges on one 277.8 ps grid); ck_hbm = the HBM3E controller clock from the macro's second synthesiser (its
// frequency is the PHY's, unrelated to the stream clock).  lock: all outputs stable; pd (active high) powers down
// and resets the macro.  OT_S81PH_PLL_MODEL: a behavioural model for benches (lock after LOCK_REF refclk edges).
`ifdef OT_S81PH_PLL_MODEL
module ot_s81_pll_bb #(parameter integer LOCK_REF = 20, parameter real T_S = 0.8333, parameter real T_V = 1.1111,
                       parameter real T_H = 1.024) (
    input wire refclk, input wire pd, output reg ck_stream, output reg ck_serial, output reg ck_hbm, output reg lock);
    integer n;
    initial begin ck_stream = 0; ck_serial = 0; ck_hbm = 0; lock = 0; n = 0; end
    always #(T_S / 2) ck_stream = ~ck_stream;
    always #(T_V / 2) ck_serial = ~ck_serial;
    always #(T_H / 2) ck_hbm = ~ck_hbm;
    always @(posedge refclk or posedge pd) if (pd) begin n <= 0; lock <= 1'b0; end
        else if (n < LOCK_REF) n <= n + 1; else lock <= 1'b1;
endmodule
`else
(* blackbox *)
module ot_s81_pll_bb (input wire refclk, input wire pd, output wire ck_stream, output wire ck_serial,
                      output wire ck_hbm, output wire lock);
endmodule
`endif
