`timescale 1ns/1ps
// Private full released GU consumer. No rounding arithmetic, expected inputs,
// raw-tag dictionary or independently granted authority. ENABLE0 is inert.
module ot_hubble_live_gu_capture #(parameter integer ENABLE=0)(
 input wire clk,rst_n,start,permit,input wire [72:0] frame,
 input wire [31:0] op_a,op_b,
 input wire span_v, input wire [2047:0] span_bf16,
 input wire [8:0] expert,count,input wire matrix,
 input wire [11:0] row_base,input wire [7:0] lane_first,source_sm,source_die,
 input wire [72:0] span_frame,input wire [31:0] span_op,
 output wire span_accept,input wire source_finished,retire,
 input wire [6:0] issue_index,
 output wire [2047:0] g,u,output wire ready,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:g_off
  assign span_accept=0;assign g=0;assign u=0;assign ready=0;assign fault=0;
 end else begin:g_on
  // Four vectors; one word holds four actual BF16 rows. Each accepted span
  // owns three distinct words. Bitmap bits describe whole atomic12-row spans.
  reg [71:0] data[0:2303];reg [71:0] seen[0:11];
  reg [71:0] ctx[0:2];
  wire [65:0] c0=decode64(ctx[0]),c1=decode64(ctx[1]),c2=decode64(ctx[2]);
  wire [191:0] raw={c2[63:0],c1[63:0],c0[63:0]};
  wire [72:0] held_frame=raw[72:0];
  wire [31:0] held_a=raw[104:73],held_b=raw[136:105];
  wire [9:0] accepted=raw[146:137];wire [2:0] phase=raw[149:147];
  wire ctx_bad=c0[65]||c1[65]||c2[65]||raw[191:150]!=0;
  wire identity=permit&&frame==held_frame&&op_a==held_a&&op_b==held_b;
  integer bank,span_index,word_index,j,beat_bank,base_word;
  reg desc_ok,payload_ok,seen_bad,read_bad,all_seen;
  reg [65:0] bitmap_word,read_word;
  reg [2047:0] gd,ud;
  always @* begin
   bank=(expert==65?2:0)+integer'(matrix);
   span_index=bank*192+integer'(row_base)/12;
   word_index=bank*576+integer'(row_base)/4;
   bitmap_word=66'd0;
   if(span_index>=0&&span_index<768)bitmap_word=decode64(seen[span_index/64]);
   desc_ok=(expert==41||expert==65)&&count==12&&lane_first==0&&row_base<2304&&row_base%12==0&&
    span_frame==held_frame&&span_op==(expert==41?held_a:held_b)&&
    source_die<96&&row_base==24*integer'(source_die)+12*(integer'(source_sm)%2)&&
    source_sm==(expert==41?0:4)+2*integer'(matrix)+(integer'(row_base)/12)%2;
   payload_ok=1;
   for(j=0;j<12;j=j+1)if(span_bf16[j*16+7+:8]==8'hff)payload_ok=0;
   seen_bad=bitmap_word[65]||bitmap_word[span_index%64];
   all_seen=1;
   for(j=0;j<12;j=j+1)begin
    read_word=decode64(seen[j]);if(read_word[65]||read_word[63:0]!=64'hffffffffffffffff)all_seen=0;
   end
   gd=0;ud=0;read_bad=0;
   beat_bank=issue_index>=36?2:0;base_word=(integer'(issue_index)%36)*16;
   for(j=0;j<16;j=j+1)begin
    read_word=66'd0;
    if(issue_index<72)read_word=decode64(data[beat_bank*576+base_word+j]);
    if(read_word[65])read_bad=1;
    gd[j*128+:128]={{read_word[63:48],16'd0},{read_word[47:32],16'd0},
                     {read_word[31:16],16'd0},{read_word[15:0],16'd0}};
    if(issue_index<72)read_word=decode64(data[(beat_bank+1)*576+base_word+j]);
    if(read_word[65])read_bad=1;
    ud[j*128+:128]={{read_word[63:48],16'd0},{read_word[47:32],16'd0},
                     {read_word[31:16],16'd0},{read_word[15:0],16'd0}};
   end
  end
  assign fault=ctx_bad||phase==4||(phase!=0&&phase!=5&&!identity)||(phase==3&&(read_bad||!all_seen));
  assign span_accept=phase==1&&!fault&&desc_ok&&payload_ok&&!seen_bad;
  assign ready=phase==3&&!fault&&all_seen;
  assign g=ready?gd:2048'd0;assign u=ready?ud:2048'd0;
  reg [191:0] next_ctx;reg [63:0] next_seen;
  integer k;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    for(k=0;k<3;k=k+1)ctx[k]<=encode64(64'd0);
    for(k=0;k<12;k=k+1)seen[k]<=encode64(64'd0);
   end else begin
    next_ctx=raw;
    if(start)begin
     if(phase!=0||!permit||op_a==op_b)next_ctx[149:147]=4;
     else begin next_ctx=0;next_ctx[72:0]=frame;next_ctx[104:73]=op_a;
      next_ctx[136:105]=op_b;next_ctx[149:147]=1;end
    end
    if(phase!=0&&phase!=5&&(!identity||ctx_bad))next_ctx[149:147]=4;
    if(span_v&&phase==1)begin
     if(!span_accept)next_ctx[149:147]=4;
     else begin
      for(k=0;k<3;k=k+1)data[word_index+k]<=encode64(span_bf16[k*64+:64]);
      next_seen=bitmap_word[63:0];next_seen[span_index%64]=1;
      seen[span_index/64]<=encode64(next_seen);
      next_ctx[146:137]=accepted+1;
      if(accepted==767)next_ctx[149:147]=2;
     end
    end
    if(phase==2&&source_finished)begin
     if(accepted!=768||!all_seen)next_ctx[149:147]=4;
     else next_ctx[149:147]=3;
    end
    if(phase==1&&source_finished)next_ctx[149:147]=4;
    if(phase==3&&(read_bad||!all_seen))next_ctx[149:147]=4;
    if((phase==2||phase==3)&&span_v)next_ctx[149:147]=4;
    if(phase==3&&retire&&!fault)next_ctx[149:147]=5;
    for(k=0;k<3;k=k+1)ctx[k]<=encode64(next_ctx[k*64+:64]);
   end
  end
 end endgenerate
endmodule
