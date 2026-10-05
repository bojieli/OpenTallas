// Structural lint ONLY. Not linked by the exact gate and never simulated.
(* blackbox *) module ot_gpu_fadd #(parameter integer LAT=7)(
 input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
endmodule
(* blackbox *) module ot_gpu_fmul #(parameter integer LAT=7)(
 input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
endmodule
