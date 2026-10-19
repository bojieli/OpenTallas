`timescale 1ps/1ps
module bench;
 reg clk=0,rst=1,other=1; wire [3:0] c,r;
 hbm_private_reset_station #(.ENABLE(1)) source(clk,rst,c[0],r[0]);
 hbm_private_reset_station #(.ENABLE(1)) transport1(c[0],r[0],c[1],r[1]);
 hbm_private_reset_station #(.ENABLE(1)) transport2(c[1],r[1],c[2],r[2]);
 hbm_private_reset_face face(c[2],r[2],transport2.enabled.hi,r[3]);
 assign c[3]=c[2];
 wire oc,orr; hbm_private_reset_station #(.ENABLE(1)) foreign(clk,other,oc,orr);
 wire dc,dr; hbm_private_reset_station disabled(clk,rst,dc,dr);
 integer i,first;
 task check;input condition;input[511:0] msg;begin if(condition!==1)begin $display("FUNCTIONAL_FAIL %0s",msg);$fatal(1);end end endtask
 task edge_clock;begin #50;clk=1;#10;clk=0;#10;end endtask
 initial begin
 #1;check(r===4'bxxxx,"cold state must remain unknown without reset");
 check(dr===1'bx && dc===1'bx,"prototype default must stay inactive");
 rst=0;#10;check(r===0,"asynchronous assertion with clock stopped");
 check(orr===1'bx,"domain ownership must preserve unrelated cold state");
 rst=1;edge_clock;check(r[0]===0,"first release edge must hold source");
 edge_clock;check(r[0]===1,"second release edge must release source");
 first=0;
 for(i=3;i<=12;i=i+1) begin edge_clock;if(r[3]===1 && first==0)first=i;end
 check(first!=0,"face eventually releases in functional example");
 $display("FUNCTIONAL_CHAIN_FIRST_OBSERVED_EDGE %0d",first);
 if(first<8)$display("PHASE_CONTRACT_REFUSAL forwarded same-edge example; no fixed compiler age");
 rst=0;#3;check(r===0,"short logical pulse asynchronous propagation");
 rst=1;edge_clock;rst=0;#3;check(r===0,"reassert in flight");
 repeat(3)begin #100;check(r===0,"stopped asserted clock retention");end
 rst=1;repeat(12)edge_clock;check(r===15,"release after reassert");
 other=0;#3;check(orr===0,"foreign reset own domain");check(r===15,"foreign assertion cannot reset hbm");
 $display("FUNCTIONAL_PASS four-state cold, truth, stopped clock, pulse, reassert, ownership");
 $display("PHYSICAL_TIMING_NULL TT FF minCQ recovery removal pulsewidth phase POR age");$finish;
 end
endmodule
