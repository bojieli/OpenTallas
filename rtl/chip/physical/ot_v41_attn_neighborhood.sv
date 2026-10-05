`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Composition of the group-column cut of the V4.1 attention neighborhood:
// one ot_v41_attn_stage_ctl plus D/32 = 16 ot_v41_attn_col_slice columns.
// Functionally the adopted ot_chip_v41x_window_stage4 (four banks + rotation),
// the WINDOW/CKV beat of ot_chip_v41x_attn_row_merge and the engine's
// ot_hdc_v41x_attn_staging, with every row-wide bus split by group column.
// Die assembly places one control block and 16 column abstracts; this module
// is the netlist-level reference for that placement and the equivalence bench.
// ---------------------------------------------------------------------------
module ot_v41_attn_neighborhood #(
    parameter bit SRAM_MACRO = 1,
    parameter integer POS_W = 21,
    parameter integer USER_W = 10
) (
    input wire clk,
    input wire rst_n,
    input wire inv_v,
    input wire [POS_W-1:0] inv_row,
    input wire fill_v,
    input wire [USER_W-1:0] fill_user,
    input wire [POS_W-1:0] fill_row,
    input wire [4:0] fill_sector,
    input wire [255:0] fill_data,
    input wire fill_last,
    input wire req_v,
    output wire req_ready,
    input wire [USER_W-1:0] req_user,
    input wire [POS_W-1:0] req_first_row,
    input wire [3:0] req_mask,
    output wire rsp_v,
    output wire [USER_W-1:0] rsp_user,
    output wire [POS_W-1:0] rsp_first_row,
    output wire [3:0] rsp_mask,
    output wire [3:0] rsp_valid_mask,
    output wire rsp_fault,
    input wire beat_clr, beat_full,
    input wire [3:0] beat_lane,
    input wire beat_ckv,
    input wire [2303:0] ckv_row,
    input wire [3:0] stg_we,
    input wire [7:0] stg_waddr,
    input wire [7:0] stg_raddr,
    output wire [4*16*265-1:0] stg_q
);
    wire [63:0] code_we;
    wire [3:0] scale_we, rot_ok;
    wire [4:0] slot;
    wire creq_v;
    wire [19:0] raddr;
    wire [7:0] rot_bank;
    ot_v41_attn_stage_ctl #(.POS_W(POS_W), .USER_W(USER_W)) u_ctl (
        .clk(clk), .rst_n(rst_n), .inv_v(inv_v), .inv_row(inv_row),
        .fill_v(fill_v), .fill_user(fill_user), .fill_row(fill_row),
        .fill_sector(fill_sector), .fill_last(fill_last),
        .req_v(req_v), .req_ready(req_ready), .req_user(req_user),
        .req_first_row(req_first_row), .req_mask(req_mask),
        .rsp_v(rsp_v), .rsp_user(rsp_user), .rsp_first_row(rsp_first_row),
        .rsp_mask(rsp_mask), .rsp_valid_mask(rsp_valid_mask), .rsp_fault(rsp_fault),
        .col_code_we(code_we), .col_scale_we(scale_we), .col_slot(slot),
        .col_req_v(creq_v), .col_raddr(raddr), .col_rot_bank(rot_bank), .col_rot_ok(rot_ok));
    genvar g, l;
    generate for (g = 0; g < 16; g = g + 1) begin : g_col
        wire [4*265-1:0] q;
        ot_v41_attn_col_slice #(.SRAM_MACRO(SRAM_MACRO)) u_col (
            .clk(clk), .rst_n(rst_n),
            .fill_code_we(code_we[g*4 +: 4]), .fill_scale_we(scale_we),
            .fill_slot(slot), .fill_code(fill_data), .fill_scale(fill_data[8*g +: 8]),
            .req_v(creq_v), .req_raddr(raddr), .rot_bank(rot_bank), .rot_ok(rot_ok),
            .beat_clr(beat_clr), .beat_full(beat_full), .beat_lane(beat_lane),
            .beat_ckv(beat_ckv),
            .ckv_group({ckv_row[2048+16*g +: 16], ckv_row[128*g +: 128]}),
            .stg_we(stg_we), .stg_waddr(stg_waddr), .stg_raddr(stg_raddr), .stg_q(q));
        for (l = 0; l < 4; l = l + 1) begin : g_lane
            assign stg_q[(l*16+g)*265 +: 265] = q[265*l +: 265];
        end
    end endgenerate
endmodule
