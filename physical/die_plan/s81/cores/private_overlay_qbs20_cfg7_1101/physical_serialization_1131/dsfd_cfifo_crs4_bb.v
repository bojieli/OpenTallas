// Exact specialization checked before header staging; content INSTANCE retained.
(* blackbox *)
module dsfd_cfifo_crs4 #(parameter integer LFACE=0, parameter integer LGATE=0) (
    output wire [14:0] cc,
    input wire cr,
    input wire cr_s,
    output wire [69:0] rd,
    input wire [65:0] ri,
    output reg rs,               
    input wire rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [535:0] x2,
    input wire [275:0] xl0,      
    input wire [275:0] xl1,      
    input wire [275:0] xl2,      
    input wire [275:0] xl3,      
    input wire [3:0] xk,         
    input wire [11:0] lk         
);
endmodule
