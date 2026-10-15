`timescale 1ns/1ps
// Legacy forward frame {seq10,last,payload552,CRC32}. Last is independent
// of payload[551]. Two registered edges each way; no replay or credit gating.
// Calendar metadata is supplied on the edge rx_frame is sampled.
module s81_static_raw_fmt1_codec #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire tx_v,input wire[9:0]tx_seq,
 input wire tx_last,input wire[551:0]tx_payload,
 output reg tx_frame_v,output reg[594:0]tx_frame,
 input wire rx_frame_v,input wire[594:0]rx_frame,
 input wire[9:0]rx_expected_seq,input wire rx_expected_last,
 output reg rx_v,output reg rx_last,output reg[551:0]rx_payload,
 output reg fault
);
 wire[562:0]pay={tx_seq,tx_last,tx_payload};
 wire[31:0]tl,th,z,rl,rh;
 ot_link_crc32 #(.W(563)) tlo(.d({282'b0,pay[280:0]}),.crc(tl));
 ot_link_crc32 #(.W(563)) thi(.d({pay[562:281],281'b0}),.crc(th));
 ot_link_crc32 #(.W(563)) zero(.d(563'b0),.crc(z));
 ot_link_crc32 #(.W(563)) rlo(.d({282'b0,rx_frame[312:32]}),.crc(rl));
 ot_link_crc32 #(.W(563)) rhi(.d({rx_frame[594:313],281'b0}),.crc(rh));
 reg tv,rv;reg[562:0]tp;reg[31:0]tlo_q,thi_q,rlo_q,rhi_q;
 reg[594:0]rp;reg[9:0]seq_q;reg last_q;
 wire ok=rp[31:0]==(rlo_q^rhi_q^z) && rp[594:585]==seq_q && rp[584]==last_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin tv<=0;rv<=0;tx_frame_v<=0;rx_v<=0;fault<=0;tp<=0;rp<=0;
   tlo_q<=0;thi_q<=0;rlo_q<=0;rhi_q<=0;tx_frame<=0;rx_payload<=0;
   rx_last<=0;seq_q<=0;last_q<=0;end
  else begin
   tv<=tx_v;tp<=pay;tlo_q<=tl;thi_q<=th;
   tx_frame_v<=tv;tx_frame<={tp,tlo_q^thi_q^z} ^ ((MUT==1)?595'b1:595'b0);
   rv<=rx_frame_v;rp<=rx_frame;rlo_q<=rl;rhi_q<=rh;
   seq_q<=rx_expected_seq;last_q<=rx_expected_last;
   rx_v<=rv && ok;rx_last<=rp[584];rx_payload<=rp[583:32];
   if(rv && !ok)fault<=1;
  end
 end
endmodule
