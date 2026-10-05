`timescale 1ps/1fs
// Default-off near-HBM streaming-read controller for one HBM3E stack: 32 pseudo-channel
// sequencers (ot_hbm_r14_stream_pc) and 16 per-channel row-command slots (JESD238: 16
// independent channels, each two 32-bit pseudo-channels sharing the channel's C/A).
// Column commands: each PC owns one per controller cycle (CK/2), i.e. half of its channel's
// 1-tCK column slots.  Row commands: one per channel per cycle; the channel's two PCs take
// alternate cycles (TDM).  ENABLE=0 (default) ties every output to zero.
// WR_EN = 1 (default 0): per-PC write queues (ot_hbm_r14_stream_pc WR_EN); col_we flags a WR.
// PULLIN = N (default 0): each PC may refresh up to N REFpb ahead of schedule while not reading.
// AQ_RD = 1 (default 0): wr_rd marks a pushed access-queue entry as a tagged read; col_aq flags its RD.
module ot_qwen_service_stack_aq_act_select #(
  parameter integer AQ_ACT_CUT = 0,
  parameter integer ENABLE = 0, REF_MODE = 1, CRED = 32, PHASE = 0,
  parameter integer T_REFI = 3808, T_REFIPB = 118,
  parameter integer NCH = 16,                  // channels (2 PCs each); 16 = one stack, 1 = a screen slice
  parameter integer WR_EN = 0, WQ = 4,
  parameter integer PULLIN = 0,                // ot_hbm_r14_stream_pc PULLIN (stream-aware refresh pull-in)
  parameter integer AQ_RD = 0                  // ot_hbm_r14_stream_pc AQ_RD (tagged reads in the access queue)
)(
  input  wire          clk, rst_n,
  input  wire          desc_v, output wire desc_r,
  input  wire [18:0]   desc_row, input wire [10:0] desc_n,
  input  wire          go, next_posted,
  output wire [2*NCH-1:0]  row_v, output wire [6*NCH-1:0] row_op, output wire [10*NCH-1:0] row_bank,
  output wire [38*NCH-1:0] row_row,
  output wire [2*NCH-1:0]  col_v, output wire [10*NCH-1:0] col_bank, output wire [10*NCH-1:0] col_col,
  input  wire [6*NCH-1:0]  cred_ret,
  output wire [2*NCH-1:0]  busy, output wire fault,
  input  wire [2*NCH-1:0]  wr_v, input wire [10*NCH-1:0] wr_bank, input wire [10*NCH-1:0] wr_col,
  output wire [2*NCH-1:0]  wr_r, output wire [2*NCH-1:0] col_we,
  input  wire [2*NCH-1:0]  wr_rd, output wire [2*NCH-1:0] col_aq    // AQ_RD only
);
  generate if (AQ_ACT_CUT) begin : candidate
    ot_hbm_r14_stream_stack_aq_act_cut #(.ENABLE(ENABLE), .REF_MODE(REF_MODE), .CRED(CRED), .PHASE(PHASE), .T_REFI(T_REFI), .T_REFIPB(T_REFIPB), .NCH(NCH), .WR_EN(WR_EN), .WQ(WQ), .PULLIN(PULLIN), .AQ_RD(AQ_RD), .AQ_HOLD_LOOKAHEAD(1)) u (.*);
  end else begin : original
    ot_hbm_r14_stream_stack #(.ENABLE(ENABLE), .REF_MODE(REF_MODE), .CRED(CRED), .PHASE(PHASE), .T_REFI(T_REFI), .T_REFIPB(T_REFIPB), .NCH(NCH), .WR_EN(WR_EN), .WQ(WQ), .PULLIN(PULLIN), .AQ_RD(AQ_RD)) u (.*);
  end endgenerate
endmodule
