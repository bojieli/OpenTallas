// PRIVATE OPT-IN GRAPH: never selected by public main defaults.
`timescale 1ns/1ps
(* keep_hierarchy = 1 *) module ot_gunit_guarded_1019_dsdv_gunit_operand_pin32 (
    input wire clk, input wire [31:0] d, output reg [31:0] q
);
    always @(posedge clk) q <= d;
endmodule

(* keep_hierarchy = 1 *) module ot_gunit_guarded_1019_dsdv_gunit_control_first(input wire clk, rst_n, d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule

(* keep_hierarchy = 1 *) module ot_gunit_guarded_1019_dsdv_gunit_control_bit(input wire clk, d, output reg q);
    always @(posedge clk) q <= d;
endmodule

(* keep_hierarchy = 1 *) module ot_gunit_guarded_1019_dsdv_gunit_capture_bank24(
    input wire clk, armed, captured, input wire [9:0] sage, deadline, output wire [23:0] q);
    wire fire = armed && !captured && sage == deadline;
    for (genvar k = 0; k < 24; k = k + 1) begin : g_q
        (* keep = 1 *) ot_gunit_guarded_1019_dsdv_gunit_control_bit u_q (.clk(clk), .d(fire), .q(q[k]));
    end
endmodule
