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
module ot_hbm_r14_stream_stack_aq_head_ready_cut #(
  parameter integer ENABLE = 0, REF_MODE = 1, CRED = 32, PHASE = 0,
  parameter integer T_REFI = 3808, T_REFIPB = 118,
  parameter integer NCH = 16,                  // channels (2 PCs each); 16 = one stack, 1 = a screen slice
  parameter integer WR_EN = 0, WQ = 4,
  parameter integer PULLIN = 0,                // ot_hbm_r14_stream_pc PULLIN (stream-aware refresh pull-in)
  parameter integer AQ_HOLD_LOOKAHEAD = 0,
  parameter integer AQ_HEAD_READY_LOOKAHEAD = 0,
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
  generate if (!ENABLE) begin : off
    assign desc_r = 0; assign row_v = 0; assign row_op = 0; assign row_bank = 0; assign row_row = 0;
    assign col_v = 0; assign col_bank = 0; assign col_col = 0; assign busy = 0; assign fault = 0;
    assign wr_r = 0; assign col_we = 0; assign col_aq = 0;
  end else begin : on
    localparam integer PERIOD = REF_MODE ? T_REFIPB : T_REFI;
    localparam integer NP = 2 * NCH;
    wire [NP-1:0] req, prio, gnt, pc_r, pc_fault;
    reg  [NCH-1:0] rr;
    reg  arb_fault;
    for (genvar p = 0; p < NP; p = p + 1) begin : pc
      ot_hbm_r14_stream_pc_aq_head_ready_cut #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(p), .CRED(CRED),
        .T_REFI(T_REFI), .T_REFIPB(T_REFIPB), .WR_EN(WR_EN), .WQ(WQ), .PULLIN(PULLIN), .AQ_RD(AQ_RD), .AQ_HOLD_LOOKAHEAD(AQ_HOLD_LOOKAHEAD), .AQ_HEAD_READY_LOOKAHEAD(AQ_HEAD_READY_LOOKAHEAD),
        .REF_PHASE((PHASE + (p * PERIOD) / 32) % PERIOD)) u (
        .clk(clk), .rst_n(rst_n), .desc_v(desc_v && desc_r), .desc_r(pc_r[p]),
        .desc_row(desc_row), .desc_n(desc_n), .go(go), .next_posted(next_posted),
        .row_v(req[p]), .row_prio(prio[p]), .row_gnt(gnt[p]),
        .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]), .row_row(row_row[p*19 +: 19]),
        .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
        .cred_ret(cred_ret[p*3 +: 3]), .busy(busy[p]), .ref_fault(pc_fault[p]),
        .wr_v(wr_v[p]), .wr_bank(wr_bank[p*5 +: 5]), .wr_col(wr_col[p*5 +: 5]), .wr_r(wr_r[p]), .col_we(col_we[p]),
        .wr_rd(wr_rd[p]), .col_aq(col_aq[p]));
    end
    // Row slot per channel: its two PCs alternate cycles (TDM, PC[0] = cycle parity), so no
    // arbitration; two requests in one cycle would be a design fault.
    assign gnt = {NP{1'b1}};
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rr <= 0; arb_fault <= 0; end
      else for (integer c = 0; c < NCH; c = c + 1)
        if (req[2*c] && req[2*c+1]) arb_fault <= 1;
    assign row_v = req & gnt;
    assign desc_r = &pc_r;
    assign fault = arb_fault || (|pc_fault);
  end endgenerate
endmodule
