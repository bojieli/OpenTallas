// GENERATED from rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv (the register bank and the H16 quad parent, verbatim) for the
// parent route, where the quad is a hardened macro (physical/hbm_attn_tile_r/quad_bb.sv).
`timescale 1ns/1ps
(* keep_hierarchy = "yes" *)
module ot_attn_rp_reg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_attn_tile_m6h1p #(
    parameter integer PMID = 0,
    parameter integer POUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    localparam integer PW = 1 + 1618;
    wire [PW-1:0] pk = {rst_n, ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv, ibank, ib};
    wire [PW-1:0] root_q;
    (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_root (.clk(clk), .d(pk), .q(root_q));
    wire [15:0] gov;
    genvar y, x, l;
    generate for (y = 0; y < 2; y = y + 1) begin : g_y
        wire [PW-1:0] row_q, mid_q;
        wire [PW-1:0] mid_c [0:PMID];
        assign mid_c[0] = root_q;
        for (l = 0; l < PMID; l = l + 1) begin : g_mid
            (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_mid (.clk(clk), .d(mid_c[l]), .q(mid_c[l + 1]));
        end
        assign mid_q = mid_c[PMID];
        (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_row (.clk(clk), .d(mid_q), .q(row_q));
        wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
        wire [2:0]    q_ld_bank, q_ibank;
        wire [7:0]    q_ld_grp;
        wire [1023:0] q_ld_w;
        wire [575:0]  q_ib;
        assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 8 * y + 2 * x;
            wire [3:0]   qv, qf, qv0, qf0;
            wire [127:0] qy, qy0;
            ot_attn_tile_m6h1q u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            wire [135:0] oc [0:POUT];
            assign oc[0] = {qv0, qf0, qy0};
            genvar o;
            for (o = 0; o < POUT; o = o + 1) begin : g_out
                (* keep = "true" *) ot_attn_rp_reg #(.W(136)) u_o (.clk(clk), .d(oc[o]), .q(oc[o + 1]));
            end
            assign {qv, qf, qy} = oc[POUT];
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
        end
    end endgenerate
    assign ov = gov[0];
endmodule
