`timescale 1ns/1ps
// Independent source publication of the existing boot cfg-data register.
// Captures the same D under the same enable, reset value and execution edge.
(* keep_hierarchy="yes" *) module qfd_sysface_cfg_copy #(parameter integer W=32,ID=0)(
 input wire ck,rst_n,we,input wire[W-1:0]d,output reg[W-1:0]q
);
 always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else if(we)q<=d;
endmodule
