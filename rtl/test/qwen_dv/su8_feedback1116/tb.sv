`timescale 1ns/1ps
module tb;
reg ck=0; always #0.5 ck=~ck;
reg rst_n=0,start=0; reg[456:0]si=0;
localparam[456:0] GUR=457'h0000000000000000000000000000000000040000000011010010000000000000000000000000000000000c80000004000000001100008000002, SILU=457'h0000000017f0000000000000000000000004000001000001e030000010000000004400000008000000002600000004000000001100004000002;
wire[243:0]gb;wire[2:0]gv;wire[7:0]lv;wire[767:0]pd;
wire nr,idle,fault;wire[15:0]prog,rows;
reg[399:0]feedback=0,last_feedback=0;integer delay_edges=48;
wire retire=feedback[delay_edges-1];
qfd_dv_s5_su8_rst3 u(.ck(ck),.rst_n(rst_n),.start(start),.si(si),.l_retire(retire),.l_last(last_feedback[delay_edges-1]),.l_fault(8'b0),.kv_we(8'b0),.rd_v(1'b0),.red_busy(1'b0),.red_fault(1'b0),.lvm_we(8'b0),.gb(gb),.gv(gv),.lv1(lv),.pd1(pd),.su_nr(nr),.su_idle(idle),.su_fault(fault),.su_prog(prog),.su_rows(rows));
integer cy=0,origin=0,active=0,first_ready=-1,last_retire=-1,nemit=0,nretire=0,nfault=0;
always @(posedge ck)begin
 cy=cy+1;
 if(!rst_n) begin feedback<=0;last_feedback<=0;end else begin feedback<={feedback[398:0],gv[2]};last_feedback<={last_feedback[398:0],gv[2]&&gv[0]};end
 if(active)begin
  if(gv[2])nemit=nemit+1;
  if(retire)begin nretire=nretire+1;last_retire=cy-origin;end
  if(fault||nr)nfault=nfault+1;
  if(cy-origin>=62 && first_ready<0 && u.ready)first_ready=cy-origin;
 end
end
integer k,probe48,probe162,target,fail=0,trial;
task automatic run_case(input integer latency,input integer next_start,input integer expect_fault,input integer sameclass,input integer mode);
begin
 @(negedge ck);active=0;rst_n=0;start=0;si=GUR;
 repeat(30)@(negedge ck);rst_n=1;repeat(30)@(negedge ck);
 delay_edges=latency;first_ready=-1;last_retire=-1;nemit=0;nretire=0;nfault=0;origin=cy+1;active=1;
 for(k=0;k<600;k=k+1)begin
  start=(k==0 || k==next_start);
  si=k<60 ? GUR:SILU;
  if(sameclass)si[265:263]=0;
  @(negedge ck);
 end
 active=0;start=0;
 $display("FEEDBACK latency=%0d next_start=%0d expect_fault=%0d sameclass=%0d first_ready=%0d last_retire=%0d emit=%0d retire=%0d fault_cycles=%0d inflight=%0d",latency,next_start,expect_fault,sameclass,first_ready,last_retire,nemit,nretire,nfault,u.inflight);
 if(mode==0)begin
  if(nemit!=32 || nretire!=32 || nfault!=0 || u.inflight!=0 || first_ready<0)fail=fail+1;
 end else if(expect_fault)begin
  if(nfault==0)fail=fail+1;
 end else begin
  if(nfault!=0 || nemit!=48 || nretire!=48 || u.inflight!=0)fail=fail+1;
 end
end endtask
initial begin
 run_case(48,-1,0,0,0);probe48=first_ready;
 run_case(162,-1,0,0,0);probe162=first_ready;
 if(probe162-probe48!=114)begin $display("BAD_FEEDBACK_TRANSLATION");fail=fail+1;end
 // start->su_go is five source flops; measure the boundary, do not assume a busy margin.
 run_case(48,probe48-5,0,0,1);
 run_case(48,probe48-6,1,0,1);
 run_case(162,probe162-5,0,0,1);
 run_case(162,probe162-6,1,0,1);
 // Same SFU class may start while the older token still has inflight words.
 run_case(162,65,0,1,1);
 if(fail)$fatal(1,"SU8_FEEDBACK_FAIL %0d",fail);
 $display("SU8_FEEDBACK_PASS source_control_only actual_GUR_SILU_words delta114 first_ready_boundary_and_early_mutants");$finish;
end
endmodule
