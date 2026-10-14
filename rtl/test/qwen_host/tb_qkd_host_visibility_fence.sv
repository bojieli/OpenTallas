`timescale 1ns/1ps
module tb_qkd_host_visibility_fence;
 parameter integer MUT=0;
 reg ck=0,clk_h=0;always #5 ck=~ck;always #7 clk_h=~clk_h;
 reg rst_n=0;reg[7:0]ack_n=0;reg in_v=0;reg[63:0]in_d=0;wire in_cr,out_v;wire[63:0]out_d;reg out_cr=0;wire fault;wire[31:0]landed_debug;
 qkd_host_visibility_fence #(.MUT(MUT))dut(.*);
 integer nout=0,checks=0;
 always @(posedge clk_h)if(out_v)begin nout++;if(out_d!=64'h01002a0000000005)$fatal(1,"fenced descriptor changed");end
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 initial begin
  repeat(8)@(negedge clk_h);rst_n=1;repeat(8)@(negedge clk_h);
  in_d=64'h01002a0000000005;in_v=1;@(negedge clk_h);in_v=0;
  repeat(30)@(negedge clk_h);check(nout==0,"descriptor engine-done is not HBM visibility");
  @(negedge ck);ack_n=3;@(negedge ck);ack_n=0;repeat(30)@(negedge clk_h);check(nout==0&&landed_debug==3,"partial physical ACK not enough");
  @(negedge ck);ack_n=2;@(negedge ck);ack_n=0;repeat(30)@(negedge clk_h);check(nout==1&&landed_debug==5&&!fault,"real commit fence releases exact done");
  $display("PASS HOST_VISIBILITY_FENCE checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
