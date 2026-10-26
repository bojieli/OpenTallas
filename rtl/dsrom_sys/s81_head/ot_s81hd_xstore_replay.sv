`timescale 1ns/1ps
`default_nettype none
// Control subcomponent for the current head's real tile stream, not a host codec.
// A compiled load is 160 consecutive accepted 512-bit words: 128 words of A
// (K0..4095 BF16), then32 words of B(K4096..5119). Low256 precedes high256.
// issue produces go at G and xa=A[m%256],xb=B[m%64] at G+5+m, exactly
// ot_s81hd_bundle's contract. No credits/completion choose issue dates.
// LOAD_W1024 accepts the actual80 consecutive1024-bit stage beats; layout is
// low256 through high256 in each beat, same A then B storage, same GO/stream.
// Data memories/output data are unreset; controls only reset. No full-head claim.
module ot_s81hd_xstore_replay #(
 parameter integer SK=11,
 parameter integer MUT_B_ADDR=0,
 parameter integer LOAD_W=512 //1024 matches the real stage ring:80 XB beats, no input serialization
)(
 input wire ck,rst_n,
 input wire load_begin,load_v,
 input wire [LOAD_W-1:0] load_d,
 input wire issue,
 output reg go,xv,busy,done,fault,
 output reg [255:0] xa,xb
);
 localparam integer STREAM_CYCLES=8192+7*SK;
 localparam integer CHUNKS=LOAD_W/256, AWORDS=65536/LOAD_W, WORDS=81920/LOAD_W;
 integer j;
 reg [255:0] a[0:255];
 reg [255:0] b[0:63];
 reg [7:0] loaded;
 reg [13:0] age;
 wire [13:0] m=age-14'd4;
 wire [5:0] bi=MUT_B_ADDR ? (m[5:0]^6'd1) : m[5:0];
 always @(posedge ck) begin
  if(load_v && !busy && !load_begin && loaded<WORDS) begin
   for(j=0;j<CHUNKS;j=j+1)
    if(loaded<AWORDS) a[loaded*CHUNKS+j]<=load_d[j*256+:256];
    else b[(loaded-AWORDS)*CHUNKS+j]<=load_d[j*256+:256];
  end
  if(busy && age>=4 && age<STREAM_CYCLES+4) begin xa<=a[m[7:0]];xb<=b[bi];end
 end
 always @(posedge ck or negedge rst_n) begin
  if(!rst_n) begin loaded<=0;age<=0;go<=0;xv<=0;busy<=0;done<=0;fault<=0;end
  else begin
   go<=0;xv<=0;done<=0;
   if(load_begin) begin
    if(busy || load_v || issue) fault<=1;
    else loaded<=0;
   end
   if(load_v) begin
    if(busy || load_begin || loaded>=WORDS) fault<=1;
    else loaded<=loaded+1'b1;
   end
   if(issue) begin
    if(busy || loaded!=WORDS || load_begin || load_v) fault<=1;
    else begin go<=1;busy<=1;age<=0;end
   end
   if(busy) begin
    age<=age+1'b1;
    xv<=age>=4 && age<STREAM_CYCLES+4;
    if(age==STREAM_CYCLES+3) begin busy<=0;done<=1;end
   end
  end
 end
 initial if((LOAD_W!=512 && LOAD_W!=1024) || SK<0 || STREAM_CYCLES+4>=16384) $fatal(1,"unsupported head skew");
endmodule
`default_nettype wire
