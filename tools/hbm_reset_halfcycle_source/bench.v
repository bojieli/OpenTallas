`timescale 1ps/1ps
module bench;
 reg clk=0,rst=1,foreign_rst=1;wire [2:0] c,h;wire [3:0] r;
 hbm_halfcycle_station #(.ENABLE(1)) source(clk,rst,c[0],r[0],h[0]);
 hbm_halfcycle_station #(.ENABLE(1)) t1(c[0],r[0],c[1],r[1],h[1]);
 hbm_halfcycle_station #(.ENABLE(1)) t2(c[1],r[1],c[2],r[2],h[2]);
 hbm_halfcycle_pair #(.ENABLE(1)) face(c[2],r[2],h[2],r[3]);
 wire fc,fr,fh;hbm_halfcycle_station #(.ENABLE(1)) foreign_domain(clk,foreign_rst,fc,fr,fh);
 wire dc,dr,dh;hbm_halfcycle_station disabled(clk,rst,dc,dr,dh);
 integer i,j;reg [7:0] state;
 task check;input condition;input[511:0] msg;begin
 if(condition!==1)begin $display("FUNCTIONAL_FAIL %0s",msg);$fatal(1);end end endtask
 task tick;begin #341;clk=1;#683;clk=0;#1;end endtask
 task force_state;begin
 force source.enabled.pair.enabled.ff1.IQN=state[0];force source.enabled.pair.enabled.ff2.IQN=state[1];
 force t1.enabled.pair.enabled.ff1.IQN=state[2];force t1.enabled.pair.enabled.ff2.IQN=state[3];
 force t2.enabled.pair.enabled.ff1.IQN=state[4];force t2.enabled.pair.enabled.ff2.IQN=state[5];
 force face.enabled.ff1.IQN=state[6];force face.enabled.ff2.IQN=state[7];#1;
 release source.enabled.pair.enabled.ff1.IQN;release source.enabled.pair.enabled.ff2.IQN;
 release t1.enabled.pair.enabled.ff1.IQN;release t1.enabled.pair.enabled.ff2.IQN;
 release t2.enabled.pair.enabled.ff1.IQN;release t2.enabled.pair.enabled.ff2.IQN;
 release face.enabled.ff1.IQN;release face.enabled.ff2.IQN;#1;
 end endtask
 initial begin
 #1;check(r===4'bxxxx,"unforced cold unknown");check(dr===1'bx && dc===1'bx,"default off");
 rst=0;#10;check(r===0,"stopped-clock async assert");check(fr===1'bx,"foreign cold ownership");
 rst=1;#7;clk=1;#1;check(r===0,"positive edge before first negative cannot release");
 #700;clk=0;#1;check(r===0,"negative edge only releases first owned stage");
 #323;clk=1;#1;check(r[0]===1 && r[1]===0,"source releases only after genuine half-cycle");
 clk=0;#1;repeat(6)tick;check(r===15,"cold-first-use chain release");
 foreign_rst=0;#10;check(fr===0 && r===15,"independent owner assertion");
 rst=0;#2;check(r===0,"logical pulse assertion");rst=1;tick;rst=0;#10;check(r===0,"in-flight reassertion");
 repeat(3)begin #1024;check(r===0,"stopped asserted retention");end
 // Separate exhaustive testbench state injection; this is not the cold-X proof.
 for(i=0;i<256;i=i+1)begin
 rst=1;state=i;force_state;rst=0;#10;check(r===0,"arbitrary eight-Q-state stopped assert");
 rst=1;for(j=0;j<6;j=j+1)tick;check(r===15,"arbitrary-state post-reset first use");
 end
 $display("FUNCTIONAL_PASS cold_X distinct_from 256 arbitrary_Q assignments; stopped assert pulse reassert ownership first-use");
 $display("PHYSICAL_HOLD duty used only as digital stimulus; native timing pulse aperture age NULL");$finish;
 end
endmodule
