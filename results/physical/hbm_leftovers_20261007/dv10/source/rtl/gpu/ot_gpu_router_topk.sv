`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Router top-K selector of the V4.1 HBM comparator (W19 B2): the K = 6 experts
// of one token from its N = 384 router values  bi = scores + bias  (FP32),
// exactly hdc_golden_v41.topk_lowest_index (value descending, the lower index
// first on ties), emitted sorted by expert id (the golden runs and sums the
// experts in id order; the fetch path fetches them in that order).
//
// ORDER.  Each value becomes an unsigned key: FP32 bits with -0 canonicalised
// to +0 (the golden compares in float64, where -0 == +0), then the sign-flip
// map (negative: ~bits, non-negative: bits | 1 << 31), which orders every
// non-NaN FP32 like the reals.  The full key {valid, value key, ~index} is
// strictly totally ordered (indices are unique), so "larger key" is exactly
// the golden's rank order and every compare-swap below is on plain unsigned
// integers.
//
// DATAPATH (1.2 GHz: every stage one comparator level + a mux, registered).
//   lanes    P lanes, lane j takes the value of index b * P + j on beat b and
//            keeps its own sorted top-8 list with a one-cycle compare-insert
//            (8 parallel comparators against the new key, then a shift);
//   tree     log2(P) levels merge two sorted 8-lists into their top 8: one
//            registered max(A_i, B_7-i) stage (the union's top 8 as a bitonic
//            sequence) and the three registered half-cleaner stages that sort
//            it (4 cycles a level);
//   by id    the final top K (entries 0..K-1, the rest marked invalid) go
//            through a registered 8-input bitonic sorter on {~valid, index}
//            (6 stages) and leave ascending by id.
// Latency from the last beat: 1 + 4 log2(P) + 6 + 1 cycles; one vector per
// N / P cycles (lanes restart on the beat after in_last).
// ---------------------------------------------------------------------------
module ot_gpu_topk_cs #(
    parameter integer W = 42,
    parameter integer N = 8,
    parameter integer KB = 8,       // bitonic block (direction from i & KB)
    parameter integer J = 4,        // compare distance
    parameter integer DESC = 1      // 1: larger first
) (
    input  wire           clk,
    input  wire [N*W-1:0] d,
    output reg  [N*W-1:0] q
);
    integer i, l;
    reg [W-1:0] a, b;
    reg up;
    always @(posedge clk) begin
        for (i = 0; i < N; i = i + 1) q[i*W +: W] <= d[i*W +: W];
        for (i = 0; i < N; i = i + 1) begin
            l = i ^ J;
            if (l > i) begin
                a = d[i*W +: W]; b = d[l*W +: W];
                up = (((i & KB) == 0) ? 1'b1 : 1'b0) ^ (DESC != 0);   // up: ascending pair
                if (up ? (a > b) : (a < b)) begin
                    q[i*W +: W] <= b; q[l*W +: W] <= a;
                end
            end
        end
    end
endmodule

// two descending 8-lists -> their top 8, descending (4 registered stages)
module ot_gpu_topk_merge #(parameter integer W = 42) (
    input  wire           clk,
    input  wire [8*W-1:0] a,
    input  wire [8*W-1:0] b,
    output wire [8*W-1:0] q
);
    reg [8*W-1:0] s0;
    integer i;
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1)
            s0[i*W +: W] <= (a[i*W +: W] > b[(7-i)*W +: W]) ? a[i*W +: W] : b[(7-i)*W +: W];
    wire [8*W-1:0] s1, s2;
    ot_gpu_topk_cs #(.W(W), .KB(8), .J(4), .DESC(1)) c1 (.clk(clk), .d(s0), .q(s1));
    ot_gpu_topk_cs #(.W(W), .KB(8), .J(2), .DESC(1)) c2 (.clk(clk), .d(s1), .q(s2));
    ot_gpu_topk_cs #(.W(W), .KB(8), .J(1), .DESC(1)) c3 (.clk(clk), .d(s2), .q(q));
endmodule

module ot_gpu_router_topk #(
    parameter integer N  = 384,
    parameter integer P  = 16,      // values a beat (power of two)
    parameter integer K  = 6,       // <= 8
    parameter integer IW = 9
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire [P*32-1:0]   in_vals,     // indices b*P .. b*P+P-1 of the vector, lane j at [32j +: 32]
    input  wire              in_last,     // the vector's last beat
    output wire              out_valid,
    output wire [K*IW-1:0]   out_ids      // ascending, id 0 at [IW-1:0]
);
    localparam integer W = 1 + 32 + IW;
    localparam integer LP = $clog2(P);
    localparam integer DEPTH_T = 4 * LP;
    // ---- lanes ----
    reg [IW-1:0] beat_base;
    reg          fresh;                            // the next beat starts a vector
    reg [8*W-1:0] lane [0:P-1];
    reg [8*W-1:0] lane_fin [0:P-1];
    reg           fin_v;
    function automatic [31:0] okey(input [31:0] f);
        reg [31:0] c;
        begin
            c = (f == 32'h8000_0000) ? 32'h0 : f;       // -0 -> +0
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [8*W-1:0] insert(input [8*W-1:0] lst, input [W-1:0] x);
        integer i;
        reg gt_i, gt_p;
        begin
            for (i = 0; i < 8; i = i + 1) begin
                gt_i = lst[i*W +: W] > x;
                gt_p = (i == 0) ? 1'b1 : (lst[(i-1)*W +: W] > x);
                insert[i*W +: W] = gt_i ? lst[i*W +: W] : (gt_p ? x : lst[(i-1)*W +: W]);
            end
        end
    endfunction
    integer j;
    reg [8*W-1:0] base_l, nl;
    reg [IW-1:0] idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            beat_base <= 0; fresh <= 1'b1; fin_v <= 1'b0;
            for (j = 0; j < P; j = j + 1) lane[j] <= {8*W{1'b0}};
        end else begin
            fin_v <= in_valid && in_last;
            if (in_valid) begin
                for (j = 0; j < P; j = j + 1) begin
                    base_l = fresh ? {8*W{1'b0}} : lane[j];
                    idx = beat_base + j;
                    nl = insert(base_l, {1'b1, okey(in_vals[32*j +: 32]), ~idx});
                    lane[j] <= nl;
                    lane_fin[j] <= nl;
                end
                beat_base <= in_last ? {IW{1'b0}} : beat_base + P;
                fresh <= in_last;
            end
        end
    end
    // ---- merge tree ----
    wire [8*W-1:0] lvl [0:2*P-2];                  // heap order: node n has children 2n+1, 2n+2; leaves P-1 ..
    genvar g;
    generate
        for (g = 0; g < P; g = g + 1) begin : g_leaf
            assign lvl[P - 1 + g] = lane_fin[g];
        end
        for (g = P - 2; g >= 0; g = g - 1) begin : g_node
            ot_gpu_topk_merge #(.W(W)) m (.clk(clk), .a(lvl[2*g+1]), .b(lvl[2*g+2]), .q(lvl[g]));
        end
    endgenerate
    // valid pipe through the tree (4 per level) and the id sort (6)
    reg [DEPTH_T+6:0] vpipe;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vpipe <= 0;
        else vpipe <= {vpipe[DEPTH_T+5:0], fin_v};
    // ---- by id: {~valid, index} ascending over entries 0..7 (entries >= K invalid) ----
    localparam integer WI = 1 + IW;
    reg [8*WI-1:0] id0;
    integer e;
    always @(*) begin
        for (e = 0; e < 8; e = e + 1)
            if (e < K) id0[e*WI +: WI] = {~lvl[0][e*W + W - 1], ~lvl[0][e*W +: IW]};
            else id0[e*WI +: WI] = {1'b1, {IW{1'b1}}};
    end
    wire [8*WI-1:0] i1, i2, i3, i4, i5, i6;
    ot_gpu_topk_cs #(.W(WI), .KB(2), .J(1), .DESC(0)) s1 (.clk(clk), .d(id0), .q(i1));
    ot_gpu_topk_cs #(.W(WI), .KB(4), .J(2), .DESC(0)) s2 (.clk(clk), .d(i1), .q(i2));
    ot_gpu_topk_cs #(.W(WI), .KB(4), .J(1), .DESC(0)) s3 (.clk(clk), .d(i2), .q(i3));
    ot_gpu_topk_cs #(.W(WI), .KB(8), .J(4), .DESC(0)) s4 (.clk(clk), .d(i3), .q(i4));
    ot_gpu_topk_cs #(.W(WI), .KB(8), .J(2), .DESC(0)) s5 (.clk(clk), .d(i4), .q(i5));
    ot_gpu_topk_cs #(.W(WI), .KB(8), .J(1), .DESC(0)) s6 (.clk(clk), .d(i5), .q(i6));
    assign out_valid = vpipe[DEPTH_T+5];
    generate
        for (g = 0; g < K; g = g + 1) begin : g_out
            assign out_ids[g*IW +: IW] = i6[g*WI +: IW];
        end
    endgenerate
endmodule
