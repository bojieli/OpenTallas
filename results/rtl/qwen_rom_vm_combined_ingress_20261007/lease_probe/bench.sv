`timescale 1ns/1ps
module tb_lease;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,wanted=0;reg[2255:0]zero=0;
wire tick,lease,fault,drained;wire[63:0]epoch,reads,writes,acks;
wire[2256*32-1:0]rq;
ot_qwen_rom_vm_ingress_adapter #(.ENABLE(1),.ROM_INGRESS(1),.DIRECT_READBACK(1))dut(
.clk(clk),.rst_n(rst_n),.source_me_wanted(wanted),.head_source_producer_go(1'b0),
.raw_read_en(2256'd0),.raw_read_zero(zero),.read_addr(54144'd0),.read_q(rq),
.raw_write_en(865'd0),.write_addr(20760'd0),.write_data(27680'd0),
.native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),.native_epoch(epoch),
.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),.held_edges(),.head_fill_reads(),.head_hit_edges());
integer edges=0;
always @(posedge clk)if(rst_n)begin
 edges=edges+1;
 if(fault)$fatal(1,"unexpected probe fault");
 if(tick)begin
  if(!wanted || dut.me_frame || lease || reads || writes || acks)$fatal(1,"captured0/live1 lease contract changed");
  $display("PASS captured_me0 live_original_me1 native_tick1 native_me_lease0 edges=%0d",edges);$finish;
 end
 if(edges>4+2256+865+2)$fatal(1,"finite zero-frame state bound");
end
initial begin
 repeat(3)@(negedge clk);zero[0]=1;rst_n=1;
 wait(dut.state==1);@(negedge clk);wanted=1;
end
endmodule
