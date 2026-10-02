`timescale 1ps/1fs
// Actual hardware finite32beat diagnosticclient. Addr is metadata-bound weight
// range; issuance is an explicit TEST phase, not opcode17 prefetched execution.
module ot_hbm_r14_burst_client(
 input wire clk,rst_n,start,input wire [33:0] base,output wire req_v,input wire req_r,
 output ot_hbm_r14_pkg::request_t req,input wire result_v,output wire result_r,
 input ot_hbm_r14_pkg::owned_t result,input wire result_we,result_credit,
 output reg done,output reg fault,output reg [31:0] seen);
 import ot_hbm_r14_pkg::*;
 reg [1:0] phase;reg [33:0] address;reg [31:0] RF;
 assign req_v=phase==1;assign result_r=phase==2;
 assign req='{id:'{die:1'b0,stack:2'b0,sector:address,producer:64'd7,transport:32'd8,
   caller:16'hfedc,client:6'd63,irs_slot:5'd0,irs_serial:32'd99},len:6'd32,we:1'b0,data:256'b0};
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin phase<=0;address<=0;RF<=0;seen<=0;done<=0;fault<=0;end
   else begin
     done<=0;if(start&&phase==0)begin address<=base;phase<=1;seen<=0;end
     if(req_v&&req_r)phase<=2;
     if(result_v&&result_r)begin
       if(result_we||result_credit||result.id.producer!=7||result.id.transport!=8||result.id.caller!=16'hfedc||
         result.id.sector!=address+34'(result.beat)||seen[result.beat])fault<=1;
       else begin seen[result.beat]<=1;RF<=RF^result.data[31:0];
         if((seen|(32'b1<<result.beat))==32'hffffffff)begin done<=1;phase<=0;end
       end
     end
   end
 end
endmodule
