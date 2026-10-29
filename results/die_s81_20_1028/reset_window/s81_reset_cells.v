// extracted verbatim from tools/die_plan/gen_rtl.py CELLS (origin/main)
`timescale 1ns/1ps
(* keep_hierarchy *)
module ot_dp_rsync_s2 (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    // Intentional reset CDC shift register; only this async_reg declaration
    // mixes asynchronous assertion with synchronous release/feedback.
    /* verilator lint_off SYNCASYNCNET */
    (* async_reg = "true" *) reg [1:0] p;
    /* verilator lint_on SYNCASYNCNET */
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) p <= 2'b0; else p <= {p[0], 1'b1};
    assign sync_rst_n = p[1];
endmodule

(* keep_hierarchy, keep *)
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
