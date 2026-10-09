`timescale 1ps/1fs
// Final actual arithmetic stage of key generation. One128-element key is
// prepaid before no-stall quantizer issue. Output retains all68 bytes until
// the real append consumer accepts them. No HBM publication is inferred here.
module ot_hbm_key_quant_producer #(parameter integer ENABLE=0)(
 input wire clk,por_n,start, output wire start_ready,
 input wire[19:0] key_index,input wire[5:0] layer,
 input wire block_v,output wire block_r,input wire[1:0] block_number,
 input wire[1023:0] block_data,
 output wire key_v,input wire key_r,output wire[543:0] key_data,
 output wire[19:0] out_key_index,output wire[5:0] out_layer,
 output reg done,output reg fault
);
generate if(!ENABLE)begin:off
 assign start_ready=0;assign block_r=0;assign key_v=0;assign key_data=0;
 assign out_key_index=0;assign out_layer=0;
 always @* begin done=0;fault=0;end
end else begin:on
 reg active;reg[2:0] accepted;reg[3:0] seen;
 reg[25:0] route;reg[543:0] data;
 reg[1:0] tag[0:12];
 wire take=block_v&&block_r;
 wire qv,qfault;wire[255:0] q;wire signed[9:0] qe;wire[511:0] qy;
 assign start_ready=!active&&!fault;
 assign block_r=active&&accepted<4&&!fault;
 assign key_v=active&&(&seen)&&!fault;
 assign key_data=data;assign out_layer=route[25:20];assign out_key_index=route[19:0];
 ot_hdc_actquant u_quant(.clk(clk),.rst_n(por_n),.v(take),.fp4(1'b1),
 .x(block_data),.vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 integer t,l;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin active<=0;accepted<=0;seen<=0;done<=0;fault<=0;end
  else begin
   done<=0;tag[0]<=block_number;
   for(t=1;t<13;t=t+1)tag[t]<=tag[t-1];
   if(start&&start_ready)begin
    active<=1;accepted<=0;seen<=0;route<={layer,key_index};
    if(layer>=40)fault<=1;
   end
   if(take)begin
    if(block_number!==accepted[1:0])fault<=1;
    accepted<=accepted+1;
   end
   if(qv)begin
    if(!active||qfault||qe < -127||qe>125||seen[tag[12]])fault<=1;
    else begin
     seen[tag[12]]<=1;
     data[512+8*tag[12]+:8]<=8'(qe+127);
     for(l=0;l<32;l=l+1)data[128*tag[12]+4*l+:4]<=q[8*l+:4];
    end
   end
   if(key_v&&key_r)begin active<=0;done<=1;end
  end
 end
end endgenerate
endmodule
