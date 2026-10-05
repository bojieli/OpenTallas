`timescale 1ns/1ps
// Barrier-network bench (rtl/gpu/ot_gpu_barrier_node.sv): N_SM participants in quadrants of K1 under
// quadrant nodes, K2 quadrant nodes under the root, with D_LEAF registered wire stages between an SM and its
// quadrant node and D_TRUNK between a quadrant node and the root (both ways), from the floorplan
// (tools/hbm_gpu_floorplan.py).  Each participant works a random time after it is released, then arrives.
// Measured per barrier: last arrival -> every participant released.
module tb_gpu_barrier;
    parameter integer K1 = 8, K2 = 4, D_LEAF = 7, D_TRUNK = 6, NBAR = 200, WMAX = 300;
    localparam integer N = K1 * K2;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [N-1:0] arrive;
    wire [N-1:0] arr_q, rel_sm;
    wire [K2-1:0] q_up, q_up_far, q_rel_in;
    wire root_up;
    wire [K2-1:0] root_rel;
    wire [N-1:0] q_rel;
    genvar s, q;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_sm
            ot_gpu_barrier_link #(.D(D_LEAF)) u_a (.clk(clk), .rst_n(rst_n), .d(arrive[s]), .q(arr_q[s]));
            ot_gpu_barrier_link #(.D(D_LEAF)) u_r (.clk(clk), .rst_n(rst_n), .d(q_rel[s]), .q(rel_sm[s]));
        end
        for (q = 0; q < K2; q = q + 1) begin : g_q
            ot_gpu_barrier_node #(.K(K1)) u_n (.clk(clk), .rst_n(rst_n), .arr(arr_q[q*K1 +: K1]), .up(q_up[q]),
                                               .rel_in(q_rel_in[q]), .rel(q_rel[q*K1 +: K1]));
            ot_gpu_barrier_link #(.D(D_TRUNK)) u_a (.clk(clk), .rst_n(rst_n), .d(q_up[q]), .q(q_up_far[q]));
            ot_gpu_barrier_link #(.D(D_TRUNK)) u_r (.clk(clk), .rst_n(rst_n), .d(root_rel[q]), .q(q_rel_in[q]));
        end
    endgenerate
    ot_gpu_barrier_node #(.K(K2)) u_root (.clk(clk), .rst_n(rst_n), .arr(q_up_far), .up(root_up),
                                          .rel_in(root_up), .rel(root_rel));
    integer cyc = 0, b, i, t_last, t_rel, lat, lat_min = 1 << 30, lat_max = 0, lat_sum = 0, errs = 0, seed = 5;
    integer wdone [0:N-1];
    reg sense;
    always @(posedge clk) cyc <= cyc + 1;
    initial begin
        arrive = 0; sense = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
        for (b = 0; b < NBAR; b = b + 1) begin
            sense = ~sense;
            t_last = 0;
            for (i = 0; i < N; i = i + 1) begin
                wdone[i] = cyc + 1 + ($urandom(seed) % WMAX);
                if (wdone[i] > t_last) t_last = wdone[i];
            end
            // participants arrive at their own times
            while (arrive != {N{sense}}) begin
                @(negedge clk);
                for (i = 0; i < N; i = i + 1) if (cyc >= wdone[i]) arrive[i] = sense;
                // nobody may be released before everyone has arrived
                if (rel_sm != {N{~sense}} && rel_sm != {N{sense}}) ;
                if (rel_sm == {N{sense}}) errs = errs + 1;
            end
            t_last = cyc;
            while (rel_sm != {N{sense}}) @(negedge clk);
            t_rel = cyc;
            lat = t_rel - t_last;
            lat_sum = lat_sum + lat;
            if (lat < lat_min) lat_min = lat;
            if (lat > lat_max) lat_max = lat;
        end
        $display("BARRIER n=%0d k1=%0d k2=%0d d_leaf=%0d d_trunk=%0d barriers=%0d last_arrive_to_all_released_min=%0d max=%0d mean_x100=%0d early_release_errors=%0d",
                 N, K1, K2, D_LEAF, D_TRUNK, NBAR, lat_min, lat_max, (100 * lat_sum) / NBAR, errs);
        $finish;
    end
endmodule
