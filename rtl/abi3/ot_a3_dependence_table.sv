`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 dependence table (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.6).
//
// One entry per issue-record-store slot, each holding up to A3_DEP_RANGES
// byte ranges {object, lo, hi, write} of the outstanding operation: the
// bounding ranges of its resolved views (ot_a3_view_resolver's B stage), the
// scale objects those views name as whole-object read ranges, the
// COMMUNICATION descriptor's local range for LINK and the resource objects for
// STATE.  An instruction issues only when none of its ranges conflicts with
// an outstanding one: overlap is object equality and interval intersection
// on half-open [lo, hi), and a conflict is a read against an outstanding
// write (RAW), a write against an outstanding write (WAW) or a write against
// an outstanding read (WAR).  Two check ports serve two ranges per cycle,
// registered one cycle later, against every range of every live entry.
//
// Conservative choices, each recorded (section 3.6 calls the table
// conservative by design; false stalls change timing and nothing else):
//
//   * the object field is 16 bits, not the [13:0] of section 3.6: the HBM
//     profiles admit up to 65,536 descriptors;
//   * a range on an object the entry already holds merges into it (lo = min,
//     hi = max, write |= write) -- a union that may cover bytes between two
//     disjoint views, never fewer than either;
//   * a range that finds no free slot and no object to merge with sets the
//     entry's wild bit, which conflicts with every check until the entry
//     is released;
//   * frontier streaming is not implemented: the frontier of every entry is
//     zero, so a consumer stalls until its producer completes.  Section 3.6
//     makes streaming non-architectural, and this campaign is the guard that
//     nothing observable depends on it.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_dependence_table #(
    parameter integer ENTRIES = ot_a3_pkg::A3_IRS_ENTRIES,
    parameter integer RANGES  = ot_a3_pkg::A3_DEP_RANGES
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          clear,

    // insert one range into an entry (one per cycle)
    input  wire          insert_valid,
    input  wire [4:0]    insert_slot,
    input  wire [15:0]   insert_object,
    input  wire [39:0]   insert_lo,
    input  wire [39:0]   insert_hi,
    input  wire          insert_write,

    // two check ports; conflict registered one cycle after check_valid
    input  wire          check0_valid,
    input  wire [15:0]   check0_object,
    input  wire [39:0]   check0_lo,
    input  wire [39:0]   check0_hi,
    input  wire          check0_write,
    output reg           check0_conflict,
    input  wire          check1_valid,
    input  wire [15:0]   check1_object,
    input  wire [39:0]   check1_lo,
    input  wire [39:0]   check1_hi,
    input  wire          check1_write,
    output reg           check1_conflict,

    // release the whole entry
    input  wire          release_valid,
    input  wire [4:0]    release_slot,

    output reg  [7:0]    dbg_ranges_used     // live ranges, for observation
);
    localparam integer TOTAL = ENTRIES * RANGES;

    reg [ENTRIES-1:0] entry_valid;
    reg [ENTRIES-1:0] wild;
    reg [TOTAL-1:0]   range_valid;
    reg [15:0] range_object [0:TOTAL-1];
    reg [39:0] range_lo     [0:TOTAL-1];
    reg [39:0] range_hi     [0:TOTAL-1];
    reg [TOTAL-1:0]   range_write;

    // -- checks -------------------------------------------------------------
    function automatic range_conflicts;
        input        rv;
        input [15:0] robject;
        input [39:0] rlo;
        input [39:0] rhi;
        input        rwrite;
        input [15:0] cobject;
        input [39:0] clo;
        input [39:0] chi;
        input        cwrite;
        begin
            range_conflicts = rv && (robject == cobject) &&
                              (rlo < chi) && (clo < rhi) &&
                              (cwrite || rwrite);
        end
    endfunction

    reg conflict0;
    reg conflict1;
    integer e;
    integer r;
    always @* begin
        conflict0 = 1'b0;
        conflict1 = 1'b0;
        for (e = 0; e < ENTRIES; e = e + 1) begin
            if (entry_valid[e] && wild[e]) begin
                conflict0 = 1'b1;
                conflict1 = 1'b1;
            end
            for (r = 0; r < RANGES; r = r + 1) begin
                if (range_conflicts(entry_valid[e] && range_valid[e*RANGES + r],
                                    range_object[e*RANGES + r],
                                    range_lo[e*RANGES + r],
                                    range_hi[e*RANGES + r],
                                    range_write[e*RANGES + r],
                                    check0_object, check0_lo, check0_hi,
                                    check0_write))
                    conflict0 = 1'b1;
                if (range_conflicts(entry_valid[e] && range_valid[e*RANGES + r],
                                    range_object[e*RANGES + r],
                                    range_lo[e*RANGES + r],
                                    range_hi[e*RANGES + r],
                                    range_write[e*RANGES + r],
                                    check1_object, check1_lo, check1_hi,
                                    check1_write))
                    conflict1 = 1'b1;
            end
        end
    end

    // -- insert: merge, fill, or wild ------------------------------------
    // One loop variable per process: a variable shared between processes
    // is two drivers to the synthesis front end.
    reg        ins_merge;
    reg [2:0]  ins_merge_index;
    reg        ins_free;
    reg [2:0]  ins_free_index;
    integer    m;
    always @* begin
        ins_merge = 1'b0;
        ins_merge_index = 3'd0;
        ins_free = 1'b0;
        ins_free_index = 3'd0;
        for (m = RANGES - 1; m >= 0; m = m - 1) begin
            if (range_valid[insert_slot*RANGES + m] &&
                (range_object[insert_slot*RANGES + m] == insert_object)) begin
                ins_merge = 1'b1;
                ins_merge_index = m[2:0];
            end
            if (!range_valid[insert_slot*RANGES + m]) begin
                ins_free = 1'b1;
                ins_free_index = m[2:0];
            end
        end
    end
    wire [31:0] merge_index_wide = insert_slot * RANGES + ins_merge_index;
    wire [31:0] free_index_wide  = insert_slot * RANGES + ins_free_index;
    wire [6:0]  merge_index_full = merge_index_wide[6:0];
    wire [6:0]  free_index_full  = free_index_wide[6:0];

    // -- the merge comparison, BEFORE the index mux ------------------------
    // The worst path of the whole microsequencer ran
    // ``issue_slot_q -> deps.range_hi``: the merge search picks an index, a
    // 128-way 40-bit mux reads that range's bound, a 40-bit comparison decides
    // whether to widen it, and a 128-way demux writes it back -- mux, then
    // compare, then write, all in one cycle.  At a 2.9 ns target that path had
    // 2 ps of slack, so this reduction *was* the control plane's clock.
    //
    // The comparison does not depend on which index wins, so it is done for
    // every range in parallel and only its one-bit result is muxed.  The path
    // becomes max(merge search, 40-bit compare) -> 1-bit mux -> write enable
    // instead of merge search -> 40-bit mux -> 40-bit compare -> write.
    // Semantics are untouched: same widening rule, same cycle, same latency,
    // no interlock and no new hazard -- only the order of a mux and a compare.
    wire [TOTAL-1:0] merge_lo_lt;
    wire [TOTAL-1:0] merge_hi_gt;
    genvar gc;
    generate
        for (gc = 0; gc < TOTAL; gc = gc + 1) begin : g_merge_cmp
            assign merge_lo_lt[gc] = insert_lo < range_lo[gc];
            assign merge_hi_gt[gc] = insert_hi > range_hi[gc];
        end
    endgenerate

    reg [7:0] used;
    integer c;
    always @* begin
        used = 8'd0;
        for (c = 0; c < TOTAL; c = c + 1)
            used = used + {7'd0, range_valid[c]};
    end

    integer q;
    integer rr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            entry_valid <= {ENTRIES{1'b0}};
            wild <= {ENTRIES{1'b0}};
            range_valid <= {TOTAL{1'b0}};
            range_write <= {TOTAL{1'b0}};
            for (q = 0; q < TOTAL; q = q + 1) begin
                range_object[q] <= 16'd0;
                range_lo[q] <= 40'd0;
                range_hi[q] <= 40'd0;
            end
            check0_conflict <= 1'b0;
            check1_conflict <= 1'b0;
            dbg_ranges_used <= 8'd0;
        end else begin
            check0_conflict <= check0_valid && conflict0;
            check1_conflict <= check1_valid && conflict1;
            dbg_ranges_used <= used;
            if (clear) begin
                entry_valid <= {ENTRIES{1'b0}};
                wild <= {ENTRIES{1'b0}};
                range_valid <= {TOTAL{1'b0}};
            end else begin
                if (release_valid) begin
                    entry_valid[release_slot] <= 1'b0;
                    wild[release_slot] <= 1'b0;
                    for (rr = 0; rr < RANGES; rr = rr + 1)
                        range_valid[release_slot*RANGES + rr] <= 1'b0;
                end
                if (insert_valid) begin
                    entry_valid[insert_slot] <= 1'b1;
                    if (ins_merge) begin
                        if (merge_lo_lt[merge_index_full])
                            range_lo[merge_index_full] <= insert_lo;
                        if (merge_hi_gt[merge_index_full])
                            range_hi[merge_index_full] <= insert_hi;
                        range_write[merge_index_full] <=
                            range_write[merge_index_full] | insert_write;
                    end else if (ins_free) begin
                        range_valid[free_index_full] <= 1'b1;
                        range_object[free_index_full] <= insert_object;
                        range_lo[free_index_full] <= insert_lo;
                        range_hi[free_index_full] <= insert_hi;
                        range_write[free_index_full] <= insert_write;
                    end else begin
                        wild[insert_slot] <= 1'b1;
                    end
                end
            end
        end
    end
endmodule
