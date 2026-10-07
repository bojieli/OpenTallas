`timescale 1ns/1ps
// ot_hdc_v41_fh_head_q: quadrant-structured fused head = ot_hdc_v41_fh_head_top + 4 x ot_hdc_v41_fh_quad (one hardened
// element, gid strap). Port list of ot_hdc_v41_fh_macro_ctx at MARGIN=1 HARD_LANE=1 (CAPTURE 1, ALAT 7, RETURN_EXTRA 5,
// PROTECT_SPLIT 1, RETIRE 1, VM_ENDPOINT 1, VM_GUARD 1); cycle-identical to it (tb_fh_head_q lockstep). The feed-through
// inputs (res_in, o_addr1_in, o_mask1_in, leaf_mask_in, leaf_row_in, am_idx_in) go straight to quadrant pin flops.
module ot_hdc_v41_fh_head_q #(
    parameter integer W = 16, G = 4, IL = 8, AW = 24, NW = 16, FPIPE = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire commit_busy,commit_ack_v,
    input wire native_cold_n,native_request_ready,native_reply_capture,native_reply_v,
    input wire [31:0] native_ordinal,
    input wire [46:0] native_request_owner,
    input wire [1266:0] native_checked_reply,
    output wire native_request_checked_v,native_reply_checked_v,
    output wire [3:0] native_permission_capture,
    output wire [2830:0] native_captured_request,
    output wire [0:0] native_captured_request_check,
    output wire [1266:0] native_captured_reply,
    output wire [0:0] native_captured_reply_check,
    input wire [7:0] commit_ack_id,
    input wire [23:0] commit_ack_word,
    input wire [15:0] commit_ack_mask,
    output wire commit_warm,commit_debt,
    output wire [7:0] commit_id,
    input  wire              s3_v_in,
    input  wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] a_tag_p_in,
    input  wire [G*W*32-1:0] res_in,
    input wire [G-1:0] wr_en,
    input wire [G*AW-1:0] wr_addr,
    input wire [G*W-1:0] wr_mask,
    input wire [G*W*32-1:0] wr_data,
    output wire [G-1:0]      ra_re,
    output wire [G*AW-1:0]   ra_addr,
    input  wire              go_fus,
    input  wire [AW-1:0]     i_iaddr,
    input  wire [4:0]        busy_in,
    input  wire [G-1:0]      o_we1_in,
    input  wire [G*AW-1:0]   o_addr1_in,
    input  wire [G*W-1:0]    o_mask1_in,
    input  wire [G*W-1:0]    leaf_mask_in,
    input  wire [NW-1:0]     leaf_row_in,
    input  wire              tv_in,
    input  wire              ov1_in,
    input  wire [NW-1:0]     am_idx_in,
    output wire  [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] r_tag,
    output wire               r_v,
    output wire [(1+32+NW)*G*W-1:0] leaf,
    output wire  [G-1:0]      o_we,
    output wire  [G*AW-1:0]   o_addr,
    output wire  [G*W-1:0]    o_mask,
    output wire  [G*W*32-1:0] o_data,
    output wire              fault,
    output wire [0:0] result_capture,
    output wire [0:0] argmax_level1
);
    localparam integer CW = 1 + 32 + NW;
    wire [G-1:0] q_rok, q_rv_mid, q_fsel_m, q_iwg_m, q_group_fault;
    wire [G*9-1:0] q_rrow, q_wrow;
    wire [G-1:0] q_wok;
    wire [G*W-1:0] q_o_mask, q_poison;
    wire [G*W*32-1:0] q_o_data;
    wire [AW-1:0] q_iw_e;
    wire [CW*G*W-1:0] q_leaf;
    wire [G*AW-1:0] q_o_addr;
    assign native_captured_request_check = 1'b0;
    assign native_captured_reply_check = 1'b0;
    assign result_capture = 1'b0;
    ot_hdc_v41_fh_head_top #(.W(W),.G(G),.IL(IL),.AW(AW),.NW(NW),.FPIPE(FPIPE)) u_top (
        .clk(clk),.rst_n(rst_n),.commit_busy(commit_busy),.commit_ack_v(commit_ack_v),
        .native_cold_n(native_cold_n),.native_request_ready(native_request_ready),.native_reply_capture(native_reply_capture),
        .native_reply_v(native_reply_v),.native_ordinal(native_ordinal),.native_request_owner(native_request_owner),
        .native_checked_reply(native_checked_reply),.native_request_checked_v(native_request_checked_v),
        .native_reply_checked_v(native_reply_checked_v),.native_permission_capture(native_permission_capture),
        .native_captured_request(native_captured_request),.native_captured_reply(native_captured_reply),
        .commit_ack_id(commit_ack_id),.commit_ack_word(commit_ack_word),.commit_ack_mask(commit_ack_mask),
        .commit_warm(commit_warm),.commit_debt(commit_debt),.commit_id(commit_id),
        .s3_v_in(s3_v_in),.a_tag_p_in(a_tag_p_in),.wr_en(wr_en),.wr_addr(wr_addr),
        .ra_re(ra_re),.ra_addr(ra_addr),.go_fus(go_fus),.i_iaddr(i_iaddr),.busy_in(busy_in),.o_we1_in(o_we1_in),
        .tv_in(tv_in),.ov1_in(ov1_in),.r_tag(r_tag),.r_v(r_v),.leaf(leaf),.o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),
        .o_data(o_data),.fault(fault),.argmax_level1(argmax_level1),
        .q_rok(q_rok),.q_rrow(q_rrow),.q_wok(q_wok),.q_wrow(q_wrow),.q_rv_mid(q_rv_mid),
        .q_fsel_m(q_fsel_m),.q_iwg_m(q_iwg_m),.q_iw_e(q_iw_e),.q_leaf(q_leaf),.q_o_data(q_o_data),.q_o_mask(q_o_mask),
        .q_o_addr(q_o_addr),.q_poison(q_poison),.q_group_fault(q_group_fault));
    genvar g;
    generate for (g = 0; g < G; g = g + 1) begin : g_quad
        ot_hdc_v41_fh_quad #(.W(W),.AW(AW),.NW(NW)) u_quad (
            .clk(clk),.rst_n(rst_n),.gid(2'(g)),
            .rok(q_rok[g]),.rrow(q_rrow[9*g+:9]),.wok(q_wok[g]),.wrow(q_wrow[9*g+:9]),
            .wr_mask_in(wr_mask[W*g+:W]),.wr_data_in(wr_data[W*32*g+:W*32]),
            .res_in(res_in[W*32*g+:W*32]),.o_mask1_in(o_mask1_in[W*g+:W]),.o_addr1_in(o_addr1_in[AW*g+:AW]),
            .leaf_mask_in(leaf_mask_in[W*g+:W]),.leaf_row_in(leaf_row_in),.am_idx_in(am_idx_in),
            .rv_mid(q_rv_mid[g]),.fsel_m(q_fsel_m[g]),.iwg_m(q_iwg_m[g]),.iw_e(q_iw_e),
            .leaf(q_leaf[CW*W*g+:CW*W]),.o_data(q_o_data[W*32*g+:W*32]),.o_mask(q_o_mask[W*g+:W]),
            .o_addr(q_o_addr[AW*g+:AW]),.poison(q_poison[W*g+:W]),.group_fault(q_group_fault[g]));
    end endgenerate
endmodule
