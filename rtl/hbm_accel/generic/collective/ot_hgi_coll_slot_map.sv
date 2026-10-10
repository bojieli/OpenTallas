`timescale 1ns/1ps
`default_nettype none
// G25 address transpose for ONE bypass gather of M complete owned rows.
// Producer stages M*words flits in the existing protected SU inject store.
// This module uses the endpoint's actual rank/gi and never changes payload bits.
// Sink must accept every asserted lane, as on the existing endpoint delivery bus.
// Supported native packed-row shapes are 9,16,32 512-bit words; other shapes fault.
module ot_hgi_coll_slot_map #(
 parameter integer ENABLE=0, DEL=4, FW=512, PWT=FW+33, MUT_ORDER=0
)(
 input wire clk,rst_n,start,
 input wire [7:0] group_size,group_base,rank,destinations,
 input wire [15:0] flits_per_rank,row_words,
 input wire [DEL-1:0] in_v,input wire [DEL*PWT-1:0] in_flit,
 input wire endpoint_done,
 output reg [DEL-1:0] out_v,
 output reg [DEL*FW-1:0] out_data,
 output reg [DEL*20-1:0] out_row,
 output reg [DEL*16-1:0] out_word,
 output reg done,output reg fault
);
 reg [7:0] G,GB,DEST,RANK;
 reg [15:0] PF,W;
 reg [DEL-1:0] v0,v1,v2;
 reg [DEL*FW-1:0] d0,d1,d2;
 reg [7:0] src0[0:DEL-1],src1[0:DEL-1],src2[0:DEL-1];
 reg [15:0] gi0[0:DEL-1], local1[0:DEL-1],slot2[0:DEL-1],word2[0:DEL-1];
 reg [3:0] done_pipe;
 reg [DEL-1:0] e0,e1,e2;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   G<=0;GB<=0;DEST<=0;RANK<=0;PF<=0;W<=0;
   v0<=0;v1<=0;v2<=0;out_v<=0;done_pipe<=0;done<=0;fault<=0;
  end else if(ENABLE!=0) begin
   if(start) begin
    G<=group_size;GB<=group_base;DEST<=destinations;RANK<=rank;
    PF<=flits_per_rank;W<=row_words;
    if(!(group_size==1||group_size==2||group_size==4||group_size==8||group_size==96)||
       destinations==0||destinations>group_size||rank<group_base||rank>=group_base+group_size||
       !(row_words==9||row_words==16||row_words==32)||flits_per_rank==0||flits_per_rank>512||
       flits_per_rank%row_words!=0) fault<=1;
   end
   done_pipe<={done_pipe[2:0],endpoint_done}; done<=done_pipe[3]&&!fault;
   v0<=in_v;v1<=v0;v2<=v1;
   out_v<=v2 & {DEL{RANK-GB<DEST && !fault}};
   d1<=d0;d2<=d1;out_data<=d2;
   for(integer l=0;l<DEL;l=l+1) begin
    d0[l*FW+:FW]<=in_flit[l*PWT+:FW];
    src0[l]<=in_flit[l*PWT+FW+16+:8]-GB;
    gi0[l]<=in_flit[l*PWT+FW+:16];
    e0[l]<=!in_flit[l*PWT+PWT-1]||in_flit[l*PWT+FW+24+:8]!=8'hff||
            in_flit[l*PWT+FW+16+:8]<GB||in_flit[l*PWT+FW+16+:8]>=GB+G;
    src1[l]<=src0[l];local1[l]<=gi0[l]-src0[l]*PF;
    e1[l]<=e0[l]||gi0[l]<src0[l]*PF||gi0[l]>= (src0[l]+16'd1)*PF;
    src2[l]<=src1[l];e2[l]<=e1[l];
    case(W)
     9:begin slot2[l]<=local1[l]/16'd9;word2[l]<=local1[l]%16'd9;end
     16:begin slot2[l]<=local1[l]>>4;word2[l]<={12'd0,local1[l][3:0]};end
     32:begin slot2[l]<=local1[l]>>5;word2[l]<={11'd0,local1[l][4:0]};end
     default:begin slot2[l]<=0;word2[l]<=0;e2[l]<=1;end
    endcase
    out_row[l*20+:20]<=MUT_ORDER?src2[l]*(PF/W)+slot2[l]:slot2[l]*G+src2[l];
    out_word[l*16+:16]<=word2[l];
    if(v2[l] && e2[l])begin fault<=1;out_v[l]<=0;end
   end
  end
 end
endmodule
`default_nettype wire
