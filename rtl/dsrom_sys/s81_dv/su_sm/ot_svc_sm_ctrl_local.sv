`timescale 1ns/1ps
// Same-edge retained control copies. Separate module boundaries prevent
// cross-instance merging before technology mapping. No new clock or latency.
(* keep_hierarchy = 1 *)
module ot_svc_sm_keep_bit #(parameter integer RESET = 1)(
    input wire clk, rst_n, d,
    output reg q
);
    generate if (RESET != 0) begin : g_reset
        always @(posedge clk or negedge rst_n)
            if (!rst_n) q <= 1'b0; else q <= d;
    end else begin : g_data
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
