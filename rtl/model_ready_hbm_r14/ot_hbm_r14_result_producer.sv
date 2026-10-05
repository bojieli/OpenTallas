`timescale 1ps/1fs
// Finite RF commit producer for ownership/IRS exercise ONLY.27clock residency,
// real register computation and held completion. These integer test operations
// are not transformerSCORES/EXP/PV arithmetic and confer no numerical credit.
module ot_hbm_r14_result_producer(
 input wire clk,rst_n,iv,output wire ir,input wire [2:0] kind,
 input wire [31:0] input_result,input wire [63:0] producer,input wire [31:0] transport,
 output reg commit,output wire complete_v,input wire complete_r,
 output wire [2:0] result_kind,output wire [63:0] result_producer,
 output wire [31:0] result_transport,output wire [31:0] RF_result);
 reg live,held;reg [4:0] count;reg [2:0] opcode;
 reg [63:0] epoch;reg [31:0] transfer,value;
 assign ir=!live;assign complete_v=held;assign result_kind=opcode;
 assign result_producer=epoch;assign result_transport=transfer;assign RF_result=value;
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin live<=0;held<=0;count<=0;opcode<=0;epoch<=0;transfer<=0;value<=0;commit<=0;end
   else begin
     commit<=0;
     if(iv&&ir)begin live<=1;opcode<=kind;epoch<=producer;transfer<=transport;value<=input_result;count<=0;end
     if(live&&!held)begin
       value<={value[30:0],value[31]}^32'h1f123bb5;
       if(count==26)begin commit<=1;held<=1;end else count<=count+1'b1;
     end
     if(complete_v&&complete_r)begin held<=0;live<=0;end
   end
 end
endmodule
