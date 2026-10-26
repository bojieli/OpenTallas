`timescale 1ns/1ps
module tb_hbm_all_target_status;
parameter integer MUT=0;
`include "all_targets.svh"
reg clk=0;always #5 clk=~clk;
reg rst_n=0,cv=0,dv=0,lv=0;
reg [7:0] ct=0;
reg [NT-1:0] ready=0,active=0;
reg [NF-1:0] fault=0;
wire br,pa,pf,df,irq;
ot_hbm_status_join #(.NT(NT),.NF(NF),.NH(1),.TGTS(TGTS),.MUT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.cfg_v(cv),.desc_v(dv),.launch_v(lv),.cfg_target(ct),
 .t_ready(ready),.t_active(active),.t_fault(fault),.h_fault(1'b0),
 .block_ready(br),.program_active(pa),.program_fault(pf),.die_fault(df),.irq(irq));
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
integer k,j;
initial begin
for(k=0;k<NT;k=k+1)begin
 rst_n=0;cv=0;dv=0;lv=0;ready=0;active=0;fault=0;repeat(3)tick;rst_n=1;repeat(12)tick;
 if(br!==0)$fatal(1,"empty programme unexpectedly ready");
 ct=TGTS[k*8+:8];dv=1;tick;dv=0;
 ready[k]=1;repeat(12)tick;
 if(br!==1)$fatal(1,"target %0d blocked by nonparticipants",ct);
 cv=1;tick;cv=0;tick;tick;
 if(br!==0)$fatal(1,"stale readiness guard bypassed target %0d",ct);
 repeat(12)tick;
 if(br!==1)$fatal(1,"guard failed to release");
 ready[k]=0;repeat(3)tick;if(br!==0)$fatal(1,"target notready ignored");
 ready[k]=1;repeat(3)tick;lv=1;tick;lv=0;active[k]=1;repeat(4)tick;
 if(pa!==1)$fatal(1,"target active lost");
 active[k]=0;repeat(4)tick;if(irq!==1)$fatal(1,"completion irq lost");
end
for(j=0;j<NF;j=j+1)begin
 fault=0;fault[j]=1;repeat(3)tick;if(pf!==1||df!==1)$fatal(1,"fault %0d lost",j);
end
$display("ALL_TARGET_STATUS PASS targets=%0d faults=%0d",NT,NF);$finish;
end
endmodule
