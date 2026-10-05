`timescale 1ns/1ps
/* verilator lint_off DECLFILENAME */
// Canonical ascending-order reduction.  Missing sources are positive zero;
// duplicate detection is performed by the endpoint wrapper below.
module ot_reduction_tree #(
    parameter integer SOURCES = 8,
    parameter integer DATA_W = 32
) (
    input  wire [SOURCES-1:0] source_valid,
    input  wire signed [SOURCES*DATA_W-1:0] source_data,
    output wire signed [DATA_W-1:0] sum,
    output wire overflow
);
    localparam integer EXTRA_W = (SOURCES <= 1) ? 1 : $clog2(SOURCES);
    localparam integer REDUCE_W = DATA_W + EXTRA_W;
    localparam integer LEVELS = (SOURCES <= 1) ? 0 : $clog2(SOURCES);
    localparam integer NP = 1 << LEVELS;      // sources, padded to a power of two

    //: A BALANCED TREE, not a serial accumulation.  The loop this replaces added
    //: the sources one at a time into a running total, which is SOURCES
    //: carry-propagate adds back to back -- eight of them at 35 bits wide for the
    //: routed s8 configuration.  Pairwise reduction is ceil(log2(SOURCES)) adds
    //: deep instead: three, not eight.
    //:
    //: The sum is unchanged and this is not an approximation: these are signed
    //: two's-complement integers in a width that cannot overflow before the
    //: final truncation, and integer addition is associative, so no grouping can
    //: give a different total.  Proven against the previous implementation over
    //: every input by SAT miter, in tools/prove_reduction_tree_equivalence.sh.
    wire signed [REDUCE_W-1:0] node [0:2*NP-1];

    genvar i;
    generate
        for (i = 0; i < NP; i = i + 1) begin : leaf
            //: A source that is not valid contributes exactly zero, so masking
            //: here is what lets the tree be a plain sum with no per-level
            //: conditionals.
            wire signed [DATA_W-1:0] raw = (i < SOURCES)
                ? $signed(source_data[i*DATA_W +: DATA_W]) : {DATA_W{1'b0}};
            assign node[NP+i] = ((i < SOURCES) && source_valid[i])
                ? {{(REDUCE_W-DATA_W){raw[DATA_W-1]}}, raw}
                : {REDUCE_W{1'b0}};
        end
        for (i = 1; i < NP; i = i + 1) begin : branch
            assign node[i] = node[2*i] + node[2*i+1];
        end
    endgenerate

    wire signed [REDUCE_W-1:0] work = (NP >= 1) ? node[1] : {REDUCE_W{1'b0}};
    assign sum = work[DATA_W-1:0];
    assign overflow = (work[REDUCE_W-1:DATA_W] != {EXTRA_W{work[DATA_W-1]}});
endmodule

// Tagged collector for a reduced reticle/stage.  Arrival order is arbitrary,
// but emission waits for every expected source and reduces in source-ID order.
module ot_reduction_endpoint #(
    parameter integer SOURCES = 8,
    parameter integer DATA_W = 32,
    parameter integer GROUPS = 2,
    parameter integer TAG_W = 16
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         in_valid,
    output wire                         in_ready,
    input  wire [TAG_W-1:0]             in_tag,
    input  wire [$clog2(SOURCES)-1:0]   in_source,
    input  wire signed [DATA_W-1:0]     in_data,
    input  wire                         in_poison,
    input  wire                         in_last,
    output reg                          out_valid,
    input  wire                         out_ready,
    output reg [TAG_W-1:0]              out_tag,
    output reg signed [DATA_W-1:0]      out_data,
    output reg                          out_poison,
    output reg                          duplicate_error,
    output reg                          unexpected_error
);
    localparam integer SOURCE_INPUT_W = (SOURCES <= 2) ? 1 : $clog2(SOURCES);
    localparam integer REDUCE_EXTRA_W = (SOURCES <= 1) ? 1 : $clog2(SOURCES);
    localparam integer REDUCE_W = DATA_W + REDUCE_EXTRA_W;
    localparam [SOURCE_INPUT_W:0] SOURCES_VALUE = SOURCES[SOURCE_INPUT_W:0];
    integer g;
    integer s;
    reg group_valid [0:GROUPS-1];
    reg [TAG_W-1:0] group_tag [0:GROUPS-1];
    reg [SOURCES-1:0] seen [0:GROUPS-1];
    reg [SOURCES-1:0] expected [0:GROUPS-1];
    reg signed [DATA_W-1:0] data_mem [0:GROUPS-1][0:SOURCES-1];
    reg poison_mem [0:GROUPS-1];
    reg last_mem [0:GROUPS-1];
    integer selected_group;
    reg select_found;
    reg output_found;
    reg all_seen;
    reg signed [REDUCE_W-1:0] reduce_work;
    reg [SOURCES-1:0] expected_mask;
    wire [SOURCES-1:0] in_source_onehot =
        {{(SOURCES-1){1'b0}},1'b1} << in_source;

    assign in_ready = 1'b1; // a group slot is reserved before service issue

    //: PER-GROUP BALANCED TREES, hoisted OUT of the sequential block.
    //:
    //: The emission path used to sum a group's sources with a loop that added
    //: them one at a time into a running total, inside the clocked always block.
    //: That is SOURCES carry-propagate adds in series -- eight at 35 bits for the
    //: routed s8 configuration -- and it sat on the register-to-register path, so
    //: it set the cycle time.  It is why this engine place-and-routed at 455 MHz.
    //:
    //: Each group's sum is now a pairwise tree, ceil(log2(SOURCES)) adds deep,
    //: evaluated continuously outside the always block.  The clocked process only
    //: selects one and registers it.  The sum is identical: signed integer
    //: addition is associative and the reduce width cannot overflow before the
    //: final truncation, so no grouping changes the total.
    localparam integer RED_LEVELS = (SOURCES <= 1) ? 0 : $clog2(SOURCES);
    localparam integer RED_NP     = 1 << RED_LEVELS;

    //: NARROW WAIVER, and the only one in this file. gnode is a strict reduction
    //: TREE, not a cycle: gnode[g][i] depends solely on gnode[g][2i] and
    //: gnode[g][2i+1], so every dependency strictly increases the index, and the
    //: leaves at [RED_NP .. 2*RED_NP-1] depend on nothing inside the array.
    //: Verilator's dependency analysis is per-SIGNAL rather than per-element, so
    //: any array whose elements reference other elements of itself reads as
    //: circular combinational logic. It is a false positive.
    //:
    //: It is waived HERE, at the declaration, rather than by passing -Wno-fatal to
    //: the whole build. A blanket suppression is what let a real SELRANGE error in
    //: ot_mac_lane_packed produce a wrong dot product for three commits.
    /* verilator lint_off UNOPTFLAT */
    wire signed [REDUCE_W-1:0] gnode [0:GROUPS-1][0:2*RED_NP-1];
    /* verilator lint_on UNOPTFLAT */
    wire signed [REDUCE_W-1:0] group_sum [0:GROUPS-1];

    genvar gg, ss;
    generate
        for (gg = 0; gg < GROUPS; gg = gg + 1) begin : gtree
            for (ss = 0; ss < RED_NP; ss = ss + 1) begin : gleaf
                assign gnode[gg][RED_NP+ss] = ((ss < SOURCES) && seen[gg][ss])
                    ? {{(REDUCE_W-DATA_W){data_mem[gg][ss][DATA_W-1]}},
                       data_mem[gg][ss]}
                    : {REDUCE_W{1'b0}};
            end
            for (ss = 1; ss < RED_NP; ss = ss + 1) begin : gbranch
                assign gnode[gg][ss] = gnode[gg][2*ss] + gnode[gg][2*ss+1];
            end
            assign group_sum[gg] = gnode[gg][1];
        end
    endgenerate

    always @* begin
        selected_group = 0;
        select_found = 1'b0;
        for (g = 0; g < GROUPS; g = g + 1) begin
            if (group_valid[g] && group_tag[g] == in_tag && !select_found) begin
                selected_group = g;
                select_found = 1'b1;
            end
        end
        if (!select_found) begin
            for (g = 0; g < GROUPS; g = g + 1) begin
                if (!group_valid[g] && !select_found) begin
                    selected_group = g;
                    select_found = 1'b1;
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_tag <= {TAG_W{1'b0}};
            out_data <= {DATA_W{1'b0}};
            out_poison <= 1'b0;
            duplicate_error <= 1'b0;
            unexpected_error <= 1'b0;
            for (g = 0; g < GROUPS; g = g + 1) begin
                group_valid[g] <= 1'b0;
                group_tag[g] <= {TAG_W{1'b0}};
                seen[g] <= {SOURCES{1'b0}};
                expected[g] <= {SOURCES{1'b0}};
                poison_mem[g] <= 1'b0;
                last_mem[g] <= 1'b0;
            end
        end else begin
            // Retire an emitted group only after downstream acceptance.
            if (out_valid && out_ready) begin
                out_valid <= 1'b0;
                for (g = 0; g < GROUPS; g = g + 1)
                    if (group_valid[g] && group_tag[g] == out_tag)
                        group_valid[g] <= 1'b0;
            end
            if (in_valid && in_ready) begin
                if ({1'b0,in_source} >= SOURCES_VALUE) begin
                    unexpected_error <= 1'b1;
                end else if (!select_found) begin
                    unexpected_error <= 1'b1;
                end else begin
                    if (!group_valid[selected_group]) begin
                        group_valid[selected_group] <= 1'b1;
                        group_tag[selected_group] <= in_tag;
                        // Capture the allocating flit atomically.  A whole-vector
                        // clear followed by a bit-select NBA to the same vector
                        // is simulator-order-sensitive and can lose source 0;
                        // consulting stale seen state can also create a false
                        // duplicate when a retired slot is reused.
                        seen[selected_group] <= in_source_onehot;
                        expected[selected_group] <= {SOURCES{1'b1}};
                        data_mem[selected_group][in_source] <= in_data;
                        poison_mem[selected_group] <= in_poison;
                        last_mem[selected_group] <= in_last;
                    end else begin
                        if (seen[selected_group][in_source]) begin
                            duplicate_error <= 1'b1;
                            poison_mem[selected_group] <= 1'b1;
                        end else begin
                            seen[selected_group][in_source] <= 1'b1;
                            data_mem[selected_group][in_source] <= in_data;
                        end
                        if (in_poison)
                            poison_mem[selected_group] <= 1'b1;
                        if (in_last)
                            last_mem[selected_group] <= 1'b1;
                    end
                end
            end
            // Select the lowest-ID complete group only when the output slot is
            // free.  On a retirement edge, exclude the group being retired;
            // its valid bit does not change until after this process samples
            // the old state.
            if (!out_valid || out_ready) begin
                /* verilator lint_off BLKSEQ */
                output_found = 1'b0;
                for (g = 0; g < GROUPS; g = g + 1) begin
                    expected_mask = expected[g];
                    all_seen = group_valid[g] && last_mem[g] &&
                               ((seen[g] & expected_mask) == expected_mask) &&
                               !(out_valid && out_ready && group_tag[g] == out_tag);
                    if (all_seen && !output_found) begin
                        reduce_work = group_sum[g];
                        out_tag <= group_tag[g];
                        out_data <= reduce_work[DATA_W-1:0];
                        out_poison <= poison_mem[g];
                        out_valid <= 1'b1;
                        output_found = 1'b1;
                    end
                end
                /* verilator lint_on BLKSEQ */
            end
        end
    end
endmodule
/* verilator lint_on DECLFILENAME */
