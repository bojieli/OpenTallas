(* blackbox *)
module ot_hdc_v41x_vec_side #(
    parameter integer MLAT = 3,     
    parameter integer ALAT = 3      
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [2:0]  fn,          
    input  wire [31:0] x,
    input  wire [2:0]  fn_out,      
    output wire [31:0] y,
    output wire        fault
);
endmodule
