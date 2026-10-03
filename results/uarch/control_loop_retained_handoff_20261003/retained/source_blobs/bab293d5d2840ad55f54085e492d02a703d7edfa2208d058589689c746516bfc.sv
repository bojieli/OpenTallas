(* blackbox *)
module ot_hdc_v41x_vec_red #(
    parameter integer N  = 64,          
    parameter integer LV = 6,           
    parameter integer AW = 24,
    parameter integer MW = 64,          
    parameter integer MLAT = 3,         
    parameter integer ALAT = 3          
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,        
    input  wire [N*32-1:0] x_in,
    input  wire [N-1:0]    live_in,
    input  wire            mx_in,       
    input  wire            sq_in,
    input  wire [3:0]      lt_in,       
    input  wire            span_in,     
    input  wire [2:0]      l_in,        
    input  wire            last_in,     
    input  wire [7:0]      nres_in,     
    input  wire            rnd_in,
    input  wire [AW-1:0]   rbase_in,
    input  wire [4:0]      rsh_in,
    input  wire [MW-1:0]   meta_in,
    output reg  [N/8-1:0]  o_we,
    output reg  [N/8*AW-1:0] o_addr,
    output reg  [N/8*32-1:0] o_data,
    output reg  [MW-1:0]   o_meta,
    output reg             o_ev,        
    output wire            busy,
    output reg             fault
);
endmodule
