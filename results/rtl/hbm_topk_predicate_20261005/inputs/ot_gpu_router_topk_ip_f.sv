`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Default-off registered-insert-position candidate; signoff PENDING.
// 1.2 GHz SS successor of ot_gpu_router_topk (rtl/gpu/ot_gpu_router_topk.sv, which also supplies
// ot_gpu_topk_merge / ot_gpu_topk_cs): same ports and parameters, same selections, one cycle more
// latency (1 + 1 + 4 log2(P) + 6 + 1 from the last beat).  Opt-in (ot_dshbm_dspark_top FAST = 1);
// record results/rtl/hbm_accel_fmax_inventory_20261004/ctl.
// ---------------------------------------------------------------------------
module ot_gpu_router_topk_ip_f #(
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
    // FAST LANES (exact): the beat is registered with its keys first (per-lane copies of the
    // valid / fresh / last flags, so no flag fans out to all P x 8 entries), then the lane's
    // compare-insert runs from registers only.  Within one vector every stored entry has a lower index
    // than the arriving one (indices rise with the beat), so for a valid stored entry
    //   {1, key_l, ~idx_l} > {1, key_x, ~idx_x}  <=>  key_l >= key_x
    // and an invalid entry is always below the arriving one: a 32-bit compare replaces the 42-bit one.
    // Same selections as ot_gpu_router_topk, one cycle later.
    (* keep *) reg [P-1:0] v_r, f_r, vf_r;
    reg            l_r;
    reg [W-1:0]    x_r [0:P-1];
    reg [3:0] insert_pos [0:P-1];
    reg [8*W-1:0] pending_list [0:P-1];
    reg [8*W-1:0] forward_list [0:P-1];
    reg [3:0] next_pos [0:P-1];
    integer cj, ci;
    reg [8*W-1:0] old_list, compare_list;
    reg [31:0] incoming_key;
    integer jj, ii;
    reg [8*W-1:0] cur, sh, nx;
    reg [7:0] ge;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            beat_base <= 0; fresh <= 1'b1; v_r <= 0; f_r <= 0; vf_r <= 0; l_r <= 1'b0;
            for (jj = 0; jj < P; jj = jj + 1) insert_pos[jj] <= 0;
        end else begin
            v_r <= {P{in_valid}}; vf_r <= {P{in_valid}}; l_r <= in_valid && in_last;
            if (in_valid) begin
                f_r <= {P{fresh}};
                beat_base <= in_last ? {IW{1'b0}} : beat_base + P;
                fresh <= in_last;
                for (jj = 0; jj < P; jj = jj + 1) insert_pos[jj] <= next_pos[jj];
            end
        end
    end
    always @(posedge clk)
        if (in_valid)
            for (jj = 0; jj < P; jj = jj + 1)
                x_r[jj] <= {1'b1, okey(in_vals[32*jj +: 32]), ~(beat_base + jj[IW-1:0])};
    // Two-phase compare/insert with exact II1 forwarding. A new beat compares
    // against the preceding pending insertion, not a stale committed list.
    always @(*) begin
        old_list = 0; compare_list = 0; incoming_key = 0;
        for (cj = 0; cj < P; cj = cj + 1) begin
            old_list = f_r[cj] ? {8*W{1'b0}} : lane[cj];
            for (ci = 0; ci < 8; ci = ci + 1) begin
                if (ci < insert_pos[cj]) pending_list[cj][ci*W +: W] = old_list[ci*W +: W];
                else if (ci == insert_pos[cj]) pending_list[cj][ci*W +: W] = x_r[cj];
                else if (ci == 0) pending_list[cj][ci*W +: W] = 0;
                else pending_list[cj][ci*W +: W] = old_list[(ci-1)*W +: W];
            end
            forward_list[cj] = v_r[cj] ? pending_list[cj] : lane[cj];
            compare_list = fresh ? {8*W{1'b0}} : forward_list[cj];
            incoming_key = okey(in_vals[32*cj +: 32]);
            next_pos[cj] = 8;
            for (ci = 7; ci >= 0; ci = ci - 1)
                if (!(compare_list[ci*W+W-1] &&
                      compare_list[ci*W+IW +: 32] >= incoming_key))
                    next_pos[cj] = ci;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fin_v <= 1'b0;
            for (jj = 0; jj < P; jj = jj + 1) lane[jj] <= {8*W{1'b0}};
        end else begin
            fin_v <= l_r;
            for (jj = 0; jj < P; jj = jj + 1) begin
                if (v_r[jj]) lane[jj] <= pending_list[jj];
                if (vf_r[jj]) lane_fin[jj] <= pending_list[jj];
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
    reg [DEPTH_T+6:0] vpipe;   // fin_v: one cycle after the beat registers
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
