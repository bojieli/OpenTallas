`timescale 1ns/1ps
// Exact identity-preserving rank-merge mechanism extracted from real HSF0 ctl.
// Transport framing remains outside this component. Six inputs are the two
// physical copies of each of three peers; identity is NEVER truncated to fit64.
// Each81-bit record is {position21,user10,bits32,row17,valid1}.
// Reset pins follow the actual controller's input/hold reset leaves.
module ot_s81hd_rank_merge_hsf0 # (parameter integer MUT_ROW=0)(
 input wire ck,rst_pin_n,rst_hold_n,
 input wire ov_p,input wire[80:0] orec_d,
 input wire[5:0] mrx_v,input wire[6*553-1:0] mrx_d,
 output wire valid,output wire[48:0] row_bits,output wire[30:0] identity,
 output wire tag_fault,copy_fault,nan_fault,check_valid,output wire[6:0] overwrite
);
 localparam integer FW=553;
 localparam[3:0]T_BEST=1;
 integer i;genvar g,k;
 function isnan(input[31:0]x);
  isnan=(x[30:23]==8'hff)&&(x[22:0]!=0);
 endfunction
    reg [5:0] mrv_q; reg [96:0] mrd_q [0:5];                           // only the HSF0 header + BEST payload is read
    always @(posedge ck) for (i = 0; i < 6; i = i + 1) mrd_q[i] <= mrx_d[i*FW +: 97];
    always @(posedge ck or negedge rst_pin_n) if (!rst_pin_n) mrv_q <= 6'd0; else mrv_q <= mrx_v;
    // 7 record slots: 0..5 = mesh lanes, 6 = own; 81 b each in 3 hold registers
    wire [6:0] sl_en;
    wire [7*96-1:0] sl_q;
    generate for (k = 0; k < 6; k = k + 1) begin : g_ms
        assign sl_en[k] = mrv_q[k] && mrd_q[k][3:0] == T_BEST;
        wire [95:0] dk = {15'd0, mrd_q[k][96:16]};
        for (g = 0; g < 3; g = g + 1) begin : g_h
            ot_s81hd_hreg32 u_h (.ck(ck), .en(sl_en[k]), .d(dk[32*g +: 32]), .q(sl_q[96*k + 32*g +: 32]));
        end
    end endgenerate
    assign sl_en[6] = ov_p;
    generate for (g = 0; g < 3; g = g + 1) begin : g_os
        wire [95:0] dk = {15'd0, orec_d};
        ot_s81hd_hreg32 u_h (.ck(ck), .en(ov_p), .d(dk[32*g +: 32]), .q(sl_q[96*6 + 32*g +: 32]));
    end endgenerate
    reg [6:0] sl_l, sl_v;                                              // landed enable (aligned to the hold), slot full
    wire mg_fire = &sl_v;
    reg [6:0] sl_ovw;
    always @(posedge ck or negedge rst_hold_n)
        if (!rst_hold_n) begin sl_l <= 7'd0; sl_v <= 7'd0; end
        else begin sl_l <= sl_en; sl_v <= (sl_v & {7{!mg_fire}}) | sl_l; end
    always @(*) sl_ovw = sl_l & sl_v & {7{!mg_fire}};
    // record fields: slot s -> {pos [80:60], user [59:50], bits [49:18], row [17:1], v [0]}
    // merge stage 1: checks + level-1 compares (own vs pair-0 copy 0, pair-1 copy 0 vs pair-2 copy 0)
    wire [80:0] r_own = sl_q[96*6 +: 81], r_p0 = sl_q[0 +: 81], r_p0b = sl_q[96 +: 81],
                r_p1 = sl_q[192 +: 81], r_p1b = sl_q[288 +: 81], r_p2 = sl_q[384 +: 81], r_p2b = sl_q[480 +: 81];
    // 2-level registered tree (2 edges a level): (own, pair-0) and (pair-1, pair-2), then the final pick
    wire [48:0] c1a, c1b, mg_rb;
    ot_s81hd_pick u_p1a (.ck(ck), .u(r_own[49:1]), .v(r_p0[49:1]), .y(c1a));
    ot_s81hd_pick u_p1b (.ck(ck), .u(r_p1[49:1]), .v(r_p2[49:1]), .y(c1b));
    ot_s81hd_pick u_p2  (.ck(ck), .u(c1a), .v(c1b), .y(mg_rb));
    reg mg1, mg2, mg3, mg4, mchk_tag, mchk_cpy, mchk_nan; reg [30:0] mg_t;   // tag {pos, user} (slots hold until the next record)
    always @(posedge ck) begin
        mg_t <= r_own[80:50];
        mchk_tag <= (r_p0[80:50] != r_own[80:50]) || (r_p1[80:50] != r_own[80:50]) || (r_p2[80:50] != r_own[80:50]);
        mchk_cpy <= (r_p0 != r_p0b) || (r_p1 != r_p1b) || (r_p2 != r_p2b);
        mchk_nan <= isnan(r_own[49:18]) || isnan(r_p0[49:18]) || isnan(r_p1[49:18]) || isnan(r_p2[49:18]);
    end
    always @(posedge ck or negedge rst_hold_n) if (!rst_hold_n) begin mg1 <= 1'b0; mg2 <= 1'b0; mg3 <= 1'b0; mg4 <= 1'b0; end
                                           else begin mg1 <= mg_fire; mg2 <= mg1; mg3 <= mg2; mg4 <= mg3; end
 assign valid=mg4;
 assign row_bits=mg_rb ^ (MUT_ROW ? 49'd1 : 49'd0);
 assign identity=mg_t;
 assign check_valid=mg1;
 assign tag_fault=mchk_tag;assign copy_fault=mchk_cpy;
 assign nan_fault=mchk_nan;assign overwrite=sl_ovw;
endmodule
