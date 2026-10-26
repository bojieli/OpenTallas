`timescale 1ns/1ps
// bind_tiny leaves (tools/die_plan/test_bind.py): unchanged RTL instantiated by the generated partitions.
module lf_a #(parameter integer ID = 0) (input wire clk, input wire rst_n, input wire [7:0] i, output reg [7:0] o);
    always @(posedge clk or negedge rst_n) if (!rst_n) o <= 8'd0; else o <= i + ID[7:0];
endmodule
module lf_b (input wire clk, input wire [7:0] i, input wire [3:0] id, output reg [7:0] o, output reg flt);
    always @(posedge clk) begin o <= i ^ {id, id}; flt <= &i; end
endmodule
module lf_sink (input wire clk, input wire flt, input wire [7:0] d0, input wire [7:0] d1, output reg [8:0] q);
    always @(posedge clk) q <= {flt, d0 ^ d1};
endmodule
// plan variant of lf_b for a chain head (no id input): bound per instance by asbuilt.substitute_inst
module lf_b_nid (input wire clk, input wire [7:0] i, output reg [7:0] o, output reg flt);
    always @(posedge clk) begin o <= i; flt <= &i; end
endmodule
