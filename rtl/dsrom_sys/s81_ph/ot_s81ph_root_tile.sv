`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_root_tile -- one S81 region root as an ABUTTED chain tile of dsfd_sp_gather (CLAUDE S81-PH, 2026-10-06).
//
// Why a tile: 128 hardened roots (~12.6k um2 of cells each, 2.15 Mbit of flops in all) do not fit the 1015-um gather
// column as free macros: their 128 x 53 result wires (6,784) would need ~650 um of vertical routing channel between
// macro columns that have ~65 um.  A tile carries its column's results through itself instead: a column of NS tiles
// is a registered shift chain from south to north (the capture abuts the gather's north face), and a lane word
// passes west -> east through a tile to reach the next column (NL thru slots).  Every tile port is a flop at the pin.
//
//   co <= {ci[slots 0 .. NS-2], own result}      own result = slot 0; the tile k rows below the top lands in slot k
//   lto <= lti                                   lane thru (the next tile east takes it as its own lane li)
//   fo <= fi | {busy, fault}                     column status OR chain ({busy, fault} of this lane and root)
//   rso <= reset release chain (async assert passes through every tile at once; release 2 cycles per tile)
// The root itself is ot_s81ph_root_blk's core (ot_s81ph_ret_root_p behind the lane register, PIPE 1).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_root_tile #(
    parameter integer ROOTD = 128,
    parameter integer NS = 32,               // chain slots (tiles per column)
    parameter integer NL = 1                 // lane thru slots
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rs,             // active low, from the tile below (or the gather's synchroniser)
    output wire [0:0]        rso,
    input  wire [68:0]       li,             // own lane {word {fault, busy, e, d32, t32, v}, lane valid}
    input  wire [69*NL-1:0]  lti,
    output reg  [69*NL-1:0]  lto,
    input  wire [53*NS-1:0]  ci,
    output reg  [53*NS-1:0]  co,
    input  wire [1:0]        fi,             // {busy, fault} from the tile below
    output reg  [1:0]        fo
);
    reg [1:0] rst_s;                         // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rl = rst_s[1];
    assign rso = rst_s[1];
    // lane register (valid reset, data not) and lane status
    reg lv; reg [67:0] lw;                   // lw = the 68-b lane word {fault, busy, e, d32, t32, v}
    always @(posedge ck[0] or negedge rl) if (!rl) lv <= 1'b0; else lv <= li[0];
    always @(posedge ck[0]) lw <= li[68:1];
    always @(posedge ck[0]) lto <= lti;
    wire rv, re, rf; wire [15:0] rrow, rbf; wire [2:0] rpos; wire [31:0] rfp;
    ot_s81ph_ret_root_p #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(ck[0]), .rst_n(rl), .i_v(lv & lw[0]), .i_t(lw[32:1]),
        .i_d(lw[64:33]), .i_e(lw[65]), .r_v(rv), .r_row(rrow), .r_pos(rpos), .r_fp32(rfp), .r_bf16(rbf), .r_e(re), .fault(rf));
    reg busy_l, flt_l;
    integer j;
    always @(posedge ck[0] or negedge rl)
        if (!rl) begin busy_l <= 1'b0; flt_l <= 1'b0; fo <= 2'b00; for (j = 0; j < NS; j = j + 1) co[53*j] <= 1'b0; end
        else begin
            if (lv) busy_l <= lw[66];
            if (rf || (lv && lw[67])) flt_l <= 1'b1;
            fo <= fi | {busy_l, flt_l};
            co[0] <= rv;
            for (j = 1; j < NS; j = j + 1) co[53*j] <= ci[53*(j-1)];      // slot valids: reset (no start-up garbage)
        end
    always @(posedge ck[0]) begin
        co[52:1] <= {re, rpos, rrow, rfp};
        for (j = 1; j < NS; j = j + 1) co[53*j + 1 +: 52] <= ci[53*(j-1) + 1 +: 52];
    end
endmodule
