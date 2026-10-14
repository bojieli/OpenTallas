`timescale 1ns/1ps
// Default-off native TP8 Q reader: eight ACTUAL banked-VM responses of64
// binary32 values become32 ordered512-bit Q words. No arithmetic/rounding.
// Transaction adapter must bind req_ready to actual read admission and rsp_v
// to actual bank response (a fixed-latency read may carry a matched tag delay).
// It must not fabricate payloads or response-valid from elapsed time alone.
module ot_qfd_native_q_reader #(parameter integer ENABLE=0, MUT_BEAT=0)(
 input wire clk,rst_n,
 input wire start_v,input wire [15:0] start_epoch,input wire [23:0] start_base,
 output wire start_ready,
 output reg req_v,input wire req_ready,output reg [15:0] req_epoch,
 output reg [2:0] req_chunk,output reg [23:0] req_a0,req_a1,
 input wire rsp_v,input wire [15:0] rsp_epoch,input wire [2:0] rsp_chunk,
 input wire [2047:0] rsp_data,
 output reg q_v,input wire q_ready,output reg [5:0] q_beat,
 output reg [511:0] q_data,output reg [15:0] q_epoch,
 output reg emitted_done,output reg fault
);
 reg active,pending,have;reg [15:0] epoch;reg [23:0] base;
 reg [2:0] chunk;reg [1:0] part;reg [2047:0] buffer_r;
 wire accepted=req_v&&req_ready,qt=q_v&&q_ready;
 assign start_ready=ENABLE!=0&&!active&&!req_v&&!q_v&&!fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;pending<=0;have<=0;epoch<=0;base<=0;chunk<=0;part<=0;buffer_r<=0;req_v<=0;req_epoch<=0;req_chunk<=0;req_a0<=0;req_a1<=0;q_v<=0;q_beat<=0;q_data<=0;q_epoch<=0;emitted_done<=0;fault<=0;end
  else if(ENABLE!=0)begin
   emitted_done<=0;
   if(start_v)begin
    if(!start_ready||start_base>24'hfffe00)fault<=1;
    else begin active<=1;epoch<=start_epoch;base<=start_base;chunk<=0;part<=0;req_v<=1;req_epoch<=start_epoch;req_chunk<=0;req_a0<=start_base;req_a1<=start_base+1;end
   end
   if(accepted)begin req_v<=0;pending<=1;end
   if(rsp_v)begin
    if(!active||(!pending&&!accepted)||have||rsp_epoch!=epoch||rsp_chunk!=chunk)fault<=1;
    else begin buffer_r<=rsp_data;have<=1;pending<=0;part<=0;end
   end
   if(active&&have&&!fault&&(!q_v||qt))begin
    q_v<=1;q_data<=buffer_r[512*part+:512];q_epoch<=epoch;
    q_beat<={1'b0,chunk,part}^(MUT_BEAT!=0?6'd1:6'd0);
    if(part==3)begin have<=0;end else part<=part+1'b1;
   end else if(qt)begin
    q_v<=0;
    if(q_beat[1:0]==(MUT_BEAT!=0?2'd2:2'd3)&&!have)begin
     if(chunk==7)begin active<=0;emitted_done<=1;end
     else begin chunk<=chunk+1'b1;req_v<=1;req_epoch<=epoch;req_chunk<=chunk+1'b1;req_a0<=base+24'((chunk+1)*64);req_a1<=base+24'((chunk+1)*64+1);end
    end
   end
   if(fault)begin req_v<=0;q_v<=0;end
  end
 end
endmodule
