`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_root_leaf -- NRT S81 region roots as ONE hardened leaf of the gather cluster (s81-gather 2026-10-13).
//
// The gather is 8 columns x 4 rows of this leaf (4 roots each, ot_s81ph_ret_root_s: SRAM queue + CAM-free pairing
// store).  A column is one capture bundle (roots 16 g .. 16 g + 15, leaf k = roots 16 g + 4 k + s); a row is fed from
// its half's outer face.  Every leaf port is a flop at the pin (inputs captured, outputs launched), so every
// inter-leaf net and every cluster pin net is register -> wire -> register.
//   lanes  li = NRT + NLT lane slots {word 68 {fault, busy, e, d32, t32, v}, lane valid} from the outer side:
//          slots 0 .. NRT-1 are this leaf's roots, slots NRT .. are passed on, registered, as lo slots 0 .. NLT-1
//          (the next leaf towards the centre takes its own from slot 0 again)
//   chain  co = {ci (NCI slots from the leaf above), own NRT results}: own result s in slot s, the leaf k rows up the
//          column lands in slots 4 k .. 4 k + 3 of the bottom leaf = the capture bundle order
//          slot = {e, pos3, row16, fp32 32, v}; valids are reset, data is not
//   fo     <= fi | {busy, fault}: column status OR chain, southwards ({busy, fault} of these lanes and roots)
//   rso    reset release chain (async assert passes through every leaf at once; release 2 cycles per leaf)
// Two cell names, one RTL: dsfd_gth_rw (lanes enter on W, leave on E; the W half) and dsfd_gth_re (enter on E, leave
// on W; the E half).  They differ only in the pin faces of their kits: every leaf is placed R0.
// Latency, lane pin -> row at the column bottom, against the flat gather (pin register, root_blk input register,
// root, root_blk output register, die output register): + (leaves passed on the row) + (leaves below in the column)
// - 2 cycles, i.e. -2 .. +4 for the 4 x 4 half; the root itself is cycle-identical to ot_s81ph_ret_root_p.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_root_leaf #(
    parameter integer NRT = 4,               // roots in the leaf
    parameter integer NLT = 12,              // lanes passed on
    parameter integer NCI = 12,              // chain slots from the leaf above
    parameter integer S   = 8,               // open (pos, row, n) slots per root
    parameter integer SRAM = 1
) (
    input  wire                       ck,
    input  wire                       rs,    // active low, async assert; from the leaf above (or the ctl leaf)
    output wire                       rso,
    input  wire [69*(NRT+NLT)-1:0]    li,
    output reg  [69*NLT-1:0]          lo,
    input  wire [53*NCI-1:0]          ci,
    output reg  [53*(NCI+NRT)-1:0]    co,
    input  wire [1:0]                 fi,
    output reg  [1:0]                 fo
);
    reg [1:0] rst_s;                         // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rl = rst_s[1];
    assign rso = rst_s[1];
    // lanes: own slots captured (valid reset), the others passed on (valid reset)
    reg [NRT-1:0] lv; reg [68*NRT-1:0] lw;
    wire [NRT-1:0] rv, re, rf; wire [16*NRT-1:0] rrow, rbf; wire [3*NRT-1:0] rpos; wire [32*NRT-1:0] rfp;
    reg [NRT-1:0] busy_l; reg flt_l;
    integer j;
    always @(posedge ck or negedge rl)
        if (!rl) begin
            lv <= {NRT{1'b0}}; busy_l <= {NRT{1'b0}}; flt_l <= 1'b0; fo <= 2'b00;
            for (j = 0; j < NLT; j = j + 1) lo[69*j] <= 1'b0;
            `ifdef S81PH_GTH_SSA2
            for (j = NRT; j < NCI + NRT; j = j + 1) co[53*j] <= 1'b0;
`else
            for (j = 0; j < NCI + NRT; j = j + 1) co[53*j] <= 1'b0;
`endif
        end else begin
            for (j = 0; j < NRT; j = j + 1) begin
                lv[j] <= li[69*j];
                if (lv[j]) busy_l[j] <= lw[68*j + 66];
                if (rf[j] || (lv[j] && lw[68*j + 67])) flt_l <= 1'b1;
`ifndef S81PH_GTH_SSA2
`ifdef S81PH_MUT_CHAIN
                co[53*j] <= rv[j ^ 1];       // MUTANT: own results of roots 2 i / 2 i + 1 leave in swapped chain slots
`else
                co[53*j] <= rv[j];
`endif
`endif
            end
            for (j = 0; j < NLT; j = j + 1) lo[69*j] <= li[69*(NRT+j)];
            for (j = 0; j < NCI; j = j + 1) co[53*(NRT+j)] <= ci[53*j];      // slot valids: reset (no start-up garbage)
            fo <= fi | {|busy_l, flt_l};
        end
    always @(posedge ck) begin
        for (j = 0; j < NRT; j = j + 1) begin
            lw[68*j +: 68] <= li[69*j + 1 +: 68];
`ifndef S81PH_GTH_SSA2
`ifdef S81PH_MUT_CHAIN
            co[53*j + 1 +: 52] <= {re[j ^ 1], rpos[3*(j ^ 1) +: 3], rrow[16*(j ^ 1) +: 16], rfp[32*(j ^ 1) +: 32]};
`else
            co[53*j + 1 +: 52] <= {re[j], rpos[3*j +: 3], rrow[16*j +: 16], rfp[32*j +: 32]};
`endif
`endif
        end
        for (j = 0; j < NLT; j = j + 1) lo[69*j + 1 +: 68] <= li[69*(NRT+j) + 1 +: 68];
        for (j = 0; j < NCI; j = j + 1) co[53*(NRT+j) + 1 +: 52] <= ci[53*j + 1 +: 52];
    end
`ifdef S81PH_GTH_SSA2
    // Keep the genuine own-result output sampling role separate from the
    // internal core delay-line state; sample the same D at the original edge.
    wire [53*NRT-1:0] own_result_D;
    genvar own;
    generate for (own=0; own<NRT; own=own+1) begin : g_own_D
`ifdef S81PH_MUT_CHAIN
        localparam integer SRC_ROOT = own ^ 1;
`else
        localparam integer SRC_ROOT = own;
`endif
        assign own_result_D[53*own +: 53] = {re[SRC_ROOT], rpos[3*SRC_ROOT +: 3],
            rrow[16*SRC_ROOT +: 16], rfp[32*SRC_ROOT +: 32], rv[SRC_ROOT]};
    end endgenerate
    (* keep_hierarchy = 1, dont_touch = 1 *)
    ot_s81ph_own_output_role #(.NRT(NRT)) u_own_output
        (.ck(ck), .rl(rl), .d(own_result_D), .q(co[53*NRT-1:0]));
`endif
    genvar g;
    generate for (g = 0; g < NRT; g = g + 1) begin : g_r
        ot_s81ph_ret_root_s #(.S(S), .QD(128), .SRAM(SRAM)) u_root (.clk(ck), .rst_n(rl),
            .i_v(lv[g] & lw[68*g]), .i_t(lw[68*g + 1 +: 32]), .i_d(lw[68*g + 33 +: 32]), .i_e(lw[68*g + 65]),
            .r_v(rv[g]), .r_row(rrow[16*g +: 16]), .r_pos(rpos[3*g +: 3]), .r_fp32(rfp[32*g +: 32]),
            .r_bf16(rbf[16*g +: 16]), .r_e(re[g]), .fault(rf[g]));
    end endgenerate
endmodule

// State used by external own-result outputs, independent of used core state.
(* keep_hierarchy = 1, dont_touch = 1 *)
module ot_s81ph_own_output_role #(parameter integer NRT=4) (
    input wire ck, input wire rl, input wire [53*NRT-1:0] d,
    (* keep = 1, dont_touch = 1 *) output reg [53*NRT-1:0] q
);
`ifdef S81PH_MUT_OWN_CO_PHASE
    reg [53*NRT-1:0] stale_D;
    wire [53*NRT-1:0] sample_D = stale_D;
    integer stale_j;
    always @(posedge ck or negedge rl)
        if (!rl) for (stale_j=0; stale_j<NRT; stale_j=stale_j+1) stale_D[53*stale_j] <= 1'b0;
        else for (stale_j=0; stale_j<NRT; stale_j=stale_j+1) stale_D[53*stale_j] <= d[53*stale_j];
    always @(posedge ck)
        for (stale_j=0; stale_j<NRT; stale_j=stale_j+1) stale_D[53*stale_j+1 +: 52] <= d[53*stale_j+1 +: 52];
`else
    wire [53*NRT-1:0] sample_D = d;
`endif
    integer j;
    always @(posedge ck or negedge rl)
        if (!rl) for (j=0; j<NRT; j=j+1) q[53*j] <= 1'b0;
        else for (j=0; j<NRT; j=j+1) q[53*j] <= sample_D[53*j];
    always @(posedge ck)
        for (j=0; j<NRT; j=j+1) q[53*j+1 +: 52] <= sample_D[53*j+1 +: 52];
endmodule

// open-row slots per root of the hardened cells: 8 (256 x 34 store).  Real field-order bound = 4 open (row, pos) per root
// (production binding d9f84be9, 40 layers, golden experts).  The coordinator rule asks S = 16 for a bound <= 8, but the
// S = 16 leaf does not fit the slot: its route stopped at FLOORPLAN_MARGIN (util 0.716 > 0.60 in 190.08 x 164.16, the
// largest leaf the 8 x 4 grid of the 1727.976 x 803.496 slot allows); S = 8 = 2 x the measured bound.  A 9th open row
// raises the sticky capacity fault (bench-observed).  +define+S81PH_GTH_S=16 builds the 512 x 34 store.
`ifndef S81PH_GTH_S
`define S81PH_GTH_S 8
`endif
// the two hardened cells (same RTL; W-fed and E-fed pin plans)
module dsfd_gth_rw (
    input wire ck, input wire rs, output wire rso,
    input wire [1103:0] li, output wire [827:0] lo, input wire [635:0] ci, output wire [847:0] co,
    input wire [1:0] fi, output wire [1:0] fo
);
`ifdef S81PH_LEAF_FF
    localparam integer MEM = 0;              // bench option: flop arrays instead of the macro models
`else
    localparam integer MEM = 1;
`endif
    ot_s81ph_root_leaf #(.NRT(4), .NLT(12), .NCI(12), .S(`S81PH_GTH_S), .SRAM(MEM)) u_l (.ck(ck), .rs(rs), .rso(rso), .li(li), .lo(lo),
        .ci(ci), .co(co), .fi(fi), .fo(fo));
endmodule
module dsfd_gth_re (
    input wire ck, input wire rs, output wire rso,
    input wire [1103:0] li, output wire [827:0] lo, input wire [635:0] ci, output wire [847:0] co,
    input wire [1:0] fi, output wire [1:0] fo
);
`ifdef S81PH_LEAF_FF
    localparam integer MEM = 0;
`else
    localparam integer MEM = 1;
`endif
    ot_s81ph_root_leaf #(.NRT(4), .NLT(12), .NCI(12), .S(`S81PH_GTH_S), .SRAM(MEM)) u_l (.ck(ck), .rs(rs), .rso(rso), .li(li), .lo(lo),
        .ci(ci), .co(co), .fi(fi), .fo(fo));
endmodule
