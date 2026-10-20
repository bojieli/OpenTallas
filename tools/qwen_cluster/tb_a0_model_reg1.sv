`timescale 1ns/1ps
// BENCH-ONLY behavioural model of the A0 stand-in qfd_tile_nk_rp2_romleaf_rr (physical/ref_tile/qfd_c_b16_dv_diag/
// a0_standin/a0_rr_bb.v is a blackbox) for tools/qwen_cluster/bench_reg1.sh.  Never bind it in a die.
// One registered stage on ck, deterministic function of n_a / n_b / tap (+ tile_id), no data reset (static schedule).
// t_out[507:380] carry tap[507:380] (the xstn TDM tap word); n_y uses tap[379:0] only, so the untimed reference in
// tb_qfd_c_b16_reg1.sv can mask exactly those t_out bits; the reg1 == reg1b equivalence covers every bit.
package a0_model_pkg;
  function automatic logic [513:0] f_t(input logic [513:0] a, input logic [513:0] b, input logic [507:0] tap);
    return a ^ {b[0], b[513:1]} ^ {6'b0, tap};
  endfunction
  function automatic logic [513:0] f_y(input logic [513:0] a, input logic [513:0] b, input logic [379:0] tap,
                                       input logic [15:0] tid);
    return (a + {b[256:0], b[513:257]}) ^ {134'b0, tap} ^ {498'b0, tid};
  endfunction
endpackage

module qfd_tile_nk_rp2_romleaf_rr (
    input wire [513:0] n_a, input wire [513:0] n_b, output reg [513:0] t_out, output reg [513:0] n_y,
    output wire tie_lo, output wire tie_hi, input wire [15:0] tile_id, input wire rst_n, input wire [507:0] tap,
    input wire ck_lsl0, ck_lsl1, ck_lsl2, ck_lsl3, ck_lsl4, ck_lsl5, ck_lsl6, ck_lsl7, ck_node,
    input wire ck_fa0, ck_fa1, ck_fa2, ck_fa3, ck_fa4, ck,
    input wire ck_rp0, ck_rp1, ck_rp2, ck_rp3, ck_rp4, ck_rp5, ck_rp6, ck_rp7, ck_rp8, ck_rp9,
    input wire ck_tx0, ck_tx1, ck_tx2, ck_tx3, ck_tx4, ck_tx5, ck_tx6, ck_tx7,
    input wire ck_rsw, ck_rnw, ck_dw, ck_de, ck_rs, ck_rn);
  import a0_model_pkg::*;
  assign tie_lo = 1'b0;
  assign tie_hi = 1'b1;
  initial begin t_out = '0; n_y = '0; end
  always @(posedge ck) begin
    t_out <= f_t(n_a, n_b, tap);
    n_y   <= f_y(n_a, n_b, tap[379:0], tile_id);
  end
endmodule
