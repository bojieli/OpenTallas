`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_segtree: the golden csum padded pairwise tree over one segment's chunk sums, for up to NT
// segments (trees) in flight.  Base nodes of a tree arrive IN ORDER (chunk sums for FP8, chunk-pair
// sums for FP4); `final` marks a tree's last base node.  Per level a held left operand waits for its
// right sibling; a final node with no held sibling passes up unchanged (the golden's +0 padding is
// an identity: no zero here is -0).  The tree logic is ot_hdc_chunk8_stack's (rtl/hdc/v41), keyed by
// tree instead of row slot.  A tree's value leaves as ov at level LV after 5 * LV (+1) cycles.
// ---------------------------------------------------------------------------
module ot_v41_segtree #(
    parameter integer NT = 4,
    parameter integer LV = 4
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     in_v,
    input  wire [$clog2(NT)-1:0]    in_tree,
    input  wire [31:0]              in_val,
    input  wire                     in_final,
    input  wire                     in_err,
    output reg                      ov,
    output reg  [$clog2(NT)-1:0]    otree,
    output reg  [31:0]              oval,
    output reg                      oerr
);
    localparam integer PW = $clog2(NT);
    wire [31:0] value [0:LV];
    wire [PW-1:0] slot [0:LV];
    wire [LV:0] event_v, final_v, error_v;
    assign value[0] = in_val;
    assign slot[0] = in_tree;
    assign event_v[0] = in_v;
    assign final_v[0] = in_final;
    assign error_v[0] = in_err;
    genvar level;
    generate for (level = 0; level < LV; level = level + 1) begin : g_tree
        reg [31:0] held [0:NT-1];
        reg [NT-1:0] have, held_error;
        wire pair = event_v[level] && have[slot[level]];
        wire pass = event_v[level] && !have[slot[level]] && final_v[level];
        wire [31:0] added, passed;
        wire [1:0] aerr;
        wire avo;
        ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(pair),
            .a(held[slot[level]]), .b(value[level]), .y(added), .err(aerr), .valid_out(avo));
        ot_hdc_delay #(.W(32), .D(5)) u_pass (.clk(clk), .rst_n(rst_n), .d(value[level]), .q(passed));
        wire [PW+3:0] tag;
        ot_hdc_delay #(.W(PW+4), .D(5)) u_tag (.clk(clk), .rst_n(rst_n),
            .d({slot[level], pair, final_v[level],
                error_v[level] | (pair && held_error[slot[level]]), pair | pass}), .q(tag));
        reg [4:0] valid_pipe;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                have <= '0;
                held_error <= '0;
                valid_pipe <= 0;
            end else begin
                valid_pipe <= {valid_pipe[3:0], pair | pass};
                if (pair) have[slot[level]] <= 1'b0;
                else if (event_v[level] && !pass) begin
                    have[slot[level]] <= 1'b1;
                    held_error[slot[level]] <= error_v[level];
                end
            end
        end
        always @(posedge clk) if (event_v[level] && !have[slot[level]] && !pass)
            held[slot[level]] <= value[level];
        assign slot[level+1] = tag[PW+3:4];
        assign event_v[level+1] = valid_pipe[4];
        assign final_v[level+1] = tag[2];
        assign error_v[level+1] = tag[1] | (tag[3] && (aerr != 2'd0));
        assign value[level+1] = tag[3] ? added : passed;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov <= 1'b0; oerr <= 1'b0; end
        else begin
            ov <= event_v[LV] && final_v[LV];
            oerr <= event_v[LV] && final_v[LV] && error_v[LV];
        end
    end
    always @(posedge clk) begin
        oval <= value[LV];
        otree <= slot[LV];
    end
endmodule
