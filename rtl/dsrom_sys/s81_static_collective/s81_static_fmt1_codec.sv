`timescale 1ns/1ps
// Exact legacy reliable-link forward format, CRC polynomial/bit order and split
// pipeline. Normal mode is scheduled, without ACK/credit/replay-driven issue.
module s81_static_fmt1_codec #(parameter integer PEER=0)(
 input wire clk,rst_n,input wire tx_v,input wire[568:0]tx_record,
 output reg tx_frame_v,output reg[594:0]tx_frame,
 input wire rx_frame_v,input wire[594:0]rx_frame,
 output reg rx_v,output reg[568:0]rx_record,output reg fault
);
 wire[562:0]pay={tx_record[556:547],tx_record[513],4'b0,1'b1,tx_record[546:0]};
 wire[31:0]tl,th,z,rl,rh;
 ot_link_crc32 #(.W(563)) tlo(.d({282'b0,pay[280:0]}),.crc(tl));
 ot_link_crc32 #(.W(563)) thi(.d({pay[562:281],281'b0}),.crc(th));
 ot_link_crc32 #(.W(563)) zero(.d(563'b0),.crc(z));
 ot_link_crc32 #(.W(563)) rlo(.d({282'b0,rx_frame[32+:281]}),.crc(rl));
 ot_link_crc32 #(.W(563)) rhi(.d({rx_frame[594:313],281'b0}),.crc(rh));
 reg tv,rv;reg[562:0]tp;reg[31:0]tlo_q,thi_q,rlo_q,rhi_q;
 reg[594:0]rp;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin tv<=0;rv<=0;tx_frame_v<=0;rx_v<=0;fault<=0;tp<=0;rp<=0;
   tlo_q<=0;thi_q<=0;rlo_q<=0;rhi_q<=0;tx_frame<=0;rx_record<=0;end
  else begin
   tv<=tx_v;tp<=pay;tlo_q<=tl;thi_q<=th;
   tx_frame_v<=tv;tx_frame<={tp,tlo_q^thi_q^z};
   if(tx_v && (tx_record[562:557]!=0 || tx_record[566:563]!=4'hf))fault<=1;
   rv<=rx_frame_v;rp<=rx_frame;rlo_q<=rl;rhi_q<=rh;
   rx_v<=rv && rp[31:0]==(rlo_q^rhi_q^z) && rp[583:580]==0 && rp[579] && rp[584]==rp[545];
   if(rv && (rp[31:0]!=(rlo_q^rhi_q^z) || rp[583:580]!=0 || !rp[579] || rp[584]!=rp[545]))fault<=1;
   rx_record<={2'(PEER),4'hf,6'b0,rp[594:585],rp[578:32]};
  end
 end
endmodule
