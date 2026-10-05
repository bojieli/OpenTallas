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
 wire [71:0] repaired[0:NW-1];
 wire [6:0] syndrome[0:NW-1];
 wire [NW-1:0] overall;
 wire [PAD-1:0] value;
 wire [PAD-1:0] padded;
 assign padded={{(PAD-WIDTH){1'b0}},next_data};
 wire [NW-1:0] ces,ues;
 function automatic [63:0] unpack64(input [71:0] c);
  integer p,j;
  begin j=0;unpack64=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin
    unpack64[j]=c[p-1];j=j+1;
   end
  end
 endfunction
 for(genvar k=0;k<NW;k=k+1)begin:rows
  assign decoded[k]=ot_gpu_w6_secded_pkg::decode64(code[k]);
  assign overall[k]=^code[k];
  for(genvar b=0;b<7;b=b+1)begin:checks
   wire [70:0] selected;
   for(genvar p=1;p<=71;p=p+1)begin:positions
    assign selected[p-1]=((p&(1<<b))!=0)?code[k][p-1]:1'b0;
   end
   assign syndrome[k][b]=^selected;
  end
  // Same W6 correction, expressed as independent constant-position compares.
  // Avoid the variable-bit read/modify/write barrel network and CE re-encode.
  // The unchanged codec remains the CE/DUE authority; no raw-state mirror.
  for(genvar p=1;p<=71;p=p+1)begin:correction
   assign repaired[k][p-1]=code[k][p-1]^(overall[k] && syndrome[k]==p);
  end
  assign repaired[k][71]=code[k][71]^(overall[k] && syndrome[k]==0);
  assign value[k*64+:64]=unpack64(repaired[k]);
  assign ces[k]=decoded[k][64];assign ues[k]=decoded[k][65];
 end
 assign data=value[WIDTH-1:0];assign ce=|ces;assign due=|ues;
 assign good=!(ce||due);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)for(integer k=0;k<NW;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
  else if(!due)begin
   if(ce)for(integer k=0;k<NW;k=k+1)
    code[k]<=repaired[k];
   else if(we)for(integer k=0;k<NW;k=k+1)
    code[k]<=ot_gpu_w6_secded_pkg::encode64(padded[k*64+:64]);
  end
 end
endmodule
