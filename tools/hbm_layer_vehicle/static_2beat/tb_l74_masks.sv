`timescale 1ns/1ps
// Actual L74 semantics: pgp.valid is held c_busy; TKM del_slot is a one-edge
// strobe matching del_valid. A full TKM ingress quartet arrives every8 edges.
module tb_l74_masks;
 parameter integer OLD_MASK=0,BAD_SLOT=0;
 localparam[8:0] MASK=OLD_MASK?9'b111:BAD_SLOT?9'b001:9'b101;
 localparam[8:0] HOLD=OLD_MASK?9'b0:9'b10;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,start=0;reg[8:0]d=0;wire[5:0]beat;wire side,slot0,tf,rf;wire[8:0]q;wire qs;
 reg[5:0]pipe[0:2];reg sidepipe[0:2];
 always@(posedge clk)begin pipe[0]<=beat;sidepipe[0]<=side;for(integer j=1;j<3;j=j+1)begin pipe[j]<=pipe[j-1];sidepipe[j]<=sidepipe[j-1];end end
 ot_hbm_static_2beat_tx #(.W(9),.B(6),.S(1),.CONTROL_MASK(MASK),.HOLD_MASK(HOLD)) tx(clk,rst_n,start,d,1'b0,beat,side,tf,slot0);
 ot_hbm_static_2beat_rx #(.W(9),.B(6),.S(1),.LINK_STAGES(3),.CONTROL_MASK(MASK),.HOLD_MASK(HOLD)) rx(clk,rst_n,start,pipe[2],sidepipe[2],q,qs,rf);
 integer words=0,checks=0,slotcount=0;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
  for(integer i=0;i<160;i=i+1)begin
   d=9'b10; // programme-active remains asserted through both transmit phases.
   if(slot0)begin
    if(words%4==0)begin d[0]=1;d[2]=1;end
    words++;
   end
   @(posedge clk);#0.01;
   if(i>20)begin
    if(tf||rf)$fatal(1,"L74_MASK legal programme-active faulted");
    if(q[1]!==1'b1)$fatal(1,"L74_MASK programme-active did not hold");
    if(q[0]!==q[2])$fatal(1,"L74_MASK TKM del_slot outlives del_valid");
    if(q[0])slotcount++;
    checks++;
   end
   @(negedge clk);
  end
  if(checks!=139||slotcount<10)$fatal(1,"L74_MASK coverage");
  $display("L74_MASK PASS held_programme_active139edges TKM_slot8_count%0d",slotcount);$finish;
 end
endmodule
