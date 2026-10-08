`timescale 1ns/1ps
module tb_collective_reset_entry;
 reg cs=0,cl=0,ps=0,pl=0;
 wire rn,pn,offr,offp;
 integer se=0,le=0,checks=0;
 always #5 cs=~cs;
 always #7 cl=~cl;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) dut(cs,cl,ps,pl,rn,pn);
 ot_hbm_collective_reset_entry off(cs,cl,ps,pl,offr,offp);
 always @(posedge cs or posedge ps) begin
  if(ps)se=0;else se=se+1;
  #0.001;
  if(rn !== (!ps && se>=2))$fatal(1,"stream reset edge count %0d",se);
  if(offr!==0 || offp!==0)$fatal(1,"disabled entry released reset");
  checks=checks+1;
 end
 always @(posedge cl or posedge pl) begin
  if(pl)le=0;else le=le+1;
  #0.001;
  if(pn !== (!pl && le>=2))$fatal(1,"link reset edge count %0d",le);
  checks=checks+1;
 end
 initial begin
  #1;ps=1;pl=1;
  #1;ps=0;pl=0;
  #50;
  repeat(12)begin
   // Short cold-reset pulses between clock edges must still assert immediately.
   ps=1;pl=1;#0.001;
   if(rn!==0 || pn!==0)$fatal(1,"asynchronous assertion missing");
   #0.499;ps=0;#0.25;pl=0;
   #37.25;
  end
  #30;
  if(checks<100)$fatal(1,"insufficient reset checks");
  $display("PASS independent clock cold reset checks=%0d",checks);$finish;
 end
endmodule
