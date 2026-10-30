`timescale 1ps/1ps
module tb;
parameter BAD=0;reg clk=0,rst=0,ctx=0,cv=0;reg[307:0]cmd=0;reg[88:0]p=0;reg[15:0]fv=0,fb=0;reg[255:0]fe=0;
wire[15:0]rv,xv;wire ccv,fault;wire[88:0]cp;integer i,b;
ot_hbm_static_load_raw_copy_fill_route d(clk,rst,ctx,cmd,cv,p,fv,fb,fe,rv,xv,ccv,cp,fault);
always begin #416;clk=1;#417;clk=0;end
task tick;begin @(negedge clk);end endtask
task meta(input[15:0]e);begin tick;p=0;p[52]=1;p[69:54]=e;p[84:70]=77;p[88:85]=9;cv=1;tick;cv=0;p=0;end endtask
task tags(input[15:0]e);begin for(b=0;b<16;b=b+1)fe[b*16+:16]=e;end endtask
initial begin repeat(5)tick;rst=1;tick;
// All RAWvalidpatterns, including unowned/malformed tags, are unchanged when
// no accepted LOADcontext exists; downstream native RAW retains faultchecking.
fb=16'ha55a;fe='x;
for(i=0;i<65536;i=i+1)begin fv=i;#1;if(rv!==fv||xv!==0)$fatal(1,"legacy changed");end
fv=0;fb=0;fe=0;ctx=1;cmd[291]=0;cmd[307:292]=21;cmd[103:89]=77;cmd[85:82]=9;
if(BAD==1)begin tags(21);fv=16'h81;tick;tick;end
else if(BAD==2)begin tick;p=0;p[52]=1;p[69:54]=21;p[84:70]=78;p[88:85]=9;cv=1;tick;cv=0;end
else begin
meta(21);tags(21);fv=16'ha55a;#1;if(rv!==0||xv!==fv)$fatal(1,"copy-only split");tick;fv=0;
// A foreign old RAWepoch is never swallowed by the active COPYcontext.
tags(20);fv=16'hffff;#1;if(rv!==fv||xv!==0)$fatal(1,"foreign RAW swallowed");tick;fv=0;
cmd[307:292]=22;tick;p=0;p[0]=1;p[17:2]=22;cv=1;tick;cv=0;p=0;
meta(22);tags(22);fv=16'h3c;#1;if(rv!==fv||xv!==fv)$fatal(1,"joint split");tick;fv=0;
end
repeat(2)tick;
if(BAD==0)begin if(fault)$fatal(1,"baseline fault");$display("PASS RAW_COPY_ROUTE legacy65536validpatterns4state_malformed_tags/COPYonly/joint/foreignRAWpreserved");end
else begin if(!fault)$fatal(1,"control escaped");$display("PASS CONTROL_CAUGHT bad=%0d",BAD);end
$finish;end
endmodule
