`timescale 1ns/1ps
module tb;
parameter integer OMIT=0;
reg ck=0,rst_n=0,reload=0,epoch_go=0,halt=0,bt=0,br=0;
reg [5:0] ba=0;reg [31:0] bd=0;
wire fault,join_q,sink_q;
qkd_d2d_cal_seq_pin_bc #(.EP_SKEW(3)) dut(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
 .bcfg_tx_we(bt),.bcfg_rx_we(br),.bcfg_addr(ba),.bcfg_data(bd),.fault(fault));
qkd_astk_fault_join j(.ck(ck),.rst_n(rst_n),.a(1'b0),.b(OMIT?1'b0:fault),.q(join_q));
qkd_astk_fault_join s(.ck(ck),.rst_n(rst_n),.a(join_q),.b(sink_q),.q(sink_q));
reg golden=0,gj=0,gs=0;reg[4:0] covered=0;
integer cycles=0,checks=0;
task tick;
reg nf,nj,ns;reg[4:0] causes;
begin
 ck=0;#2;
 causes={dut.s_fault,dut.n_col,dut.n_run,dut.n_stale,dut.n_early};
 nf=dut.rl?(golden||(|causes)):0;nj=rst_n?golden:0;ns=rst_n?(gj||gs):0;
 if(dut.rl)covered=covered|causes;
 ck=1;#2;cycles++;
 if(fault!==nf)$fatal(1,"DCAL_STICKY_CLEAR_MISMATCH cycle=%0d",cycles);
 if(join_q!==nj||sink_q!==ns)$fatal(1,"DCAL_FOLD_MISMATCH cycle=%0d",cycles);
 golden=nf;gj=nj;gs=ns;checks+=3;ck=0;#2;
end endtask
task reset_all;
begin
 rst_n=0;reload=0;epoch_go=0;halt=0;bt=0;br=0;#2;
 golden=0;gj=0;gs=0;
 if(fault!==0||sink_q!==0)$fatal(1,"DCAL_ASYNC_CLEAR_MISMATCH");
 tick();rst_n=1;tick();
 if(dut.rl!==0)$fatal(1,"DCAL_RELEASE_EARLY");
 tick();if(dut.rl!==1)$fatal(1,"DCAL_RELEASE_LATE");
 repeat(80)tick();
end endtask
task epoch;
begin epoch_go=1;tick();epoch_go=0;tick();end endtask
task preserve_health;
begin
 repeat(5)tick();if(!fault||!sink_q)$fatal(1,"DCAL_FAULT_NOT_OBSERVED");
 halt=1;repeat(5)tick();halt=0;reload=1;repeat(5)tick();reload=0;repeat(80)tick();
 if(!fault||!sink_q)$fatal(1,"DCAL_NONRESET_CLEAR");
end endtask
initial begin
 // Real boot-config writes generate STALE; halt/reload must retain health.
 reset_all();bt=1;ba=32;bd=32'hffffffff;repeat(3)tick();bt=0;preserve_health();
 // No boot bases: natural admission start generates EARLY.
 reset_all();epoch();repeat(85)tick();preserve_health();
 // Continuous real boot writes overlap the epoch SEG2 restore (COL), and
 // admission execution (RUN). Repeated epochs during execution cause s_fault.
 reset_all();bt=1;ba=0;bd=0;epoch();repeat(1300)tick();bt=0;epoch();repeat(100)tick();preserve_health();
 if(covered!==5'b11111)$fatal(1,"DCAL_CAUSE_COVERAGE got=%b",covered);
 reset_all();repeat(8)tick();if(fault||sink_q)$fatal(1,"DCAL_RESET_RESURRECTION");
 $display("DCAL_REAL_PREDICATES_PASS causes=%b cycles=%0d checks=%0d",covered,cycles,checks);$finish;
end
endmodule
