module tb #(parameter GMUT=0, CMUT=0);
 timeunit 1ns; timeprecision 1ps;
 reg ck=0; always #0.416667 ck=~ck;
 reg rst=0; reg[24:0]raw=0;reg[7:0]pf=0,tf=0;reg[92:0]tk=0;
 wire[92:0]gt;wire abort,ready;wire[15:0]epoch;wire[25:0]diag;
 wire[31:0]status;wire[3:0]groups;wire[7:0]pout,tout;
 qkd_host_service_guard #(.MUT(GMUT)) guard(ck,rst,raw,3'd0,pf,tf,1'b0,2'd0,16'd0,1'b0,64'd0,1'b0,32'd0,1'b0,16'd0,1'b0,16'd0,tk,gt,abort,ready,epoch,diag,status,groups,pout,tout,1'b0);
 reg[60:0]req=0;wire[181:0]hc;wire[119:0]res;
 // Replication is a fixture for controller reduction, NOT the production packet transport.
 qkd_host_ctl_service_pins #(.ENABLE_SERVICE(1),.MUT(CMUT)) ctl(ck,rst,1'b1,1'b0,3'd0,req,143'd0,{8{gt}},abort,ready,1'b0,1'b0,8'hff,hc,res);
 integer checks=0,n;reg[1:0]gen;
 task edge_n(input integer k);repeat(k)begin @(posedge ck);#0.01;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s status=%h res=%h",why,status,res);end endtask
 task reset;begin @(negedge ck);rst=0;raw=0;pf=0;tf=0;tk=0;req=0;edge_n(3);@(negedge ck);rst=1;edge_n(15);check(ready&&!abort,"startup");end endtask
 task start;begin @(negedge ck);req=1;@(negedge ck);req=0;n=0;while(!hc[38]&&n<10)begin edge_n(1);n++;end check(hc[38],"accepted START");gen=hc[37:36];edge_n(2);end endtask
 task report;begin @(negedge ck);tk[92]=1;tk[91:90]=gen;tk[89]=1;edge_n(10);end endtask
 initial begin
 reset();@(negedge ck);pf=8'hff;tf=8'hff;edge_n(12);
 check(pout==255&&tout==255,"physical diagnostics arrive");check(ready&&!abort&&!gt[88],"WITNESS physical transport do not enter bad or guarded fault");
 start();report();check(res[0]&&!res[1],"WITNESS healthy completion despite physical transport");
 reset();start();@(negedge ck);raw=1;
 edge_n(1);check(!abort,"fm edge1");edge_n(1);check(!abort,"fs edge2");edge_n(1);check(abort&&gt[88]&&!ready,"sticky abort edge3");
 edge_n(12);check(!res[0]&&!res[1],"WITNESS inflight service fault alone does not complete/fault package");
 report();check(res[0]&&res[1],"matching DONE carries sticky service fault");
 @(negedge ck);raw=0;edge_n(10);check(abort&&gt[88],"sticky health retained");
 reset();start();report();check(res[0]&&!res[1],"clean terminal");@(negedge ck);raw=1;edge_n(15);
 check(abort&&gt[88]&&!ready,"late fault observed continuously");check(!res[1],"WITNESS prior terminal cannot be retroactively faulted");
 @(negedge ck);req=1;@(negedge ck);req=0;edge_n(10);check(res[1]&&res[86],"subsequent start rejected fault");
 reset();check(!gt[88]&&!res[1]&&ready,"host reset clears health and controller");
 $display("PASS host health mechanism checks=%0d profile MU=0 ENABLE_SERVICE=1; packet/physical/reset timing unqualified",checks);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
