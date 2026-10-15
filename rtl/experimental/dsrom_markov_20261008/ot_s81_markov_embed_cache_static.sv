`timescale 1ns/1ps
`default_nettype none
// One real 4096-FF immutable-per-token E vector per existing A32 Markov slot.
// Shared mapped E ROM loads once before the compiler's row windows; each A
// replays locally at its own row phase (q3's head stream is two cycles later).
// Explicit constant-index FF banks: no behavioural memory or port arbitration.
module ot_s81_markov_embed_cache_static #(parameter integer ID_W=60)(
 input wire clk,rst_n,input wire load_v,input wire[255:0]load_data,
 input wire[3:0]load_beat,input wire[16:0]load_token,input wire[ID_W-1:0]load_identity,
 input wire request_slot,input wire[16:0]token,input wire[ID_W-1:0]identity,
 output reg word_v,output reg[255:0]word_data,output reg[3:0]word_beat,
 output reg[16:0]word_token,output reg[ID_W-1:0]word_identity,output reg fault
);
 wire[4095:0]bank_data;
 reg[15:0]loaded;reg[4:0]next_load;reg[16:0]cache_token;reg[ID_W-1:0]cache_id;
 reg issuing;reg[3:0]next_beat;reg[16:0]held_token;reg[ID_W-1:0]held_id;
 reg[5:0]v;reg[3:0]bp[0:5];reg[16:0]tp[0:5];reg[ID_W-1:0]ip[0:5];
 wire issue=request_slot||issuing;
 wire[3:0]ib=request_slot?4'd0:next_beat;
 wire[16:0]it=request_slot?token:held_token;
 wire[ID_W-1:0]ii=request_slot?identity:held_id;
 wire loading_ok=load_beat==0||load_beat==next_load;
 generate for(genvar b=0;b<16;b=b+1)begin:g_bank
  (* keep *)reg[255:0]data;
  always @(posedge clk)if(load_v&&load_beat==b)data<=load_data;
  assign bank_data[b*256+:256]=data;
 end endgenerate
 reg[255:0]selected;integer b,i;
 always @*begin selected=0;for(b=0;b<16;b=b+1)if(bp[5]==b)selected=selected|bank_data[b*256+:256];end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   loaded<=0;next_load<=0;cache_token<=0;cache_id<=0;issuing<=0;next_beat<=0;held_token<=0;held_id<=0;
   v<=0;word_v<=0;word_data<=0;word_beat<=0;word_token<=0;word_identity<=0;fault<=0;
   for(i=0;i<6;i=i+1)begin bp[i]<=0;tp[i]<=0;ip[i]<=0;end
  end else begin
   if(load_v)begin
    if(issuing||(|v)||request_slot||!loading_ok||load_token>=129280)fault<=1;
    if(load_beat==0)begin loaded<=16'd1;next_load<=1;cache_token<=load_token;cache_id<=load_identity;end
    else begin
     if(load_token!=cache_token||load_identity!=cache_id)fault<=1;
     loaded[load_beat]<=1;next_load<=next_load+1'b1;
    end
   end
   if(request_slot)begin
    if(issuing||(|v)||load_v||loaded!=16'hffff||token!=cache_token||identity!=cache_id)fault<=1;
    issuing<=1;next_beat<=1;held_token<=token;held_id<=identity;
   end else if(issuing)begin
    if(next_beat==15)issuing<=0;else next_beat<=next_beat+1'b1;
   end
   v<={v[4:0],issue};bp[0]<=ib;tp[0]<=it;ip[0]<=ii;
   for(i=1;i<6;i=i+1)begin bp[i]<=bp[i-1];tp[i]<=tp[i-1];ip[i]<=ip[i-1];end
   word_v<=v[5];word_data<=selected;word_beat<=bp[5];word_token<=tp[5];word_identity<=ip[5];
  end
 end
endmodule
`default_nettype wire
