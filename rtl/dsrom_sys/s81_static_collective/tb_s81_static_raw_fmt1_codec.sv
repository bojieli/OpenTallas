`timescale 1ns/1ps
module tb_s81_static_raw_fmt1_codec;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,tx_v=0,tx_last=0,rx_frame_v=0,rx_expected_last=0;
 reg[9:0]tx_seq=0,rx_expected_seq=0;reg[551:0]tx_payload=0;reg[594:0]rx_frame=0;
 wire tx_frame_v,rx_v,rx_last,fault;wire[594:0]tx_frame;wire[551:0]rx_payload;
 s81_static_raw_fmt1_codec dut(.*);
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 integer k;
 initial begin
 for(k=0;k<4;k=k+1)begin
  rst_n=0;rx_frame_v=0;tx_v=0;step();rst_n=1;
  tx_seq=10'h321;tx_last=1;tx_payload={552{1'b1}};tx_v=1;step();tx_v=0;step();
  if(!tx_frame_v)$fatal(1,"TX latency");
  rx_frame=tx_frame;rx_expected_seq=10'h321;rx_expected_last=1;
  case(k)0:rx_frame[99]=~rx_frame[99];1:rx_expected_seq=10'h320;2:rx_expected_last=0;endcase
  rx_frame_v=1;step();rx_frame_v=0;step();
  if(k<3 && (!fault||rx_v))$fatal(1,"bad frame not rejected %0d",k);
  if(k==3 && (fault||!rx_v||rx_payload!=={552{1'b1}}||!rx_last))$fatal(1,"good frame");
  step();if(k<3 && !fault)$fatal(1,"fault not sticky");
 end
 $display("PASS raw codec CRC/sequence/last faults, sticky status, exact two-edge latency");$finish;
 end
endmodule
