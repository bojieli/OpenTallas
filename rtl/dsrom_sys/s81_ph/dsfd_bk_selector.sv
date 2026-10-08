`timescale 1ns/1ps
// CLAUDE S81-PH: die view top of the S81 selector slab (ports exactly physical/s81_ph_views/ports/layer/dsfd_bk_selector/
// ports.svh; the head-die master has the same ports, only ck / rst sit elsewhere on the N face).  rst is active low
// (the die reset net, as every r8/r9 glue block); vd is the vr lane {data 512, valid, rst_n} launched from flops at the
// pins; vf is its forwarded clock (ck through the kept forwarding inverter: the first station captures on negedge vf =
// posedge ck, one full cycle).  Function and word formats: ot_s81ph_sel.sv.
module dsfd_bk_selector #(
    parameter integer CMP_RETIME = 0,
    parameter integer PIPE2 = 0, MRG_PIPE = 0, RQPIPE = 0, SLAT = 0,   // CLAUDE s81-blocks variants (ot_s81ph_sel_tile.sv)
    parameter integer SEARCH_PIPE = 1,   // adopted 10-07 (selt_c cd3337221-b SS -541; bench selector/pipeline_r1)
    parameter integer STG  = 6,
    parameter integer PACE = 2,
`ifdef OT_S81PH_SEL_FLAT
    parameter integer TILED = 0,
`else
    parameter integer TILED = 1,             // 1 (redesign pass): ot_s81ph_sel_t composition (ot_s81ph_sel_tile.sv)
`endif
    parameter integer LSTG = 5,
`ifdef OT_S81PH_SEL_SAFE
    parameter integer SAFE = 1
`else
    parameter integer SAFE = 0
`endif
) (
    input wire [0:0] ck,
    input wire [514:0] iNE,
    input wire [514:0] iNW,
    input wire [514:0] iSE,
    input wire [514:0] iSW,
    input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf
);
    generate if (TILED != 0) begin : g_t
        ot_s81ph_sel_t #(.CMP_RETIME(CMP_RETIME), .PIPE2(PIPE2), .MRG_PIPE(MRG_PIPE), .RQPIPE(RQPIPE), .SLAT(SLAT), .SEARCH_PIPE(SEARCH_PIPE), .SAFE(SAFE), .LSTG(LSTG), .PACE(PACE)) u_t (.ck(ck[0]), .rst(rst[0]), .lanes({iNE, iNW, iSE, iSW}),
            .vd(vd), .vf(vf[0]));
    end else begin : g_v
        reg [1:0] rst_s;
        always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
        wire        o_v;
        wire [511:0] o_d;
        ot_s81ph_sel_core #(.STG(STG), .PACE(PACE)) u_core (.clk(ck[0]), .rst_n(rst_s[1]), .lanes({iNE, iNW, iSE, iSW}),
            .o_v(o_v), .o_d(o_d), .dbg_fault());
        reg [513:0] vd_q;
        always @(posedge ck[0]) vd_q <= {o_d, o_v & rst_s[1], rst_s[1]};
        assign vd = vd_q;
        ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
    end endgenerate
endmodule
