`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA1 system-context harness: a drop-in for rtl/gpu/ot_gpu_barrier_node.sv in
// the reduced HBM system top (rtl/gpu_sys/ot_gpu_hbm_system.sv instantiates
// one node per die as the root, rel_in tied to its own up).  The HA1 runner
// (tools/hbm_accel/run_ha1_system.py) compiles this file INSTEAD of the
// original, so every pinned file stays byte-identical.
//   default         : the original sense-reversing tree node, line for line
//   +define+HA1_TXCOUNT: no root release; each child j gets its own
//                     ot_hbm_txcount_arrival counter over every child's
//                     arrival sense (point-to-point), rel[j] = its phase.
// Both forms measure, per barrier, the cycle the last child arrived and the
// cycle the last child saw its release, and print totals at the end:
//   HA1_BAR inst=<path> barriers=N boundary_sum=S boundary_max=M wait_sum=W
// boundary = last arrival -> every child released; wait = sum over children
// of (own release - own arrival), the SM cycles spent in B_BAR.
// ---------------------------------------------------------------------------
module ot_gpu_barrier_node #(
    parameter integer K = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [K-1:0] arr,
    output reg          up,
    input  wire         rel_in,
    output reg  [K-1:0] rel
);
`ifdef HA1_TXCOUNT
    wire [K-1:0] rel_w;
    genvar j;
    for (j = 0; j < K; j = j + 1) begin : g_cons
        ot_hbm_txcount_arrival #(.ENABLE(1), .K(K)) u_cnt (.clk(clk), .rst_n(rst_n), .arr(arr), .rel(rel_w[j]));
    end
    always @* begin up = 1'b0; rel = rel_w; end
`else
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            up <= 1'b0;
            rel <= {K{1'b0}};
        end else begin
            if (arr == {K{~up}}) up <= ~up;
            rel <= {K{rel_in}};
        end
    end
`endif
`ifndef SYNTHESIS
    // ---- measurement only
    longint unsigned cyc = 0, nbar = 0, bsum = 0, bmax = 0, wsum = 0;
    reg [K-1:0] arr_q = 0, rel_q = 0;
    reg sense = 1'b0;                 // sense of the barrier in flight
    longint unsigned t_arr [0:K-1];
    longint unsigned t_last = 0;
    integer c;
    reg all_arr = 1'b0;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        arr_q <= arr; rel_q <= rel;
        for (c = 0; c < K; c = c + 1) begin
            if (arr[c] != arr_q[c]) t_arr[c] = cyc;
        end
        if (!all_arr && arr == {K{~sense}}) begin all_arr = 1'b1; t_last = cyc; end
        if (all_arr) begin
            for (c = 0; c < K; c = c + 1) if (rel[c] != rel_q[c] && rel[c] == ~sense) wsum = wsum + (cyc - t_arr[c]);
            if (rel == {K{~sense}}) begin
                nbar = nbar + 1;
                bsum = bsum + (cyc - t_last);
                if (cyc - t_last > bmax) bmax = cyc - t_last;
                sense = ~sense; all_arr = 1'b0;
            end
        end
    end
    final $display("HA1_BAR inst=%m barriers=%0d boundary_sum=%0d boundary_max=%0d wait_sum=%0d", nbar, bsum, bmax, wsum);
`endif
endmodule

// Registered wire of D stages (unchanged copy of the original's second module).
module ot_gpu_barrier_link #(
    parameter integer D = 1
) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    ot_hdc_delay #(.W(1), .D(D), .RESET(1)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
