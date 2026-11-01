`timescale 1ns/1fs
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
(* keep_hierarchy, keep *)
module ot_dp_rrelay_drive (input wire clk, input wire d, output wire q);
    (* keep *) reg state;
    always @(posedge clk) state <= d;
`ifdef SYNTHESIS
    (* keep, dont_touch *) BUFx4f_ASAP7_75t_R u_drive (.A(state), .Y(q));
`else
    assign q = state;
`endif
endmodule
(* keep_hierarchy, keep *)
module ot_dp_rgate (input wire clk, input wire d, input wire run, output reg q);
    always @(posedge clk) q <= d & run;
endmodule
