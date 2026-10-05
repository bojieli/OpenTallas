`timescale 1ns/1ps
// R-ARITH reduction of an ordered stream of FP32 block terms.
// Each eight consecutive terms are added sequentially from +0; completed
// chunk sums enter a pairwise tree padded with +0 to a power of two.  The
// arithmetic is the same qualified FP32 RNE pipeline as the reduced core.
//
// One input per cycle is accepted across IL interleaved row slots.  A slot
// cannot be revisited within the adder's five-cycle recurrence; in_ready
// exposes that rule.  With the core's rotating IL>=8 schedule it remains high.
// A final term leaves as out_v after 5*(1+ceil(log2(MAX_BLOCKS/8)))+1
// registered cycles.  The tree costs one FP32 adder per level in addition to
// the chunk adder, plus IL held FP32 words per level.  No P&R claim is made.
module ot_hdc_chunk8_stack #(
    parameter integer IL = 8,
    parameter integer MAX_BLOCKS = 192
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         in_v,
    output wire                         in_ready,
    input  wire                         in_first,
    input  wire                         in_last,
    input  wire [$clog2(IL)-1:0]        in_slot,
    input  wire [31:0]                  in_term,
    input  wire                         in_fault,
    output reg                          out_v,
    output reg  [31:0]                  out_acc,
    output reg  [15:0]                  out_bf16,
    output reg                          out_fault
);
    localparam integer PW = $clog2(IL);
    localparam integer NC = (MAX_BLOCKS + 7) / 8;
    localparam integer LV = $clog2(NC);
    initial begin
        if (IL < 5 || MAX_BLOCKS < 16 || MAX_BLOCKS > 256)
            $error("ot_hdc_chunk8_stack requires IL>=5 and 16<=MAX_BLOCKS<=256");
    end

    reg [31:0] chunk_acc [0:IL-1];
    reg [IL-1:0] chunk_fault;
    reg [7:0] ordinal [0:IL-1];
    reg [PW-1:0] pending_slot [0:4];
    reg [4:0] pending_v;
    integer k;
    reg slot_pending;
    always @* begin
        slot_pending = 1'b0;
        for (integer p = 0; p < 5; p = p + 1)
            if (pending_v[p] && pending_slot[p] == in_slot)
                slot_pending = 1'b1;
    end
    assign in_ready = !slot_pending;
    wire accept = in_v && in_ready;
    wire [7:0] idx = in_first ? 8'd0 : ordinal[in_slot];
    wire start_chunk = idx[2:0] == 3'd0;
    wire end_chunk = in_last || idx[2:0] == 3'd7;
    wire [31:0] add_a = start_chunk ? 32'd0 : chunk_acc[in_slot];
    wire add_bad = in_fault | (!start_chunk && chunk_fault[in_slot]) |
                   (idx >= MAX_BLOCKS);
    wire [31:0] chunk_sum;
    wire chunk_add_fault;
    ot_hdc_fadd u_chunk (.clk(clk), .rst_n(rst_n), .v(accept),
        .a(add_a), .b(in_term), .y(chunk_sum), .fault(chunk_add_fault));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending_v <= 5'd0;
            chunk_fault <= '0;
            for (k = 0; k < IL; k = k + 1) ordinal[k] <= 0;
        end else begin
            pending_v <= {pending_v[3:0], accept};
            if (accept) ordinal[in_slot] <= in_first ? 8'd1 : ordinal[in_slot] + 8'd1;
            if (pending_v[4]) chunk_fault[pending_slot[4]] <= leaf_bad;
        end
    end
    always @(posedge clk) begin
        pending_slot[0] <= in_slot;
        for (integer q = 1; q < 5; q = q + 1) pending_slot[q] <= pending_slot[q-1];
        if (pending_v[4]) chunk_acc[pending_slot[4]] <= chunk_sum;
    end
    wire [PW+2:0] leaf_tag;
    ot_hdc_delay #(.W(PW+3), .D(5)) u_leaf_tag (.clk(clk), .rst_n(rst_n),
        .d({in_slot, end_chunk, in_last, add_bad}), .q(leaf_tag));
    wire leaf_bad = leaf_tag[0] | chunk_add_fault;

    wire [31:0] value [0:LV];
    wire [PW-1:0] slot [0:LV];
    wire [LV:0] event_v, final_v, error_v;
    assign value[0] = chunk_sum;
    assign slot[0] = leaf_tag[PW+2:3];
    assign event_v[0] = pending_v[4] && leaf_tag[2];
    assign final_v[0] = leaf_tag[1];
    assign error_v[0] = leaf_bad;
    genvar level;
    generate for (level = 0; level < LV; level = level + 1) begin : g_tree
        reg [31:0] held [0:IL-1];
        reg [IL-1:0] have, held_error;
        wire pair = event_v[level] && have[slot[level]];
        wire pass = event_v[level] && !have[slot[level]] && final_v[level];
        wire [31:0] added, passed;
        wire add_fault;
        ot_hdc_fadd u_add (.clk(clk), .rst_n(rst_n), .v(pair),
            .a(held[slot[level]]), .b(value[level]), .y(added), .fault(add_fault));
        ot_hdc_delay #(.W(32), .D(5)) u_pass (.clk(clk), .rst_n(rst_n),
            .d(value[level]), .q(passed));
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
        assign error_v[level+1] = tag[1] | (tag[3] && add_fault);
        assign value[level+1] = tag[3] ? added : passed;
    end endgenerate
    wire [32:0] rounded = {1'b0, value[LV]} + 33'h7FFF + {32'd0, value[LV][16]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin out_v <= 1'b0; out_fault <= 1'b0; end
        else begin
            out_v <= event_v[LV] && final_v[LV];
            out_fault <= event_v[LV] && final_v[LV] && error_v[LV];
        end
    end
    always @(posedge clk) begin
        out_acc <= value[LV];
        out_bf16 <= rounded[31:16];
    end
endmodule
