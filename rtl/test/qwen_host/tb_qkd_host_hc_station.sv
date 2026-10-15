`timescale 1ns/1ps
module tb_qkd_host_hc_station;
 parameter integer MUT=0;reg ck=0,rst_n=0;always #5 ck=~ck;
 reg[2:0]die_id=0;reg[181:0]raw_hc=0;reg cmd_cr=0;wire cmd_v,source_cr,available,fault;wire[181:0]cmd_hc;
 qkd_host_hc_station #(.MUT(MUT))dut(.*);
 reg[181:0]expected[0:63];integer sent=0,got=0,returns=0;
 always @(posedge ck)if(rst_n)begin
  if(cmd_v)begin if(cmd_hc!==expected[got])$fatal(1,"raw hc pulse/payload corruption %0d",got);got++;end
  if(source_cr)returns++;
 end
 task tick;begin @(negedge ck);end endtask
 task send(input integer bits);reg[181:0]h;begin
  h=182'(sent)*182'hdeabc54728;h[38]=bits[0];h[113]=bits[1];h[181]=bits[2];
  expected[sent]=h;sent++;raw_hc=h;tick;raw_hc=0;
 end endtask
 initial begin repeat(4)tick;rst_n=1;repeat(3)tick;
  for(integer round=0;round<8;round++)begin
   for(integer k=0;k<4;k++)send(1+((round*4+k)%7));
   repeat(6)tick;if(fault||got!=sent||available)$fatal(1,"four raw command credit window");
   for(integer k=0;k<4;k++)begin cmd_cr=1;tick;end cmd_cr=0;repeat(5)tick;
   if(fault||!available||returns!=(round+1)*4)$fatal(1,"command returned credits");
  end
  // Capacity overflow is explicit fail closed, rather than silent pulse loss.
  for(integer k=0;k<5;k++)send(7);repeat(6)tick;
  if(!fault||got!=36)$fatal(1,"uncredited raw command not rejected got%0d",got);
  rst_n=0;die_id=7;repeat(4)tick;rst_n=1;repeat(4)tick;send(7);repeat(5)tick;
  if(fault||got!=36||available)$fatal(1,"nonzero role emitted independent package command");
  die_id=6;repeat(4)tick;if(!fault)$fatal(1,"runtime role mutation not rejected");
  $display("PASS HC_STATION originalRAW182 events=%0d all7pulse-combinations bounded4 overflowfailclosed",got);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
