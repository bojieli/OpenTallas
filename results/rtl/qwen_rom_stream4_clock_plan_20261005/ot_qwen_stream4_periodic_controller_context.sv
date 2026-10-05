`timescale 1ps/1fs
// Source-context cut, NOT a runtime replacement or a PHY load model.
// Explicit periodic1024ps physical clock input; exact selected stack instance block.
// Input signals MUST arrive from protected CORE/TCLK CDC service outputs in HCLK.
// Controller reset requires source clock stable + local synchronous release.
// This cut does not install the prospective CDC/PHY services or qualify their loads.
// All input ports below are the actual parent registered-signal boundary.
module ot_qwen_stream4_periodic_controller_context (
 input wire controller_hclk, controller_rst_n, desc_v_q, go_q,
 input wire [18:0] dq_row, input wire [10:0] dq_n,
 input wire [383:0] cred_ret,
 input wire [127:0] wr_v_q, wr_rd_q,
 input wire [639:0] wr_bank_q, wr_col_q,
 output wire desc_r, sfault, busy_all,
 output wire [127:0] row_v, col_v, col_we, col_aq, busy, wr_r,
 output wire [383:0] row_op,
 output wire [639:0] row_bank, col_bank, col_col,
 output wire [2431:0] row_row
);
 localparam integer NSTK=4, NPC=128, CRED=32, PHASE=0, WQ=4, PULLIN=16;
 wire hclk=controller_hclk, rst_n=controller_rst_n;
 wire [NSTK-1:0] desc_rk, sfault_k, busy_k;
 assign desc_r=&desc_rk;
 assign sfault=|sfault_k;
 assign busy_all=&busy_k;
    for (genvar sk = 0; sk < NSTK; sk = sk + 1) begin : stk
        ot_hbm_r14_stream_stack #(.ENABLE(1), .REF_MODE(1), .CRED(CRED), .PHASE(PHASE), .WR_EN(1), .WQ(WQ), .PULLIN(PULLIN),
                                  .AQ_RD(1)) u_ctl (
            .clk(hclk), .rst_n(rst_n), .desc_v(desc_v_q && desc_r), .desc_r(desc_rk[sk]), .desc_row(dq_row), .desc_n(dq_n),
            .go(go_q), .next_posted(1'b0), .row_v(row_v[sk*32 +: 32]), .row_op(row_op[sk*96 +: 96]),
            .row_bank(row_bank[sk*160 +: 160]), .row_row(row_row[sk*608 +: 608]),
            .col_v(col_v[sk*32 +: 32]), .col_bank(col_bank[sk*160 +: 160]), .col_col(col_col[sk*160 +: 160]),
            .cred_ret(cred_ret[sk*96 +: 96]), .busy(busy[sk*32 +: 32]), .fault(sfault_k[sk]),
            .wr_v(wr_v_q[sk*32 +: 32]), .wr_bank(wr_bank_q[sk*160 +: 160]), .wr_col(wr_col_q[sk*160 +: 160]),
            .wr_r(wr_r[sk*32 +: 32]), .col_we(col_we[sk*32 +: 32]),
            .wr_rd(wr_rd_q[sk*32 +: 32]), .col_aq(col_aq[sk*32 +: 32]));
        assign busy_k[sk] = busy[sk*32];
    end

endmodule
