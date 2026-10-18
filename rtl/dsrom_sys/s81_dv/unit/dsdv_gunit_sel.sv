`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT-L1 (2026-10-17): select-network primitives of the partitioned router select (dsdv_gunit_l1f / _l1c).
// Same records and order as rtl/hdc/v41/ot_hdc_select_tree.sv (unchanged): R = {valid, key(value), ~index, ninf}, a
// strict total order over the valid entries of a segment (indices unique; bit 0 = payload, not compared), so every
// bitonic compare-exchange network that sorts by R returns tools/hdc_golden_v41 `topk_lowest_index`'s selection and
// order (the k largest, ties to the LOWER index, -0 == +0).  The difference is the stage packing: TWO (or three, on the
// 11-bit order records) compare-exchanges are chained between registers instead of one (43-bit compare + 2:1 mux is
// ~250 ps; two fit the 833 ps period), which halves the select's registers and its latency.
// ---------------------------------------------------------------------------------------------------------------------

// one combinational compare-exchange of a bitonic network over 8 records: pair (i, i^J); the larger record to i when
// (i & KB) == 0, else to i^J.  SKIP (bench mutant only) passes the records through.
module dsdv_sel_cx8 #(
    parameter integer EW   = 41,
    parameter integer J    = 1,
    parameter integer KB   = 8,
    parameter integer SKIP = 0
) (
    input  wire [8*EW-1:0] d,
    output wire [8*EW-1:0] q
);
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_p
            localparam integer L = i ^ J;
            if (SKIP != 0) begin : g_skip
                assign q[EW*i +: EW] = d[EW*i +: EW];
            end else if (L > i) begin : g_ce
                wire [EW-1:0] a  = d[EW*i +: EW];
                wire [EW-1:0] b  = d[EW*L +: EW];
                wire          gt = a[EW-1:1] > b[EW-1:1];
                wire          s  = (gt == ((i & KB) == 0));
                assign q[EW*i +: EW] = s ? a : b;
                assign q[EW*L +: EW] = s ? b : a;
            end
        end
    endgenerate
endmodule

// full bitonic sorter of 8 records, descending: the six compare-exchanges (KB, J) = (2,1) (4,2) (4,1) (8,4) (8,2) (8,1)
// packed CPS to a registered stage (CPS 2: 3 stages, CPS 3: 2 stages).  ZQ = 1 zeroes the last register when !iv
// (zero-idle output bus).  MUT 10 (bench only): the last compare-exchange of the last 3-exchange stage is skipped.
module dsdv_sel_sort8 #(
    parameter integer EW  = 41,
    parameter integer CPS = 2,
    parameter integer FW  = 3,
    parameter integer ZQ  = 0,
    parameter integer MUT = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [FW-1:0]   fi,          // flags (fi[0] = valid), delayed with the data
    input  wire [8*EW-1:0] d,
    output wire [FW-1:0]   fo,
    output wire [8*EW-1:0] q
);
    localparam integer NS = 6 / CPS;
    // registered stages: stage s takes the previous register (or d) through CPS exchanges
    localparam integer LW = 8 * EW;
    reg  [NS*LW-1:0] r;
    reg  [NS*FW-1:0] f;
    genvar s, k;
    generate
        for (s = 0; s < NS; s = s + 1) begin : g_s
            wire [LW-1:0] t [0:CPS];
            wire [FW-1:0] fin;
            if (s == 0) begin : g_i0
                assign t[0] = d; assign fin = fi;
            end else begin : g_in
                assign t[0] = r[LW*(s-1) +: LW]; assign fin = f[FW*(s-1) +: FW];
            end
            for (k = 0; k < CPS; k = k + 1) begin : g_k
                localparam integer IX = CPS * s + k;               // exchange index 0..5
                localparam integer JJ = (IX == 0 || IX == 2 || IX == 5) ? 1 : (IX == 1 || IX == 4) ? 2 : 4;
                localparam integer KK = (IX == 0) ? 2 : (IX <= 2) ? 4 : 8;
                dsdv_sel_cx8 #(.EW(EW), .J(JJ), .KB(KK), .SKIP(MUT == 10 && CPS == 3 && IX == 5)) u (.d(t[k]), .q(t[k + 1]));
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) f[FW*s +: FW] <= {FW{1'b0}}; else f[FW*s +: FW] <= fin;
            if (ZQ != 0 && s == NS - 1) begin : g_z
                always @(posedge clk) r[LW*s +: LW] <= fin[0] ? t[CPS] : {LW{1'b0}};
            end else begin : g_r
                always @(posedge clk) r[LW*s +: LW] <= t[CPS];
            end
        end
    endgenerate
    assign q  = r[LW*(NS-1) +: LW];
    assign fo = f[FW*(NS-1) +: FW];
endmodule

// top 8 of two descending 8-lists, descending, 2 registered stages: {fold c[i] = max(A[i], B[7-i]), (8,4)} |
// {(8,2), (8,1)}.  Exact for the top K of the union when each input holds its own top K (K <= 8).
module dsdv_sel_merge8 #(
    parameter integer EW = 43,
    parameter integer FW = 3
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [FW-1:0]   fi,
    input  wire [8*EW-1:0] a,
    input  wire [8*EW-1:0] b,
    output reg  [FW-1:0]   fo,
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] c, c1, c2, c3;
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_f
            wire [EW-1:0] x = a[EW*i +: EW];
            wire [EW-1:0] y = b[EW*(7-i) +: EW];
            assign c[EW*i +: EW] = (x[EW-1:1] > y[EW-1:1]) ? x : y;
        end
    endgenerate
    dsdv_sel_cx8 #(.EW(EW), .J(4), .KB(8)) u0 (.d(c), .q(c1));
    reg [8*EW-1:0] s1, s2;
    reg [FW-1:0]   f1;
    dsdv_sel_cx8 #(.EW(EW), .J(2), .KB(8)) u1 (.d(s1), .q(c2));
    dsdv_sel_cx8 #(.EW(EW), .J(1), .KB(8)) u2 (.d(c2), .q(c3));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin f1 <= {FW{1'b0}}; fo <= {FW{1'b0}}; end else begin f1 <= fi; fo <= f1; end
    always @(posedge clk) begin s1 <= c1; s2 <= c3; end
    assign q = s2;
endmodule
