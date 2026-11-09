`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dchn_kr (DIE-S81-85 2026-11-09, COORD ruling: RXB k_lo face hold safe by construction, +1 pin cycle):
// the S81 RX-BACK form of the Chien / Forney hard tile.  Every input (k_v, k_lo[309:0], k_L, k_any, rst_n) is
// registered ONCE right at its pin (one flop per pin, no logic in front of it), then ot_s81_kp4_dchn (unchanged; HEAD
// and HBM rx_bm3 keep using it) runs behind those registers.  Contract: ot_s81_kp4_dchn_kr == ot_s81_kp4_dchn with
// every input one clk later, so every output (cw_q, apply, o_unc, o_ne, fs, n_corr, n_unc) is exactly one clk later.
// Why: the bare tile's k_lo pins feed cmul logic into Rl/Ro registers on the 250-ps internal tree, so its FF hold
// requirement at the pin was 104-144 ps and the RX-BACK parent padded it with 7,398 HB4 cells (vF GRT overflow 21,571).
// With a pin register the requirement at the pin is the pin register's own (early-leaf) clock arrival + its hold
// time; the hard-core kit places these registers at their pins (face_flops) and clocks them from an early leaf.
// The parent pays the cycle: RX-BACK OT_S81_RCK_RXB_CHNKR uses this tile and waits the words one more (ddly DD + 1).
// ---------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_s81_kp4_dchn_kr #(parameter integer MUT = 0, parameter integer ROOT_COUNT_SPLIT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    k_v,
    input  wire [309:0]  k_lo,
    input  wire [4:0]    k_L,
    input  wire          k_any,
    output wire [543:0]  cw_q,
    output wire [7:0]    apply,
    output wire          o_unc,
    output wire [4:0]    o_ne,
    output wire          fs,
    output wire [31:0]   n_corr, n_unc
);
    // pin registers: plain flops (no reset, no enable), the only load of each input pin
    reg [3:0] kr_v; reg [309:0] kr_lo; reg [4:0] kr_L; reg kr_any; reg kr_rst_n;
    always @(posedge clk) begin
        kr_v <= k_v; kr_lo <= k_lo; kr_L <= k_L; kr_any <= k_any; kr_rst_n <= rst_n;
    end
    ot_s81_kp4_dchn #(.MUT(MUT), .ROOT_COUNT_SPLIT(ROOT_COUNT_SPLIT)) u_core (.clk(clk), .rst_n(kr_rst_n),
        .k_v(kr_v), .k_lo(kr_lo), .k_L(kr_L), .k_any(kr_any), .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne),
        .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
endmodule
