`timescale 1ns/1ps
module tb_host_pc_debt;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[287:0]land_es=0,host_es=0;reg[260:0]ctrl_er=0;
 reg completion_v=0,completion_we=0;
 wire[287:0]ctrl_es;wire[260:0]land_er;wire host_cr,host_ack,land_ack,fault,quiet;
 qkd_host_static_pc_emback_debt #(.MUT(MUT))dut(.ck(ck),.rst_n(rst_n),.land_es(land_es),.host_es(host_es),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),.completion_v(completion_v),.completion_we(completion_we),.land_er(land_er),.host_cr(host_cr),.host_ack(host_ack),.land_ack(land_ack),.fault(fault),.queue_quiet(quiet));
 integer accepted=0,launched=0,completed=0,read_accepted=0,read_returned=0,acks=0;
 integer cyc=0;reg debt_previous=0;
 always @(posedge ck)begin
  if(rst_n)begin
   if(land_es[0]||host_es[0])accepted=accepted+1;
   if(land_es[0]&&!land_es[286])read_accepted=read_accepted+1;
   if(ctrl_es[0])launched=launched+1;
   if(completion_v)completed=completed+1;
   if(land_er[0])read_returned=read_returned+1;
   if(host_ack||land_ack)acks=acks+1;
   // Output is a registered observation. Compare against debt known before
   // the preceding observation edge, not an internal counter alias.
   if(quiet&&debt_previous)$fatal(1,"FALSE_QUIET outstanding=%0d reads=%0d",accepted-completed,read_accepted-read_returned);
   debt_previous=(accepted!=completed)||(read_accepted!=read_returned);
  end
 end
 task tick(input integer n);repeat(n)begin @(negedge ck);cyc=cyc+1;end endtask
 task send_word(input bit wr,input bit host);begin
  if(host)host_es={1'b1,wr,5'd3,5'd4,19'd12,256'h1234,1'b1};
  else land_es={1'b1,wr,5'd3,5'd4,19'd12,256'h5678,1'b1};
  tick(1);host_es=0;land_es=0;
 end endtask
 task credit;begin ctrl_er[259]=1;tick(1);ctrl_er=0;end endtask
 task retire(input bit wr);begin completion_v=1;completion_we=wr;tick(1);completion_v=0;completion_we=0;end endtask
 initial begin
  tick(3);rst_n=1;tick(10);if(!quiet)$fatal(1,"RESET_DRAIN");
  send_word(1,1);tick(10);credit();tick(12);
  if(launched!=1||quiet)$fatal(1,"WRITE_OWNER_LOST");
  retire(1);tick(12);if(!quiet||acks!=1)$fatal(1,"WRITE_DRAIN");
  send_word(0,0);tick(10);credit();retire(0);tick(12);
  if(quiet)$fatal(1,"READ_PAYLOAD_DEBT_LOST");
  ctrl_er[0]=1;ctrl_er[258:1]=258'h123456;tick(1);ctrl_er=0;tick(12);
  if(!quiet||read_returned!=1)$fatal(1,"READ_DRAIN");
  send_word(1,1);send_word(1,0);send_word(1,1);send_word(1,0);tick(15);
  if(quiet||launched!=6)$fatal(1,"QUEUED_WRITE_DEBT");
  repeat(4)begin credit();tick(2);retire(1);tick(3);end
  tick(12);if(!quiet||fault||accepted!=6||completed!=6||acks!=5)$fatal(1,"FINAL exact accepted%0d complete%0d ack%0d fault%0d",accepted,completed,acks,fault);
  $display("PASS actual_queue accepted6 launched6 physical_done6 writes5 read_payload1");$finish;
 end
 initial begin #50000;$fatal(1,"TIMEOUT");end
endmodule
