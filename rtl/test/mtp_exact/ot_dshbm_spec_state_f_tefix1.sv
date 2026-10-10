`timescale 1ns/1ps
// Bench shim (mtp-exact 2026-10-08): presents ot_dshbm_spec_state_f_token_edge with TOKEN_EDGE_FIX = 1 under the
// module name rtl/test/hbm_fmax_ctl/tb_spec_state_lockstep.sv instantiates (ot_dshbm_spec_state_f), so the SAME
// lockstep bench checks the fixed successor.  Compile it instead of the failed f3 source, never together with it.
module ot_dshbm_spec_state_f #(
    parameter integer W = 128, PMAX = 8, WR = 136, SR = 10, TR = 16, NG = 4, NL = 40, NST = 3, NSRC = 4,
    parameter [NSRC*4-1:0] RLOG = 16'h0011,
    parameter integer CKMAX = 1 << 16, TW = 17, AW = 32
) (
    input wire clk, input wire rst_n, input wire n_set, input wire [31:0] n_val, output wire [31:0] n,
    input wire tw_v, input wire [31:0] tw_pos, input wire [TW-1:0] tw_tok,
    input wire req_v, output wire req_ready, input wire [3:0] req_kind, input wire [15:0] req_idx,
    input wire [31:0] req_pos, output wire a_v, output wire [AW-1:0] a_addr, output wire [TW-1:0] a_tok,
    output wire a_pad, output wire a_last, output wire a_err);
    ot_dshbm_spec_state_f_token_edge #(.TOKEN_EDGE_FIX(1), .W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG),
        .NL(NL), .NST(NST), .NSRC(NSRC), .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) u (.*);
endmodule
