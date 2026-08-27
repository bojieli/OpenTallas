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
    output reg signed [DATA_W-1:0] sum,
    output reg overflow
);
    integer i;
    reg signed [DATA_W:0] work;
    reg signed [DATA_W-1:0] value;
    always @* begin
        work = {(DATA_W+1){1'b0}};
        value = {DATA_W{1'b0}};
        for (i = 0; i < SOURCES; i = i + 1) begin
            if (source_valid[i]) begin
                value = $signed(source_data[i*DATA_W +: DATA_W]);
                work = work + value;
            end
        end
        sum = work[DATA_W-1:0];
        overflow = (work[DATA_W] != work[DATA_W-1]);
    end
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
    localparam integer SRC_W = (SOURCES <= 2) ? 1 : $clog2(SOURCES);
    integer g;
    integer s;
    reg group_valid [0:GROUPS-1];
    reg [TAG_W-1:0] group_tag [0:GROUPS-1];
    reg [SOURCES-1:0] seen [0:GROUPS-1];
    reg [SOURCES-1:0] expected [0:GROUPS-1];
    reg signed [DATA_W-1:0] data_mem [0:GROUPS-1][0:SOURCES-1];
    reg poison_mem [0:GROUPS-1];
    reg last_mem [0:GROUPS-1];
    reg [GROUPS-1:0] done_pending;
    integer selected_group;
    reg found;
    reg all_seen;
    reg signed [DATA_W:0] reduce_work;
    reg [SOURCES-1:0] expected_mask;

    assign in_ready = 1'b1; // a group slot is reserved before service issue

    always @* begin
        selected_group = 0;
        found = 1'b0;
        for (g = 0; g < GROUPS; g = g + 1) begin
            if (group_valid[g] && group_tag[g] == in_tag && !found) begin
                selected_group = g;
                found = 1'b1;
            end
        end
        if (!found) begin
            for (g = 0; g < GROUPS; g = g + 1) begin
                if (!group_valid[g] && !found) begin
                    selected_group = g;
                    found = 1'b1;
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
            done_pending <= {GROUPS{1'b0}};
            for (g = 0; g < GROUPS; g = g + 1) begin
                group_valid[g] <= 1'b0;
                group_tag[g] <= {TAG_W{1'b0}};
                seen[g] <= {SOURCES{1'b0}};
                expected[g] <= {SOURCES{1'b0}};
                poison_mem[g] <= 1'b0;
                last_mem[g] <= 1'b0;
            end
        end else begin
            out_valid <= 1'b0;
            // Retire an emitted group only after downstream acceptance.
            if (out_valid && out_ready) begin
                for (g = 0; g < GROUPS; g = g + 1)
                    if (group_valid[g] && group_tag[g] == out_tag)
                        group_valid[g] <= 1'b0;
            end
            if (in_valid && in_ready) begin
                if (in_source >= SOURCES) begin
                    unexpected_error <= 1'b1;
                end else if (!found) begin
                    unexpected_error <= 1'b1;
                end else begin
                    if (!group_valid[selected_group]) begin
                        group_valid[selected_group] <= 1'b1;
                        group_tag[selected_group] <= in_tag;
                        seen[selected_group] <= {SOURCES{1'b0}};
                        expected[selected_group] <= {SOURCES{1'b1}};
                        poison_mem[selected_group] <= 1'b0;
                        last_mem[selected_group] <= 1'b0;
                    end
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
            // Select the lowest-ID complete group for deterministic output.
            found = 1'b0;
            for (g = 0; g < GROUPS; g = g + 1) begin
                expected_mask = expected[g];
                all_seen = group_valid[g] && last_mem[g] && ((seen[g] & expected_mask) == expected_mask);
                if (all_seen && !found) begin
                    reduce_work = {(DATA_W+1){1'b0}};
                    for (s = 0; s < SOURCES; s = s + 1)
                        if (seen[g][s])
                            reduce_work = reduce_work + data_mem[g][s];
                    out_tag <= group_tag[g];
                    out_data <= reduce_work[DATA_W-1:0];
                    out_poison <= poison_mem[g];
                    out_valid <= 1'b1;
                    found = 1'b1;
                end
            end
        end
    end
endmodule
/* verilator lint_on DECLFILENAME */
