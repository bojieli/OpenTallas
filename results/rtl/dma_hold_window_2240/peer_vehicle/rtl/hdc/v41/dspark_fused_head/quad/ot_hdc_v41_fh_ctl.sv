`timescale 1ns/1ps
// ot_hdc_v41_fh_ctl: the fused head's CONTROL view (r4): ot_hdc_v41_fh_head_top at FPIPE=2 SAFE HQ LRET with only the
// ports that view uses (the lanes retire their own data; the checked endpoint is its own view). No logic of its own.
module ot_hdc_v41_fh_ctl #(
    parameter integer W = 16, G = 4, AW = 24, NW = 16, RETURN_EXTRA = 6, SAFE = 1, OREG = 0,
    parameter integer TW = 1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1
) (
    input  wire clk, rst_n,
    input  wire commit_busy, native_cold_n,
    output wire [3:0] native_permission_capture,
    output wire commit_warm, commit_debt,
    output wire [7:0] commit_id,
    input  wire s3_v_in,
    input  wire [TW-1:0] a_tag_p_in,
    input  wire [G-1:0] wr_en,
    input  wire [G*AW-1:0] wr_addr,
    output wire [G-1:0] ra_re,
    output wire [G*AW-1:0] ra_addr,
    input  wire go_fus,
    input  wire [AW-1:0] i_iaddr,
    input  wire [4:0] busy_in,
    input  wire [G-1:0] o_we1_in,
    input  wire tv_in, ov1_in,
    output wire [TW-1:0] r_tag,
    output wire r_v,
    output wire [G-1:0] o_we,
    output wire fault,
    output wire [G-1:0] q_rok, q_wok,
    output wire [G*9-1:0] q_rrow, q_wrow,
    output wire [G-1:0] q_rv_mid, q_fsel_m, q_iwg_m,
    output wire [AW-1:0] q_iw_e,
    input  wire [23:0] q_warm_word,          // group 0 half 0 o_addr (pre-retirement, warm transaction word)
    input  wire [15:0] q_warm_mask,          // group 0 o_mask
    input  wire [G*W-1:0] q_poison,
    input  wire [2*G-1:0] q_group_fault,
    input  wire ep_ack_v, ep_fault, ep_guard_busy, ep_request_checked_v, ep_reply_checked_v,
    input  wire [7:0] ep_ack_id,
    input  wire [23:0] ep_ack_word,
    input  wire [15:0] ep_ack_mask,
    output wire [G*W-1:0] q_lane_veto
);
    wire u0, u1; wire [2830:0] u2; wire [1266:0] u3; wire [(1+32+NW)*G*W-1:0] u4; wire [G*AW-1:0] u5;
    wire [G*W-1:0] u6; wire [G*W*32-1:0] u7; wire [0:0] u8;
    ot_hdc_v41_fh_head_top #(.W(W),.G(G),.AW(AW),.NW(NW),.FPIPE(2),.SAFE(SAFE),.HQ(1),.LRET(1),.OREG(OREG),.RETURN_EXTRA(RETURN_EXTRA)) u_top (
        .clk(clk),.rst_n(rst_n),.commit_busy(commit_busy),.commit_ack_v(1'b0),
        .native_cold_n(native_cold_n),.native_request_ready(1'b0),.native_reply_capture(1'b0),.native_reply_v(1'b0),
        .native_ordinal(32'b0),.native_request_owner(47'b0),.native_checked_reply(1267'b0),
        .native_request_checked_v(u0),.native_reply_checked_v(u1),.native_permission_capture(native_permission_capture),
        .native_captured_request(u2),.native_captured_reply(u3),
        .commit_ack_id(8'b0),.commit_ack_word(24'b0),.commit_ack_mask(16'b0),
        .commit_warm(commit_warm),.commit_debt(commit_debt),.commit_id(commit_id),
        .s3_v_in(s3_v_in),.a_tag_p_in(a_tag_p_in),.wr_en(wr_en),.wr_addr(wr_addr),.ra_re(ra_re),.ra_addr(ra_addr),
        .go_fus(go_fus),.i_iaddr(i_iaddr),.busy_in(busy_in),.o_we1_in(o_we1_in),.tv_in(tv_in),.ov1_in(ov1_in),
        .r_tag(r_tag),.r_v(r_v),.leaf(u4),.o_we(o_we),.o_addr(u5),.o_mask(u6),.o_data(u7),.fault(fault),.argmax_level1(u8),
        .q_rok(q_rok),.q_rrow(q_rrow),.q_wok(q_wok),.q_wrow(q_wrow),.q_rv_mid(q_rv_mid),.q_fsel_m(q_fsel_m),
        .q_iwg_m(q_iwg_m),.q_iw_e(q_iw_e),.q_leaf({((1+32+NW)*G*W){1'b0}}),.q_o_data({(G*W*32){1'b0}}),
        .q_o_mask({{(G*W-16){1'b0}},q_warm_mask}),.q_o_addr({{(G*AW-24){1'b0}},q_warm_word}),
        .q_poison(q_poison),.q_group_fault(q_group_fault),
        .ep_ack_v(ep_ack_v),.ep_fault(ep_fault),.ep_guard_busy(ep_guard_busy),.ep_request_checked_v(ep_request_checked_v),
        .ep_reply_checked_v(ep_reply_checked_v),.ep_ack_id(ep_ack_id),.ep_ack_word(ep_ack_word),.ep_ack_mask(ep_ack_mask),
        .q_lane_veto(q_lane_veto));
endmodule
