(* blackbox *)
module ot_coll_topk_merge #(
    parameter integer N     = 4,              
    parameter integer NMAX  = 512,            
    parameter integer LW    = 16,             
    parameter integer LDW   = 1,              
    parameter integer P     = 64,             
    parameter integer PF    = P,              
                                              
    parameter integer DIG   = 4,              
    parameter integer RB    = (N > 1) ? $clog2(N) : 1,
    parameter integer CAP   = N * NMAX,
    parameter integer CB    = $clog2(CAP + 1),
    parameter integer WB    = $clog2(CAP / LW),
    parameter integer OW    = PF / LW         
) (
    input  wire              clk,
    input  wire              rst_n,
    
    input  wire              ld_valid,
    input  wire              ld_id,
    input  wire [RB-1:0]     ld_rank,
    input  wire [WB-1:0]     ld_word,         
    input  wire [32*LW*LDW-1:0] ld_data,
    
    input  wire              go,
    input  wire [CB-1:0]     n,               
    input  wire [CB-1:0]     k,               
    input  wire [31:0]       stride,          
    output reg               busy,
    output reg               done,            
    output reg               fault,           
    
    
    output reg               out_valid,
    output reg  [$clog2(OW+1)-1:0] out_nw,
    output reg  [32*LW*OW-1:0] out_data,
    output reg               out_last,
    output reg  [31:0]       stat_cycles      
);
endmodule
