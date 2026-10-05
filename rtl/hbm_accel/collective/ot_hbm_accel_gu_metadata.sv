`timescale 1ns/1ps
// W6 authoritative descriptor retention. No raw authoritative shadow. During
// CE no permissions use corrected data: scrub atomically at the next edge,
// recheck the retained code, then resume. DUE retains damaged evidence/debt.
// rst_n is ROOT POR. A warm request never resets this module.
module ot_hbm_accel_gu_metadata #(parameter integer WIDTH=192)(
 input wire clk,rst_n,we,input wire [WIDTH-1:0] next_data,
 output wire [WIDTH-1:0] data,output wire good,ce,due
);
 localparam integer NW=(WIDTH+63)/64,PAD=NW*64;
 reg [71:0] code[0:NW-1];
 wire [65:0] decoded[0:NW-1];
 wire [PAD-1:0] value,padded={{(PAD-WIDTH){1'b0}},next_data};
 wire [NW-1:0] ces,ues;
 for(genvar k=0;k<NW;k=k+1)begin:rows
  assign decoded[k]=ot_gpu_w6_secded_pkg::decode64(code[k]);
  assign value[k*64+:64]=decoded[k][63:0];
  assign ces[k]=decoded[k][64];assign ues[k]=decoded[k][65];
 end
 assign data=value[WIDTH-1:0];assign ce=|ces;assign due=|ues;
 assign good=!(ce||due);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)for(integer k=0;k<NW;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
  else if(!due)begin
   if(ce)for(integer k=0;k<NW;k=k+1)
    code[k]<=ot_gpu_w6_secded_pkg::encode64(decoded[k][63:0]);
   else if(we)for(integer k=0;k<NW;k=k+1)
    code[k]<=ot_gpu_w6_secded_pkg::encode64(padded[k*64+:64]);
  end
 end
endmodule
