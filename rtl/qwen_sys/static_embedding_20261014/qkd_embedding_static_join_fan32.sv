`timescale 1ns/1ps
// Native32 structural candidate. One added stream edge captures payload and
// decoded local controls. The canonical low/high/scale arithmetic and fault
// rules are preserved. This module is NOT admitted until mapped native census.
module qkd_embedding_static_join_fan32(
 input wire ck,rst_n,beat_slot,beat_v,
 input wire [255:0] beat_data,input wire [17:0] beat_token,
 input wire [5:0] beat_word,input wire beat_half,beat_scale,
 input wire [15:0] beat_epoch,
 output reg word_v,output reg [511:0] word_data,
 output reg [17:0] word_token,output reg [5:0] word_index,
 output reg word_scale,output reg [15:0] word_epoch,output reg fault
);
 reg [255:0] data_q;reg [17:0] token_q;reg [5:0] index_q;
 reg [15:0] epoch_q;reg half_q,slot_q,valid_q;
 (* keep=1,dont_touch=1 *) reg scale_q;
 (* keep=1,dont_touch=1 *) reg [19:0] low_capture_q;
 (* keep=1,dont_touch=1 *) reg [17:0] out_scale_q;
 (* keep=1,dont_touch=1 *) reg [15:0] scale_onehot_q;
 always @(posedge ck)begin
  data_q<=beat_data;token_q<=beat_token;index_q<=beat_word;
  epoch_q<=beat_epoch;half_q<=beat_half;scale_q<=beat_scale;
  low_capture_q<={20{beat_slot&&!beat_scale&&!beat_half}};
  out_scale_q<={18{beat_scale}};
  for(integer i=0;i<16;i=i+1)scale_onehot_q[i]<=beat_token[3:0]==4'(i);
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin slot_q<=0;valid_q<=0;end
  else begin slot_q<=beat_slot;valid_q<=beat_v;end
 reg low_valid;reg [255:0] low_data;reg [17:0] low_token;
 reg [5:0] low_word;reg [15:0] low_epoch;
 for(genvar i=0;i<16;i=i+1)begin:g_low
  always @(posedge ck)if(low_capture_q[i])low_data[i*16+:16]<=data_q[i*16+:16];
 end
 always @(posedge ck)begin
  if(low_capture_q[16])low_token[15:0]<=token_q[15:0];
  if(low_capture_q[17])low_token[17:16]<=token_q[17:16];
  if(low_capture_q[18])low_word<=index_q;
  if(low_capture_q[19])low_epoch<=epoch_q;
  word_token<=token_q;word_index<=index_q;word_scale<=scale_q;word_epoch<=epoch_q;
 end
 reg [15:0] scale_word;
 always @(*)begin
  scale_word=16'd0;
  for(integer i=0;i<16;i=i+1)scale_word=scale_word|({16{scale_onehot_q[i]}}&data_q[i*16+:16]);
 end
 wire [511:0] code_word={data_q,low_data};
 wire [511:0] packed_scale={496'd0,scale_word};
 for(genvar i=0;i<18;i=i+1)begin:g_output
  localparam integer LO=(i==0)?0:16+(i-1)*30;
  localparam integer WIDTH=(i==0)?16:((512-LO<30)?512-LO:30);
  always @(posedge ck)word_data[LO+:WIDTH]<=out_scale_q[i]?packed_scale[LO+:WIDTH]:code_word[LO+:WIDTH];
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin low_valid<=0;word_v<=0;fault<=0;end
  else begin
   word_v<=slot_q&&(scale_q||half_q);
   if(slot_q!=valid_q)fault<=1;
   if(slot_q)begin
    if(token_q>=151936||(scale_q&&half_q))fault<=1;
    if(scale_q)begin if(low_valid)fault<=1;end
    else if(!half_q)begin if(low_valid)fault<=1;low_valid<=1;end
    else begin low_valid<=0;
     if(!low_valid||low_token!=token_q||low_word!=index_q||low_epoch!=epoch_q)fault<=1;
    end
   end
  end
endmodule
