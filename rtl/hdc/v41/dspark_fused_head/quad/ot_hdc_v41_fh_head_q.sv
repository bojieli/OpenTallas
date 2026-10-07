`timescale 1ns/1ps
// ot_hdc_v41_fh_head_q: quadrant-structured fused head = ot_hdc_v41_fh_head_top + 4 x ot_hdc_v41_fh_quad (one hardened
// element, gid strap). Port list of ot_hdc_v41_fh_macro_ctx at MARGIN=1 HARD_LANE=1 (CAPTURE 1, ALAT 7, RETURN_EXTRA 5,
// PROTECT_SPLIT 1, RETIRE 1, VM_ENDPOINT 1, VM_GUARD 1); cycle-identical to it (tb_fh_head_q lockstep). The feed-through
// inputs (res_in, o_addr1_in, o_mask1_in, leaf_mask_in, leaf_row_in, am_idx_in) go straight to quadrant pin flops.
module ot_hdc_v41_fh_head_q #(
    parameter integer W = 16, G = 4, IL = 8, AW = 24, NW = 16, FPIPE = 1, QPIN = 0, SAFE = 0,
    parameter integer HQ = 0,  // 1: eight half-quadrant views (ot_hdc_v41_fh_hquad) instead of four quadrants
    parameter integer LRET = 0 // 1 (needs HQ): lane-local retirement + the checked endpoint as its own view
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
`ifndef SYNTHESIS
    initial if (LRET && !(HQ && SAFE && FPIPE >= 2)) $fatal(1, "LRET needs HQ, SAFE and FPIPE=2 (retirement depth 7)");
`endif
    wire [G-1:0] q_rok, q_rv_mid, q_fsel_m, q_iwg_m;
    wire [(HQ?2:1)*G-1:0] q_group_fault;
    wire [G*9-1:0] q_rrow, q_wrow;
    wire [G-1:0] q_wok;
    wire [G*W-1:0] q_o_mask, q_poison;
    wire [G*W*32-1:0] q_o_data;
    wire [AW-1:0] q_iw_e;
    wire [CW*G*W-1:0] q_leaf;
    wire [G*AW-1:0] q_o_addr;
    wire t_rqv, t_rpv; wire [2830:0] t_creq; wire [1266:0] t_crep;
    wire [CW*G*W-1:0] t_leaf, r_leaf; wire [G*AW-1:0] t_oa, r_oa; wire [G*W-1:0] t_om, r_om; wire [G*W*32-1:0] t_od, r_od;
    wire [0:0] t_am;
    wire ep_ack_v, ep_fault, ep_busy, ep_rqv, ep_rpv; wire [7:0] ep_id; wire [23:0] ep_word; wire [15:0] ep_mask;
    wire [G*W-1:0] q_lane_veto;
    wire [2830:0] ep_creq; wire [1266:0] ep_crep;
    generate if (LRET) begin : g_lret_out
        assign leaf = r_leaf; assign o_addr = r_oa; assign o_mask = r_om; assign o_data = r_od;
        assign native_request_checked_v = ep_rqv; assign native_reply_checked_v = ep_rpv;
        assign native_captured_request = ep_creq; assign native_captured_reply = ep_crep;
        // the checked endpoint view (native VM endpoint copy) on the retired lane slices
        wire [2830:0] ck1; wire [1266:0] ck2; wire bf;
        ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1),.CHECK_PIPE(1),.MARGIN(1),.FPIPE(FPIPE)) u_ep (
            .fast_clk(clk),.cold_n(native_cold_n),
            .request_accept((|o_we)&&native_request_ready),.request_warm(commit_warm),
            .checked_reply_capture(native_reply_capture),.published_reply_v(native_reply_v),
            .native_ordinal(native_ordinal),.request_owner(native_request_owner),.request_id(commit_id),
            .head_we(o_we),.head_addr(r_oa),.head_mask(r_om),.head_data(r_od),
            .checked_reply(native_checked_reply),.bounds_fault(bf),.endpoint_fault(ep_fault),
            .captured_request(ep_creq),.captured_request_check(ck1),.captured_reply(ep_crep),.captured_reply_check(ck2),
            .request_checked_v(ep_rqv),.reply_checked_v(ep_rpv),.guard_busy(ep_busy),
            .head_ack_v(ep_ack_v),.head_ack_id(ep_id),.head_ack_word(ep_word),.head_ack_mask(ep_mask));
        // argmax level-1 stand-in consumer (the glue's role), outside the views
        wire [CW*(G*W/2)-1:0] full;
        for (genvar pp = 0; pp < G*W/2; pp = pp + 1) begin : g_cons
            wire [CW-1:0] x0 = r_leaf[CW*(2*pp)+:CW], x1 = r_leaf[CW*(2*pp+1)+:CW];
            reg [CW-1:0] r0, r1, c;
            always @(posedge clk) begin r0 <= x0; r1 <= x1; end
            wire r0w = r0[CW-1] && (!r1[CW-1] || r0[CW-2-:32] > r1[CW-2-:32] || (r0[CW-2-:32] == r1[CW-2-:32] && r0[NW-1:0] < r1[NW-1:0]));
            always @(posedge clk) c <= r0w ? r0 : r1;
            assign full[CW*pp+:CW] = c;
        end
        localparam integer NF = (CW*(G*W/2)+63)/64;
        wire [NF*64-1:0] ff = {{(NF*64-CW*(G*W/2)){1'b0}}, full};
        reg [NF-1:0] f1; reg f2; integer fi;
        always @(posedge clk) begin for (fi = 0; fi < NF; fi = fi + 1) f1[fi] <= ^ff[fi*64+:64]; f2 <= ^f1; end
        assign argmax_level1 = f2;
    end else begin : g_top_out
        assign leaf = t_leaf; assign o_addr = t_oa; assign o_mask = t_om; assign o_data = t_od; assign argmax_level1 = t_am;
        assign native_request_checked_v = t_rqv; assign native_reply_checked_v = t_rpv;
        assign native_captured_request = t_creq; assign native_captured_reply = t_crep;
        assign {ep_ack_v, ep_fault, ep_busy, ep_rqv, ep_rpv, ep_id, ep_word, ep_mask} = 0;
    end endgenerate
    assign native_captured_request_check = 1'b0;
    assign native_captured_reply_check = 1'b0;
    assign result_capture = 1'b0;
    ot_hdc_v41_fh_head_top #(.W(W),.G(G),.IL(IL),.AW(AW),.NW(NW),.FPIPE(FPIPE),.SAFE(SAFE),.HQ(HQ),.LRET(LRET),.RETURN_EXTRA(5+QPIN)) u_top (
        .clk(clk),.rst_n(rst_n),.commit_busy(commit_busy),.commit_ack_v(commit_ack_v),
        .native_cold_n(native_cold_n),.native_request_ready(native_request_ready),.native_reply_capture(native_reply_capture),
        .native_reply_v(native_reply_v),.native_ordinal(native_ordinal),.native_request_owner(native_request_owner),
        .native_checked_reply(native_checked_reply),.native_request_checked_v(t_rqv),
        .native_reply_checked_v(t_rpv),.native_permission_capture(native_permission_capture),
        .native_captured_request(t_creq),.native_captured_reply(t_crep),
        .commit_ack_id(commit_ack_id),.commit_ack_word(commit_ack_word),.commit_ack_mask(commit_ack_mask),
        .commit_warm(commit_warm),.commit_debt(commit_debt),.commit_id(commit_id),
        .s3_v_in(s3_v_in),.a_tag_p_in(a_tag_p_in),.wr_en(wr_en),.wr_addr(wr_addr),
        .ra_re(ra_re),.ra_addr(ra_addr),.go_fus(go_fus),.i_iaddr(i_iaddr),.busy_in(busy_in),.o_we1_in(o_we1_in),
        .tv_in(tv_in),.ov1_in(ov1_in),.r_tag(r_tag),.r_v(r_v),.leaf(t_leaf),.o_we(o_we),.o_addr(t_oa),.o_mask(t_om),
        .o_data(t_od),.fault(fault),.argmax_level1(t_am),
        .q_rok(q_rok),.q_rrow(q_rrow),.q_wok(q_wok),.q_wrow(q_wrow),.q_rv_mid(q_rv_mid),
        .q_fsel_m(q_fsel_m),.q_iwg_m(q_iwg_m),.q_iw_e(q_iw_e),.q_leaf(q_leaf),.q_o_data(q_o_data),.q_o_mask(q_o_mask),
        .q_o_addr(q_o_addr),.q_poison(q_poison),.q_group_fault(q_group_fault),
        .ep_ack_v(ep_ack_v),.ep_fault(ep_fault),.ep_guard_busy(ep_busy),.ep_request_checked_v(ep_rqv),.ep_reply_checked_v(ep_rpv),
        .ep_ack_id(ep_id),.ep_ack_word(ep_word),.ep_ack_mask(ep_mask),.q_lane_veto(q_lane_veto));
    genvar g, hh;
    generate if (HQ) begin : g_halves
     for (g = 0; g < G; g = g + 1) begin : g_grp
      for (hh = 0; hh < 2; hh = hh + 1) begin : g_half
        localparam integer L0 = W*g + 8*hh;     // first lane of this half
        wire [AW-1:0] oa, roa;
        ot_hdc_v41_fh_hquad #(.W(8),.AW(AW),.NW(NW),.RETURN_EXTRA(5+QPIN),.QPIN(QPIN),.LRET(LRET?7:0)) u_hq (
            .clk(clk),.rst_n(rst_n),.gid(2'(g)),.hid(1'(hh)),
            .rok(q_rok[g]),.rrow(q_rrow[9*g+:9]),.wok(q_wok[g]),.wrow(q_wrow[9*g+:9]),
            .wr_mask_in(wr_mask[L0+:8]),.wr_data_in(wr_data[32*L0+:256]),
            .res_in(res_in[32*L0+:256]),.o_mask1_in(o_mask1_in[L0+:8]),.o_addr1_in(o_addr1_in[AW*g+:AW]),
            .leaf_mask_in(leaf_mask_in[L0+:8]),.leaf_row_in(leaf_row_in),.am_idx_in(am_idx_in),
            .rv_mid(q_rv_mid[g]),.fsel_m(q_fsel_m[g]),.iwg_m(q_iwg_m[g]),.iw_e(q_iw_e),
            .leaf(q_leaf[CW*L0+:CW*8]),.o_data(q_o_data[32*L0+:256]),.o_mask(q_o_mask[L0+:8]),
            .o_addr(oa),.poison(q_poison[L0+:8]),.group_fault(q_group_fault[2*g+hh]),
            .lane_veto_in(q_lane_veto[L0+:8]),.r_leaf(r_leaf[CW*L0+:CW*8]),.r_o_data(r_od[32*L0+:256]),
            .r_o_mask(r_om[L0+:8]),.r_o_addr(roa));
        if (hh == 0) begin : g_oa
            assign q_o_addr[AW*g+:AW] = oa;
            assign r_oa[AW*g+:AW] = roa;
        end
      end
     end
    end else begin : g_quads
    for (g = 0; g < G; g = g + 1) begin : g_quad
        ot_hdc_v41_fh_quad #(.W(W),.AW(AW),.NW(NW),.RETURN_EXTRA(5+QPIN),.QPIN(QPIN)) u_quad (
            .clk(clk),.rst_n(rst_n),.gid(2'(g)),
            .rok(q_rok[g]),.rrow(q_rrow[9*g+:9]),.wok(q_wok[g]),.wrow(q_wrow[9*g+:9]),
            .wr_mask_in(wr_mask[W*g+:W]),.wr_data_in(wr_data[W*32*g+:W*32]),
            .res_in(res_in[W*32*g+:W*32]),.o_mask1_in(o_mask1_in[W*g+:W]),.o_addr1_in(o_addr1_in[AW*g+:AW]),
            .leaf_mask_in(leaf_mask_in[W*g+:W]),.leaf_row_in(leaf_row_in),.am_idx_in(am_idx_in),
            .rv_mid(q_rv_mid[g]),.fsel_m(q_fsel_m[g]),.iwg_m(q_iwg_m[g]),.iw_e(q_iw_e),
            .leaf(q_leaf[CW*W*g+:CW*W]),.o_data(q_o_data[W*32*g+:W*32]),.o_mask(q_o_mask[W*g+:W]),
            .o_addr(q_o_addr[AW*g+:AW]),.poison(q_poison[W*g+:W]),.group_fault(q_group_fault[g]));
    end
    end endgenerate
endmodule
