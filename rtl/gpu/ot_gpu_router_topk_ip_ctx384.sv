`timescale 1ns/1ps
// Fixed FULL router shape for the physical flow. No logic/state/latency added.
// Avoids top-level -chparam reprocessing of the parameterized array recurrence.
// Default-off: only an explicit source/top selection elaborates this wrapper.
module ot_gpu_router_topk_ip_ctx384 (
    input wire clk, rst_n, in_valid,
    input wire [511:0] in_vals,
    input wire in_last,
    output wire out_valid,
    output wire [53:0] out_ids
);
    // Pinned child defaults: N384/P16/K6/IW9; full shape, no port false paths.
    ot_gpu_router_topk_ip_f u_selector (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_vals(in_vals),
        .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids)
    );
endmodule
