`timescale 1ns/1ps
// Five speculative slots share split/tag control but have five reduction and
// row-scale datapaths. One reduction tree could only retire one slot per
// cycle and would make short-K matrices (o/down) five times slower; the O4
// sweep requires all five results in parallel. Input partials are final K
// accumulators from the base lanes plus four MAC-only copy lanes.
module ot_hdc_qwen_m5_reduce_scale #(
    parameter integer G = 4, W = 16
) (
    input  wire clk, rst_n, valid,
    input  wire [$clog2(G):0] split_log2,
    input  wire [5*G*W*32-1:0] partial_sum,
    input  wire [G*W*16-1:0] row_scale_bf16,
    output wire out_valid,
    output wire [5*G*W*32-1:0] result,
    output wire fault
);
    localparam integer LG = $clog2(G);
    wire [LG:0] vlevel;
    assign vlevel[0] = valid;
    wire [LG:0] split_level [0:LG];
    assign split_level[0] = split_log2;
    wire [5*G*W*32-1:0] level [0:LG];
    assign level[0] = partial_sum;
    wire [LG:0] tree_fault;
    assign tree_fault[0] = 1'b0;
    genvar l, s, p;
    generate for (l=1;l<=LG;l=l+1) begin : g_level
        reg [LG:0] split_d1, split_d2, delayed_split;
        always @(posedge clk) begin
            split_d1 <= split_level[l-1];
            split_d2 <= split_d1;
            delayed_split <= split_d2;
        end
        reg [LG:0] split_q;
        always @(posedge clk) split_q <= delayed_split;
        assign split_level[l] = split_q;
        reg [3:0] valid_pipe;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) valid_pipe <= 0; else valid_pipe <= {valid_pipe[2:0],vlevel[l-1]};
        assign vlevel[l] = valid_pipe[3];
        wire [5*(G>>l)*W-1:0] faults;
        for (s=0;s<5;s=s+1) begin : g_slot
            for (p=0;p<(G>>l)*W;p=p+1) begin : g_pair
                localparam integer group=p/W, lane=p%W;
                wire [31:0] sum;
                wire bad;
                ot_hdc_qadd u_add (
                    .clk(clk), .rst_n(rst_n), .v(vlevel[l-1] && (split_level[l-1] >= l)),
                    .a(level[l-1][((s*G+2*group)*W+lane)*32 +: 32]),
                    .b(level[l-1][((s*G+2*group+1)*W+lane)*32 +: 32]),
                    .y(sum), .fault(bad));
                reg [31:0] h1, h2, held;
                always @(posedge clk) begin
                    h1 <= level[l-1][((s*G+group)*W+lane)*32 +: 32];
                    h2 <= h1;
                    held <= h2;
                end
                reg [31:0] q;
                always @(posedge clk) q <= (delayed_split >= l) ? sum : held;
                assign level[l][((s*G+group)*W+lane)*32 +: 32] = q;
                assign faults[(s*(G>>l)*W)+p] = bad;
            end
            // Unused upper groups are only pass-throughs. The output mask
            // selects G >> split_log2 groups, as in ot_hdc_matvec.
            for (p=(G>>l)*W;p<G*W;p=p+1) begin : g_rest
                reg [31:0] h1, h2, h3, h4;
                always @(posedge clk) begin
                    h1 <= level[l-1][((s*G*W)+p)*32 +: 32];
                    h2 <= h1; h3 <= h2; h4 <= h3;
                end
                assign level[l][((s*G*W)+p)*32 +: 32] = h4;
            end
        end
        assign tree_fault[l] = |faults;
    end endgenerate
    wire [4:0] scaled_valid;
    wire [5*G*W-1:0] scale_fault;
    generate for (s=0;s<5;s=s+1) begin : g_scale_slot
        reg [4:0] vv;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) vv<=0; else vv<={vv[3:0],vlevel[LG]};
        assign scaled_valid[s]=vv[4];
        for (p=0;p<G*W;p=p+1) begin : g_scale_lane
            ot_hdc_fmul u_scale (
                .clk(clk), .rst_n(rst_n), .v(vlevel[LG]),
                .a(level[LG][((s*G*W)+p)*32 +: 32]),
                .b({row_scale_bf16[p*16 +: 16],16'd0}),
                .y(result[((s*G*W)+p)*32 +: 32]),
                .fault(scale_fault[s*G*W+p]));
        end
    end endgenerate
    assign out_valid = &scaled_valid;
    assign fault = (|tree_fault) || (|scale_fault);
endmodule
