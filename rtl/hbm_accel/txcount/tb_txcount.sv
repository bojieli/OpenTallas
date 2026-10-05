`timescale 1ns/1ps
module tb_txcount;
 reg clk=0;always #0.5 clk=~clk;
 reg por_n=1,rst_n=1,bv=0,mv=0,wa=0,fa=0,cr=0,sf=0;
 reg [5:0] count=2;reg [4:0] wi=0,fi=0;
 reg [54:0] mo=0,wo=0,fo=0;
 reg [6:0] wr=127,fr=127;reg [31:0] wj=32'hfe123456,fj=32'hfe123456;
 reg [3:0] wg=15,fg=15;
 wire br,mr,cv,fault;wire[6:0] rank;wire[31:0] job;wire[3:0] gen;
 wire offbr,offmr,offcv,offfault;
 ot_hbm_txcount_sm off_dut(.clk(clk),.por_n(por_n),.rst_n(rst_n),.begin_valid(bv),.begin_ready(offbr),.manifest_ready(offmr),.complete_valid(offcv),.fault(offfault));
 integer checks=0,i,last_edge,cyc=0,lat;
 always @(posedge clk)cyc<=cyc+1;
 ot_hbm_txcount_sm #(.ENABLE(1)) dut(.clk(clk),.por_n(por_n),.rst_n(rst_n),
 .begin_valid(bv),.begin_ready(br),.begin_rank(7'd127),.begin_job(32'hfe123456),.begin_gen(4'd15),.begin_count(count),
 .manifest_valid(mv),.manifest_ready(mr),.manifest_owner55(mo),
 .w4_accept(wa),.w4_index(wi),.w4_owner55(wo),.w4_rank(wr),.w4_job(wj),.w4_gen(wg),
 .w6_accept(fa),.w6_index(fi),.w6_owner55(fo),.w6_rank(fr),.w6_job(fj),.w6_gen(fg),
 .source_fault(sf),.complete_valid(cv),.complete_ready(cr),.complete_rank(rank),.complete_job(job),.complete_gen(gen),.fault(fault));
 function automatic[54:0] own(input integer n);own={7'd127,3'd5,32'hfe123456,4'd15,9'(n)};endfunction
 task ck(input bit ok,input string msg);begin checks=checks+1;if(!ok)$fatal(1,"HA1 %s",msg);end endtask
 task tick;begin @(posedge clk);#0.1;end endtask
 task clear;begin @(negedge clk);por_n=0;rst_n=1;bv=0;mv=0;wa=0;fa=0;cr=0;sf=0;wi=0;fi=0;wr=127;fr=127;wj=32'hfe123456;fj=wj;wg=15;fg=15;tick;@(negedge clk);por_n=1;tick;end endtask
 task setup(input integer n);begin
 clear;@(negedge clk);count=n;bv=1;#0.01;ck(br,"begin admitted");tick;
 @(negedge clk);bv=0;mv=1;
 for(i=0;i<n;i=i+1)begin mo=own(i);#0.01;ck(mr,"manifest slot capacity");tick;@(negedge clk);end
 mv=0;ck(!mr&&!br&&!cv,"sealed count no premature completion or reuse");
 end endtask
 task event_pair(input integer n);begin
 @(negedge clk);wa=1;fa=1;wi=n;fi=n;wo=own(n);fo=own(n);tick;
 @(negedge clk);wa=0;fa=0;#0.01;
 end endtask
 initial begin
 setup(2);ck(!offbr&&!offmr&&!offcv&&!offfault,"default-off inert");event_pair(0);ck(!cv,"missing transaction holds");
 repeat(10)begin tick;ck(!cv,"no timer arrival");end
 event_pair(1);ck(cv&&!fault,"both exact counts complete");
 for(i=0;i<8;i=i+1)begin tick;ck(cv&&!br,"completion backpressure holds debt");end
 ck(rank==127&&job==32'hfe123456&&gen==15,"retained context");
 @(negedge clk);cr=1;tick;@(negedge clk);cr=0;ck(br&&!cv,"scheduler completion consumed");
 // stale accepted event after completion must quarantine, never reopen debt.
 wa=1;wi=1;wo=own(1);tick;ck(fault&&!cv,"stale after completion");
 setup(2);event_pair(0);@(negedge clk);wa=1;wi=0;wo=own(0);tick;ck(fault&&!cv,"duplicate ACK");
 setup(2);event_pair(0);@(negedge clk);fa=1;fi=0;fo=own(0);tick;ck(fault&&!cv,"duplicate fence");
 setup(1);@(negedge clk);wa=1;wo=own(0);wg=14;tick;ck(fault&&!cv,"wrong gen");
 setup(1);@(negedge clk);wa=1;wo=own(0);wr=126;tick;ck(fault&&!cv,"wrong rank");
 setup(1);@(negedge clk);fa=1;fo=own(0);fj=fj^1;tick;ck(fault&&!cv,"wrong job");
 setup(1);@(negedge clk);wa=1;wo=own(0)^1;tick;ck(fault&&!cv,"wrong owner");
 setup(1);@(negedge clk);fa=1;fi=31;fo=own(0);tick;ck(fault&&!cv,"out of manifest");
 setup(1);event_pair(0);@(negedge clk);wa=1;wo=own(0);cr=1;#0.01;ck(!cv,"duplicate masks simultaneous release");tick;ck(fault&&!br,"duplicate cannot free");
 setup(2);event_pair(0);@(negedge clk);rst_n=0;tick;ck(fault&&!cv,"runtime reset retains debt");@(negedge clk);rst_n=1;tick;ck(!br,"reset cannot readmit");
 setup(1);@(negedge clk);dut.on.state_code=dut.on.state_code^72'd3;#0.01;ck(fault&&!cv,"mutable state UE quarantine");
 clear;@(negedge clk);count=2;bv=1;tick;@(negedge clk);bv=0;mv=1;mo=own(0);tick;
 @(negedge clk);mo=own(0);tick;ck(fault&&!cv,"duplicate manifest rejected");
 clear;@(negedge clk);count=1;bv=1;tick;@(negedge clk);bv=0;mv=1;mo=own(0)^(55'd1<<9);tick;ck(fault&&!cv,"foreign manifest generation");
 setup(32);for(i=0;i<32;i=i+1)begin event_pair(i);if(i<31)ck(!cv,"count capacity no overflow");end
 ck(cv&&!fault,"full 32 transaction count");
 $display("PASS_HA1_COUNTER checks=%0d max_count=32 no_timers=1 protocol_only=1",checks);$finish;
 end
endmodule
