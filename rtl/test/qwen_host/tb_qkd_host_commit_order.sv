`timescale 1ns/1ps
module tb_qkd_host_commit_order;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;reg rst_n=0,issue_v=0;reg[6:0]issue_pc=0;reg[127:0]acks=0;
 wire prefix_v,fault;wire[31:0]prefix_count;
 qkd_host_commit_order #(.MUT(MUT))dut(.*);
 integer cr=256,issued=0,seen=0,cycles=0;bit released=0;
 always @(posedge ck)begin cycles++;if(prefix_v)begin seen++;cr++;end
 if(!released&&seen)$fatal(1,"prefix escaped oldest unretired PC");end
 task tick;@(posedge ck);#1;endtask
 initial begin repeat(4)tick();rst_n=1;repeat(4)tick();
  for(integer n=0;n<128;n++)begin @(negedge ck);issue_v=1;issue_pc=7'(n);cr--;issued++;end
  @(negedge ck);issue_v=0;acks={128{1'b1}}^128'd1;
  @(negedge ck);acks=0;repeat(40)tick();if(fault||prefix_count)$fatal(1,"later PCs do not commit oldest");
  @(negedge ck);released=1;acks=1;@(negedge ck);acks=0;
  wait(prefix_count==128);repeat(8)tick();if(seen!=128||fault||cr!=256)$fatal(1,"exact first prefix");
  // Refill/full/wrap three rounds; completed PC0 repeated128 times.
  for(integer round=0;round<3;round++)begin
   for(integer n=0;n<256;n++)begin @(negedge ck);issue_v=1;issue_pc=7'(n%128);cr--;issued++;end
   @(negedge ck);issue_v=0;repeat(8)tick();
   if(dut.total!=256||cr!=0)$fatal(1,"full window bounded");
   for(integer pass=0;pass<2;pass++)begin @(negedge ck);acks={128{1'b1}};@(negedge ck);acks=0;end
   wait(prefix_count==32'(issued));repeat(8)tick();if(fault||cr!=256)$fatal(1,"exact wrap prefix");
  end
  // Ghost ACK has no outstanding issue on that PC.
  @(negedge ck);acks=128'd1<<63;@(negedge ck);acks=0;repeat(4)tick();if(!fault)$fatal(1,"ghost PC acknowledgement rejected");
  $display("PASS HOST_COMMIT_ORDER issues=%0d visibility=%0d cycles=%0d",issued,seen,cycles);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout issued=%0d prefix=%0d",issued,prefix_count);end
endmodule
