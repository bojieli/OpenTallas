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
//   lane: own lane from the west (li_w) or the east (li_e) face, chosen by the tied pin sel (1 = east); lane thru
//         both ways: lt_eo <= lt_wi (west -> east), lt_wo <= lt_ei (east -> west).  Every tile is R0 (no mirroring:
//         the die PDN contract's M7 stripes and the pin tracks stay on grid): columns 0/1 take west lanes (column 1
//         via column 0's lt_eo at the y of its li_w), columns 3/2 east lanes (column 2 via column 3's lt_wo)
//   fo <= fi | {busy, fault}                     column status OR chain ({busy, fault} of this lane and root)
//   rso <= reset release chain (async assert passes through every tile at once; release 2 cycles per tile)
// The root itself is ot_s81ph_root_blk's core (ot_s81ph_ret_root_p behind the lane register, PIPE 1).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_root_tile #(
    parameter integer ROOTD = 128,
    parameter integer NS = 32                // chain slots (tiles per column)
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rs,             // active low, from the tile below (or the gather's synchroniser)
    output wire [0:0]        rso,
    input  wire [0:0]        sel,            // tied: 0 = own lane from li_w, 1 = from li_e
    input  wire [68:0]       li_w,           // own lane {word {fault, busy, e, d32, t32, v}, lane valid}
    input  wire [68:0]       li_e,
    input  wire [68:0]       lt_wi,          // lane thru west -> east
    output reg  [68:0]       lt_eo,
    input  wire [68:0]       lt_ei,          // lane thru east -> west
    output reg  [68:0]       lt_wo,
    input  wire [53*NS-1:0]  ci,
    output reg  [53*NS-1:0]  co,
    input  wire [1:0]        fi,             // {busy, fault} from the tile below
    output reg  [1:0]        fo
);
    reg [1:0] rst_s;                         // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rl = rst_s[1];
    assign rso = rst_s[1];
    // lane registers at both faces (valid reset, data not), then the static select
    reg lvw, lve, sel_q; reg [67:0] lww, lwe;
    always @(posedge ck[0] or negedge rl) if (!rl) begin lvw <= 1'b0; lve <= 1'b0; end else begin lvw <= li_w[0]; lve <= li_e[0]; end
    always @(posedge ck[0]) begin lww <= li_w[68:1]; lwe <= li_e[68:1]; sel_q <= sel[0]; end
    always @(posedge ck[0]) begin lt_eo <= lt_wi; lt_wo <= lt_ei; end
    wire lv = sel_q ? lve : lvw;
    wire [67:0] lw = sel_q ? lwe : lww;      // lw = the 68-b lane word {fault, busy, e, d32, t32, v}
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
