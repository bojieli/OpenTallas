`timescale 1ns/1ps
module tb_qkd_host_static_pc;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[287:0]land_es=0,host_es=0;reg[260:0]ctrl_er=0;
 wire[260:0]land_er;wire[287:0]ctrl_es;wire host_cr,host_ack,fault;
 reg completion_v=0,completion_we=0;
 qkd_host_static_pc #(.MUT(MUT))dut(.*);
 integer checks=0,launches=0,acks=0,hostcredits=0,landcredits=0;
 reg[255:0]expected[0:7];reg[7:0]owners;
 task tick;begin @(posedge ck);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 always @(posedge ck)if(rst_n)begin
  if(ctrl_es[0])begin
   check(ctrl_es[287:286]==2'b11,"static host/data write bits");
   check(ctrl_es[285:276]=={5'd2,5'd3}&&ctrl_es[275:257]==19'd65,"static physical address exact");
   check(ctrl_es[256:1]==expected[launches],"roundrobin unchanged data");launches++;
  end
  if(host_ack)begin acks++;end
  if(host_cr)hostcredits++;
  if(land_er[259])landcredits++;
 end
 task push(input integer i);begin
  @(negedge ck);
  land_es={1'b1,1'b1,5'd2,5'd3,19'd65,256'(i*2),1'b1};
  host_es={1'b1,1'b1,5'd2,5'd3,19'd65,256'(i*2+1),1'b1};
  @(negedge ck);land_es=0;host_es=0;
 end endtask
 initial begin
  for(integer j=0;j<8;j++)expected[j]=256'(j);
  repeat(4)tick();rst_n=1;repeat(3)tick();
  for(integer j=0;j<4;j++)push(j);
  repeat(15)tick();check(launches==4,"four downstream credits bound");check(acks==0,"queue release never ACK");
  // Return scheduler queue credits long before actual timed column completion.
  repeat(4)begin @(negedge ck);ctrl_er[259]=1;@(negedge ck);ctrl_er[259]=0;end
  repeat(20)tick();check(launches==8&&hostcredits==4&&landcredits==4,"source credit identities");check(acks==0,"no early write completion");
  // First completion belongs to embedding. It must not ack host.
  @(negedge ck);completion_v=1;completion_we=1;@(negedge ck);completion_v=0;
  repeat(5)tick();check(acks==0,"embedding completion never host ACK");
  repeat(7)begin @(negedge ck);completion_v=1;completion_we=1;@(negedge ck);completion_v=0;repeat(2)tick();end
  repeat(8)tick();check(acks==4&&!fault,"four host writes visible only after completion");
  // Untagged event with no outstanding static command is an error.
  @(negedge ck);completion_v=1;@(negedge ck);completion_v=0;repeat(6)tick();check(fault,"ghost completion rejected");
  $display("PASS HOST_STATIC_PC checks=%0d launches=%0d acks=%0d",checks,launches,acks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
