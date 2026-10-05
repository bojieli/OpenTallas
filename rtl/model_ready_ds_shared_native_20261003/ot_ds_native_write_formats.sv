`timescale 1ns/1ps
`default_nettype none
// Preserve source-order last-write-wins; do not truncate word addresses.
module ot_ds_native_write_formats(
 input wire [2235:0] me,input wire [8063:0] row,input wire [2111:0] coll,
 output reg [383:0] enable,output reg [11519:0] addr,output reg [12287:0] data,output reg [2:0] bad);
 integer p,l;
 always @(*)begin
  enable=0;addr=0;data=0;bad=0;
  for(p=0;p<4;p=p+1)begin
   if(me[2232+p] && (|me[2112+p*30+15+:15]))bad[0]=1;
   for(l=0;l<16;l=l+1)begin
    enable[p*16+l]=me[2232+p]&&me[2048+p*16+l];
    addr[(p*16+l)*30+:30]={11'b0,me[2112+p*30+:15],4'(l)};
    data[(p*16+l)*32+:32]=me[p*512+l*32+:32];
    enable[256+p*16+l]=coll[2108+p];
    addr[(256+p*16+l)*30+:30]={11'b0,coll[2048+p*15+:15],4'(l)};
    data[(256+p*16+l)*32+:32]=coll[p*512+l*32+:32];
   end
  end
  enable[128+:128]=row[7936+:128];addr[3840+:3840]=row[4096+:3840];data[4096+:4096]=row[4095:0];
 end
endmodule
`default_nettype wire
