`timescale 1ps/1fs
// Two-direction ownership crossing. The service's held record is released only
// by the ACK generated at destination ov&&ore, never by FIFO write acceptance.
module ot_hbm_accel_owned_crossing(
 input wire service_clk,stream_clk,por_n,
 input wire iv,output wire ir,input ot_hbm_r14_pkg::owned_t id,
 output wire ov,input wire ore,output ot_hbm_r14_pkg::owned_t od,
 output wire fault,output wire empty);
 import ot_hbm_r14_pkg::*;import ot_gpu_w6_secded_pkg::*;
 reg sent,sticky;reg[71:0] control_seal;
 reg dst_fault; reg[71:0] dst_seal;
 (* async_reg="true" *) reg sf1,sf2,df1,df2;
 wire dst_bad=dst_seal!=encode64(64'(dst_fault));
 always @(posedge stream_clk or negedge por_n)
  if(!por_n)begin sf1<=0;sf2<=0;end else begin sf1<=sticky||control_bad;sf2<=sf1;end
 always @(posedge service_clk or negedge por_n)
  if(!por_n)begin df1<=0;df2<=0;end else begin df1<=dst_fault||dst_bad;df2<=df1;end
 wire control_bad=control_seal!=encode64({62'b0,sticky,sent});
 wire f_ready,f_valid,a_ready,a_valid;wire[575:0] fword,received;wire[287:0] ack,returned;
 for(genvar w=0;w<8;w=w+1)assign fword[w*72+:72]=encode64(64'(512'(id)>>(w*64)));
 wire[511:0] decoded;wire[7:0] ue;
 for(genvar w=0;w<8;w=w+1)begin
  wire[65:0] d=decode64(received[w*72+:72]);assign decoded[w*64+:64]=d[63:0];assign ue[w]=d[65];
 end
 assign od=owned_t'(decoded[464:0]);
 wire f_bad=(|ue)||(|decoded[511:465]);
 wire[208:0] ack_identity={od.id,od.physical_tag,od.beat};
 for(genvar w=0;w<4;w=w+1)assign ack[w*72+:72]=encode64(64'(256'(ack_identity)>>(w*64)));
 wire[255:0] decoded_ack;wire[3:0] a_ue;
 for(genvar w=0;w<4;w=w+1)begin
  wire[65:0] d=decode64(returned[w*72+:72]);assign decoded_ack[w*64+:64]=d[63:0];assign a_ue[w]=d[65];
 end
 wire a_match=decoded_ack==256'({id.id,id.physical_tag,id.beat});
 assign fault=sticky||control_bad||df2||(a_valid&&((|a_ue)||!a_match));
 assign ov=f_valid&&!f_bad&&a_ready&&!dst_fault&&!dst_bad&&!sf2;
 wire pop=ov&&ore;
 wire receipt=a_valid&&a_match&&iv&&sent&&!fault;
 assign ir=receipt;
 assign empty=!sent&&!iv&&!a_valid;
 wire ndst=dst_fault||dst_bad||(f_valid&&f_bad);
 always @(posedge stream_clk or negedge por_n)
  if(!por_n)begin dst_fault<=0;dst_seal<=0;end
  else begin dst_fault<=ndst;dst_seal<=encode64(64'(ndst));end
 ot_hbm_r14_fifo2 #(.WIDTH(576)) forward(.wc(service_clk),.wrn(por_n),.wv(iv&&!sent&&!fault),.wr(f_ready),.wd(fword),
  .rc(stream_clk),.rrn(por_n),.rv(f_valid),.rr(pop),.rd(received));
 ot_hbm_r14_fifo2 #(.WIDTH(288)) reverse(.wc(stream_clk),.wrn(por_n),.wv(pop),.wr(a_ready),.wd(ack),
  .rc(service_clk),.rrn(por_n),.rv(a_valid),.rr(receipt),.rd(returned));
 reg ns,nf;
 always @*begin
  ns=sent;nf=sticky;
  if(iv&&!sent&&!fault&&f_ready)ns=1;
  if(receipt)ns=0;
  if(control_bad||(a_valid&&((|a_ue)||!a_match)))nf=1;
 end
 always @(posedge service_clk or negedge por_n)
  if(!por_n)begin sent<=0;sticky<=0;control_seal<=0;end
  else begin sent<=ns;sticky<=nf;control_seal<=encode64({62'b0,nf,ns});end
endmodule
