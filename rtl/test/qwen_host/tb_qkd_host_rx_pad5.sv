`timescale 1ns/1ps
module tb_qkd_host_rx_pad5;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg in_v=0,out_cr=0;reg[1023:0]in_d=0;wire in_cr,out_v,fault;wire[545:0]out_d;
 qkd_host_rx_pad5 #(.MUT(MUT))dut(.*);
 integer src=0,got=0,credits=5,pending=0,cycles=0;reg begun=0;
 function[527:0]word(input integer n);word={16'h437a,{15{32'h92ca771b}},n[31:0]};endfunction
 always @(posedge clk)if(begun)begin
  cycles++;
  if(in_cr)credits++;
  if(out_v)begin if(out_d!=={18'd0,word(got)})$fatal(1,"RXpad5 payload/padding/order %0d",got);got++;pending++;end
  if(fault)$fatal(1,"legal5 source credits faulted");
 end
 always @(negedge clk)if(begun)begin
  in_v=0;out_cr=0;
  if(cycles>80&&pending>0&&cycles%3==0)begin out_cr=1;pending--;end
  if(src<48&&credits>0)begin in_v=1;in_d={496'd0,word(src)};src++;credits--;end
 end
 task tick;begin @(negedge clk);end endtask
 initial begin
  repeat(5)tick;rst_n=1;repeat(4)tick;begun=1;
  wait(cycles==60);tick;if(src!=9||got!=4||fault)$fatal(1,"capacity reservation initial5 downstream4: src%0d got%0d",src,got);
  wait(got==48);repeat(80)tick;begun=0;in_v=0;out_cr=0;repeat(5)tick;
  if(credits!=5||dut.credits!=4||dut.count!=0)$fatal(1,"all credits must return");
  // Full1024 padding must be checked after input capture and withheld.
  in_v=1;in_d={1'b1,495'd0,word(48)};tick;in_v=0;repeat(5)tick;
  if(!fault||out_v)$fatal(1,"nonzero physical padding accepted");
  // Unsolicited downstream credit cannot manufacture capacity.
  rst_n=0;repeat(3)tick;rst_n=1;repeat(3)tick;out_cr=1;tick;out_cr=0;repeat(4)tick;
  if(!fault)$fatal(1,"extra downstream credit not rejected");
  // Ten uncredited inputs exceed four destinations plus five queue slots.
  rst_n=0;repeat(3)tick;rst_n=1;repeat(3)tick;
  for(integer n=0;n<10;n++)begin in_v=1;in_d={496'd0,word(n)};tick;end
  in_v=0;repeat(5)tick;if(!fault)$fatal(1,"sixth queued word silently accepted");
  $display("PASS RXPAD5 exact48 initial5 downstream4 queued5 longstall paddingbad ghostcredit overflow failclosed");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
