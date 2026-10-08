`timescale 1ns/1ps
// CLAUDE S81-PH: die view top of the S81 collector slab (ports exactly physical/s81_ph_views/ports/layer/
// dsfd_bk_collector/ports.svh; the head-die master has the same ports).  rst is active low (the die reset net, as every
// r8/r9 glue block); vd is the vr lane {data 512, valid, rst_n} launched from flops at the pins; vf is its forwarded
// clock (ck through the kept forwarding inverter: the first station captures on negedge vf = posedge ck, one full
// cycle).  Function, decision and word formats: ot_s81ph_col.sv.
module dsfd_bk_collector #(
    parameter integer STG   = 7,
    parameter integer OSTG  = 1,
    parameter integer DEPTH = 256,
    parameter integer PACE  = 2,
`ifdef OT_S81PH_COL_FLAT
    parameter integer TILED = 0,
`else
    parameter integer TILED = 1,
`endif             // 1 (redesign pass): ot_s81ph_col_t composition (ot_s81ph_col_tile.sv)
    parameter integer HOPS  = 7,             // die stations per direction lane tile <-> merger (tiles.json)
    parameter integer DM    = 12
) (
    input wire [514:0] cNE,
    input wire [514:0] cNW,
    input wire [514:0] cSE,
    input wire [514:0] cSW,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf
);
    generate if (TILED != 0) begin : g_t
        ot_s81ph_col_t #(.HOPS(HOPS), .DEPTH(DEPTH), .DM(DM), .PACE(PACE)) u_t (.ck(ck[0]), .rst(rst[0]),
            .lanes({cNE, cNW, cSE, cSW}), .vd(vd), .vf(vf[0]));
    end else begin : g_v
        reg [1:0] rst_s;
        always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
        wire        o_v;
        wire [511:0] o_d;
        ot_s81ph_col_core #(.STG(STG), .OSTG(OSTG), .DEPTH(DEPTH), .PACE(PACE)) u_core (.clk(ck[0]), .rst_n(rst_s[1]),
            .lanes({cNE, cNW, cSE, cSW}), .o_v(o_v), .o_d(o_d), .dbg_fault());
        reg [513:0] vd_q;
        always @(posedge ck[0]) vd_q <= {o_d, o_v & rst_s[1], rst_s[1]};
        assign vd = vd_q;
        ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
    end endgenerate
endmodule
