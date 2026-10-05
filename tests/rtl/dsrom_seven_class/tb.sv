`timescale 1ns/1ps
module tb;
 reg fast_clk=0,slow_clk=0; always #3 fast_clk=~fast_clk; always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0;
 reg [13:0] abort_s=0,abort_d=0,in_v=0,out_ready=0,retire_v=0,reconcile_v=0,allcopies_fenced=0;
 wire [13:0] in_ready,out_v,retire_ready,pending,quarantined;
 reg [14*16128-1:0] in_data=0; wire [14*16128-1:0] out_data;
 reg [14*228-1:0] in_owner=0,retire_owner=0,reconcile_owner=0;
 wire [14*228-1:0] out_owner,pending_owner;
 integer cases=0,i; reg [16127:0] expected;
 ot_ds_seven_class_boundary_bank #(.ENABLE(1)) dut(.*);
 function integer width(input integer p);
 case(p) 0:width=16128;1:width=2236;2:width=31;3:width=2048;4:width=31;5:width=32;6:width=8064;7:width=16;8:width=512;9:width=2112;10:width=124;11:width=128;12:width=124;13:width=2048; endcase
 endfunction
 function integer fs(input integer p); fs=(p==1||p==2||p==4||p==6||p==7||p==9||p==10||p==12); endfunction
 task sn(input integer p); if(fs(p)) @(negedge fast_clk); else @(negedge slow_clk); endtask
 task dn(input integer p); if(fs(p)) @(negedge slow_clk); else @(negedge fast_clk); endtask
 task send(input integer p,input integer owner);
 integer k; begin
 sn(p); while(!in_ready[p]) sn(p);
 expected=0;for(k=0;k<width(p);k=k+1) expected[k]=(k%3==0);
 in_data[p*16128+:16128]=expected;in_owner[p*228+:228]=owner;in_v[p]=1;
 sn(p);in_v[p]=0; if(!pending[p]) $fatal(1,"not owned %0d",p);
 end endtask
 task receive(input integer p,input integer owner);
 begin dn(p);while(!out_v[p])dn(p);
 repeat(3)begin
 if(out_data[p*16128+:16128]!==expected||out_owner[p*228+:228]!==228'(owner))$fatal(1,"payload/tag/stall %0d",p);
 dn(p);end
 out_ready[p]=1;dn(p);out_ready[p]=0;
 sn(p);if(!pending[p]||in_ready[p])$fatal(1,"delivery retired owner %0d",p);
 cases=cases+1;
 end endtask
 task receipt(input integer p,input integer owner);
 begin dn(p);while(!retire_ready[p])dn(p);
 retire_owner[p*228+:228]=owner;retire_v[p]=1;dn(p);retire_v[p]=0;end endtask
 initial begin
 repeat(5)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
 for(i=0;i<14;i=i+1)begin
 send(i,i+1);receive(i,i+1);receipt(i,i+1);
 sn(i);while(pending[i])sn(i);if(quarantined[i])$fatal(1,"unexpected quarantine");cases=cases+1;
 // A delivered owner is still outstanding when reset flushes the transport.
 send(i,i+100);receive(i,i+100);
 sn(i);abort_s[i]=1;dn(i);abort_d[i]=1;sn(i);
 fast_rst_n=0;slow_rst_n=0;repeat(6)@(negedge slow_clk);
 if(!pending[i]||!quarantined[i]||in_ready[i])$fatal(1,"reset lost debt %0d",i);
 fast_rst_n=1;slow_rst_n=1;abort_s[i]=0;abort_d[i]=0;
 repeat(12)sn(i);if(!pending[i]||in_ready[i])$fatal(1,"empty retired debt");
 reconcile_owner[i*228+:228]=i+100;reconcile_v[i]=1;sn(i);
 if(!pending[i])$fatal(1,"unfenced reconciliation");
 allcopies_fenced[i]=1;sn(i);reconcile_v[i]=0;allcopies_fenced[i]=0;
 if(pending[i]||quarantined[i])$fatal(1,"positive reconciliation refused");cases=cases+1;
 // Accepted but not delivered reset: FIFO flush must not erase source debt.
 send(i,i+200);sn(i);abort_s[i]=1;dn(i);abort_d[i]=1;sn(i);
 fast_rst_n=0;slow_rst_n=0;repeat(6)@(negedge slow_clk);
 if(!pending[i]||!quarantined[i])$fatal(1,"undelivered reset debt lost");
 fast_rst_n=1;slow_rst_n=1;abort_s[i]=0;abort_d[i]=0;
 repeat(12)dn(i);if(out_v[i]||in_ready[i])$fatal(1,"stale replay or new admission");
 // Even a positive fence with the WRONG owner is insufficient.
 reconcile_owner[i*228+:228]=i+201;reconcile_v[i]=1;allcopies_fenced[i]=1;sn(i);
 if(!pending[i])$fatal(1,"wrong reconciliation identity");
 reconcile_owner[i*228+:228]=i+200;sn(i);reconcile_v[i]=0;allcopies_fenced[i]=0;
 if(pending[i]||quarantined[i])$fatal(1,"positive reset reconciliation refused");cases=cases+1;
 end
 // Wrong identity never returns credit.
 send(0,999);receive(0,999);receipt(0,1000);repeat(12)sn(0);
 if(!pending[0]||!quarantined[0])$fatal(1,"wrong receipt released");cases=cases+1;
 $display("PASS DS_SEVEN_CLASS_RAW_COMPOSED classes=7 planes=14 cases=%0d reset_debt_preserved=1",cases);$finish;
 end
 initial begin #100000;$fatal(1,"test event bound");end
endmodule
