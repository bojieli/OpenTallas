`timescale 1ns/1ps
// Four real vocabulary-rank results. Credit is retained until the matching
// global result retires. Full cohort+command sequence, no 8-bit tag alias.
module ot_qwen_dspark_argmax_gather #(parameter integer ENABLE=0,MUT_TIE=0)(
 input wire clk,rst_n,input wire begin_v,output wire begin_r,
 input wire [63:0] begin_id,input wire [7:0] begin_seq,
 input wire [3:0] i_v,output wire [3:0] i_r,
 input wire [255:0] i_id,input wire [31:0] i_seq,
 input wire [71:0] i_token,input wire [127:0] i_value,
 input wire [3:0] i_fault,
 output wire o_v,input wire o_r,
 output reg [17:0] o_token,output reg [31:0] o_value,
 output wire [63:0] o_id,output wire [7:0] o_seq,output reg fault
);
 reg [2:0] state;reg [3:0] present;
 reg [63:0] cohort;reg [7:0] sequence_id;
 reg [17:0] token[0:3];reg [31:0] value[0:3];
 reg [17:0] pairtoken[0:1];reg [31:0] pairvalue[0:1];
 wire [3:0] fire=i_v&i_r;
 assign begin_r=(ENABLE!=0)&&state==0&&!fault;
 assign i_r=((ENABLE!=0)&&state==1&&!fault)?~present:4'b0;
 assign o_v=(ENABLE!=0)&&state==4&&!fault;
 assign o_id=cohort;assign o_seq=sequence_id;
 function automatic [31:0] key(input [31:0] x);
  reg [31:0] y;begin y=(x==32'h80000000)?32'b0:x;key=y[31]?~y:y|32'h80000000;end
 endfunction
 function automatic choose_first(input [31:0] a,b,input [17:0] ai,bi);
  choose_first=key(a)>key(b)||(key(a)==key(b)&&((MUT_TIE!=0)?ai>bi:ai<bi));
 endfunction
 integer rank,pair;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=0;present<=0;fault<=0;end
  else begin
   if(begin_v&&begin_r)begin state<=1;present<=0;cohort<=begin_id;sequence_id<=begin_seq;end
   if(state==1)begin
    if(|i_fault)fault<=1;
    present<=present|fire;
    for(rank=0;rank<4;rank=rank+1)if(fire[rank])begin
     if(i_id[rank*64+:64]!=cohort||i_seq[rank*8+:8]!=sequence_id||
      i_token[rank*18+:18]<rank*37984||i_token[rank*18+:18]>=(rank+1)*37984||
      i_value[rank*32+23+:8]==8'hff)fault<=1;
     else begin token[rank]<=i_token[rank*18+:18];value[rank]<=i_value[rank*32+:32];end
    end
    if(&(present|fire))state<=2;
   end else if(state==2)begin
    for(pair=0;pair<2;pair=pair+1)
     if(choose_first(value[pair*2],value[pair*2+1],token[pair*2],token[pair*2+1]))begin pairtoken[pair]<=token[pair*2];pairvalue[pair]<=value[pair*2];end
     else begin pairtoken[pair]<=token[pair*2+1];pairvalue[pair]<=value[pair*2+1];end
    state<=3;
   end else if(state==3)begin
    if(choose_first(pairvalue[0],pairvalue[1],pairtoken[0],pairtoken[1]))begin o_token<=pairtoken[0];o_value<=pairvalue[0];end
    else begin o_token<=pairtoken[1];o_value<=pairvalue[1];end
    state<=4;
   end else if(state==4&&o_r)state<=0;
  end
 end
endmodule
