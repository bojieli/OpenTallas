`timescale 1ns/1ps
// KV-P2-RTL 10-23: qkd_host_hc_station HCW 39 (START-only station of the admission / OBSX host compositions).
// Same protocol checks as tb_qkd_host_hc_station (payload, four-credit window, credit return, fail-closed overflow,
// role-0 only, runtime role mutation) on the 39-bit START slice {start38, gen, token, pos}.  MUT 1 = payload LSB flip.
module tb_qkd_host_hc_station_start39;
 parameter integer MUT=0;reg ck=0,rst_n=0;always #5 ck=~ck;
 reg[2:0]die_id=0;reg[38:0]raw_hc=0;reg cmd_cr=0;wire cmd_v,source_cr,available,fault;wire[38:0]cmd_hc;
 qkd_host_hc_station #(.MUT(MUT),.HCW(39))dut(.*);
 reg[38:0]expected[0:63];integer sent=0,got=0,returns=0;
 always @(posedge ck)if(rst_n)begin
  if(cmd_v)begin if(cmd_hc!==expected[got])$fatal(1,"start hc payload corruption %0d",got);got++;end
  if(source_cr)returns++;
 end
 task tick;begin @(negedge ck);end endtask
 task send;reg[38:0]h;begin
  h=39'(sent)*39'h5deabc5473;h[38]=1'b1;expected[sent]=h;sent++;raw_hc=h;tick;raw_hc=0;
 end endtask
 initial begin repeat(4)tick;rst_n=1;repeat(3)tick;
  // a nonzero payload without START is not an event
  raw_hc=39'h0123456789;tick;raw_hc=0;repeat(4)tick;if(got!=0||fault)$fatal(1,"payload without START raised an event");
  for(integer round=0;round<8;round++)begin
   for(integer k=0;k<4;k++)send;
   repeat(6)tick;if(fault||got!=sent||available)$fatal(1,"four START command credit window");
   for(integer k=0;k<4;k++)begin cmd_cr=1;tick;end cmd_cr=0;repeat(5)tick;
   if(fault||!available||returns!=(round+1)*4)$fatal(1,"command returned credits");
  end
  for(integer k=0;k<5;k++)send;repeat(6)tick;
  if(!fault||got!=36)$fatal(1,"uncredited START not rejected got%0d",got);
  rst_n=0;die_id=7;repeat(4)tick;rst_n=1;repeat(4)tick;send;repeat(5)tick;
  if(fault||got!=36||available)$fatal(1,"nonzero role emitted independent package command");
  die_id=6;repeat(4)tick;if(!fault)$fatal(1,"runtime role mutation not rejected");
  $display("PASS HC_STATION HCW39 START-only events=%0d bounded4 overflowfailclosed nostartnoevent",got);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
