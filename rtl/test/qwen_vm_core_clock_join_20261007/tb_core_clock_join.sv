`timescale 1ns/1ps
module tb_core_clock_join;
parameter PINREG=0,LEASE=1;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg supply=0,issue_intent=0,we=0;reg[31:0]wd=32'h40914576;
wire native_clk,me_clk,tick,lease,drained,fault,wanted,effective,pending,take;
wire[31:0]accepts;wire[63:0]epoch,reads,writes,acks;integer native_edges=0,me_edges=0;
wire[31:0]rq;
ot_hdc_cg parent_gate(.clk(clk),.en(!rst_n||tick),.gclk(native_clk));
source_core_clock #(.DEC_LA_PINREG(PINREG),.VM_OWNED_LEASE(LEASE))core(.clk(native_clk),.rst_n_i(rst_n),.me_mem_ok(supply),.vm_me_lease(lease),.issue_intent(issue_intent),.vm_me_wanted(wanted),.effective(effective),.engine_clk(me_clk),.pending(pending),.take(take),.accepts(accepts));
ot_qwen_finite_vm_adapter_direct_readback #(.ENABLE(1),.DIRECT_READBACK(1),.NR(1),.NW(1),.VX0(0),.NVX(1))dut(.clk(clk),.rst_n(rst_n),.source_me_wanted(wanted),.head_source_producer_go(1'b0),.read_en(1'b0),.read_addr(24'd0),.read_q(rq),.write_en(we),.write_addr(24'd4096),.write_data(wd),.native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),.native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),.held_edges(),.head_fill_reads(),.head_hit_edges());
always @(posedge native_clk)if(rst_n)native_edges<=native_edges+1;
always @(posedge me_clk)if(rst_n)begin
 if(!lease)$fatal(1,"UNPAID_SOURCE_ME_CLOCK");
 me_edges<=me_edges+1;
end
always @(posedge clk)if(rst_n)begin
 if(fault)$fatal(1,"provider fault");
 if(|dut.wr_ACK && $isunknown(dut.g_bound.u_bank.decoded))$fatal(1,"unknown postverify payload");
end
integer n0,m0,a0;reg[63:0]e0;
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 repeat(3)@(negedge clk);
 if(PINREG==0)begin
  supply=1;issue_intent=1;
  wait(pending);@(negedge clk);issue_intent=0;supply=0;
  if(accepts!=0)$fatal(1,"ME accepted before directed hold setup");
 end
 we=1;e0=epoch;n0=native_edges;m0=me_edges;a0=accepts;
 @(posedge clk);#1;
 if(dut.state==0 || dut.me_frame!==0)$fatal(1,"nonME owned frame not captured");
 @(negedge clk);supply=1;
 // Supply rises while the physical provider services the captured nonME frame.
 wait(dut.state==7);
 if(dut.me_frame!==0 || lease!==0)$fatal(1,"captured intent0 obtained ME lease");
 if(native_edges!=n0 || me_edges!=m0 || accepts!=a0)$fatal(1,"source advanced during physical service");
 @(posedge clk);#1;
 if(epoch!=e0+1 || native_edges!=n0+1 || me_edges!=m0 || accepts!=a0 || take)$fatal(1,"UNPAID_SOURCE_ME_ACCEPTANCE");
 if(PINREG==0 && !pending)$fatal(1,"pending go was consumed without lease");
 if(acks!=1)$fatal(1,"native admission before real checked ACK");
 $display("PASS captured_intent0 live_supply1 native_only_admission PINREG=%0d checked_ACK=%0d",PINREG,acks);
 @(negedge clk);we=0;
 if(PINREG!=0)issue_intent=1;
 wait(accepts==a0+1);@(negedge clk);issue_intent=0;
 if(!LEASE)$fatal(1,"disabled mutation did not expose unpaid edge");
 $display("PASS actual_source_ICG MEIF_go_take lease_qualified_resume PINREG=%0d accepted=%0d",PINREG,accepts);
 // A captured ME frame retains its owned supply contract.
 we=1;wd=32'hbe916038;e0=epoch;n0=native_edges;m0=me_edges;
 @(posedge clk);#1;if(dut.me_frame!==1)$fatal(1,"ME frame not captured");
 @(negedge clk);supply=0;
 wait(dut.state==7);
 if(acks!=2)$fatal(1,"ME frame did not receive actual checked ACK");
 if(PINREG==0)begin
  repeat(3)begin @(posedge clk);#1;if(tick || epoch!=e0 || native_edges!=n0 || me_edges!=m0)$fatal(1,"ME source advanced without original supply");end
  @(negedge clk);supply=1;
 end else if(!wanted)$fatal(1,"PINREG supply changed while native clock held");
 @(posedge clk);#1;
 if(epoch!=e0+1 || native_edges!=n0+1 || me_edges!=m0+1)$fatal(1,"ME frame did not retire on qualified source edge");
 $display("PASS captured_intent1 supply_hold_and_PINREG_contract PINREG=%0d checked_ACK=%0d",PINREG,acks);
 $finish;
end
endmodule
