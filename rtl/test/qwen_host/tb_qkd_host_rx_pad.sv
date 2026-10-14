`timescale 1ns/1ps
module tb_qkd_host_rx_pad;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,in_v=0,out_cr=0;reg[1023:0]in_d=0;
 wire in_cr,out_v,fault;wire[545:0]out_d;
 qkd_host_rx_pad #(.MUT(MUT))dut(.*);
 integer checks=0;
 task tick;begin @(posedge clk);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 reg[527:0]payload={16'hb59a,{16{32'h8ac357e1}}};
 initial begin repeat(4)tick();rst_n=1;repeat(4)tick();
  @(negedge clk);in_v=1;in_d={496'd0,payload};@(negedge clk);in_v=0;tick();
  check(out_v&&out_d=={18'd0,payload}&&!fault,"all528 payload bits preserved");
  @(negedge clk);out_cr=1;@(negedge clk);out_cr=0;tick();check(in_cr,"independent physical queue credit");
  @(negedge clk);in_v=1;in_d={496'd1,payload};@(negedge clk);in_v=0;tick();check(!out_v&&fault,"nonzero FDI payload pad rejected");
  $display("PASS HOST_RX_PAD checks=%0d",checks);$finish;end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
