// test-only: the two kept-register helpers of rtl/qwen_dv/s5/qfd_dv_s5_suvm7.sv (claude/qw-slice2r-1020 f738e1a70), used by su7_control_projection.sv
(* keep_hierarchy = "yes" *) module qfd_dv_s7_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

(* keep_hierarchy = "yes" *) module qfd_dv_s7_kffr #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire rn, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck or negedge rn) if (!rn) q <= {W{1'b0}}; else q <= d;
endmodule

