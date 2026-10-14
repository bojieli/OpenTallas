`timescale 1ns/1ps
module tb_s81_htransfer_slots #(parameter integer MUT=0);
 reg ck=0,rst=0;always #0.4166 ck=~ck;
 reg begin_v=0,slot=0,wr=0,read_v=0;reg[13:0] wa=0,ra=0;wire re,go,fault;wire[13:0] out_a;wire[3:0] code;
 ot_s81_htransfer #(.DEPTH(32),.S_WR(1),.MUT(MUT?2:0)) dut(.clk(ck),.rst_n(rst),.store_begin(begin_v),.store_slot(slot),
 .wr_v(wr),.wr_a(wa),.wr_mask(16'hffff),.hop_go(go),.hop_re(read_v),.hop_ra(ra),.vm_re(re),.vm_ra(out_a),
 .fault(fault),.fault_code(code),.committed_rows());
 integer errors=0,seen=0;
 always @(posedge ck)if(rst&&re)begin if(out_a!=2088)errors=errors+1;seen=seen+1;end
 task automatic start_store(input bit s);
  @(negedge ck);slot=s;begin_v=1;@(negedge ck);begin_v=0;
 endtask
 initial begin
  repeat(5)@(negedge ck);rst=1;start_store(0);
  @(negedge ck);read_v=1;ra=2088;@(negedge ck);read_v=0;
  repeat(3)@(negedge ck);if(dut.n!=1||dut.queued_h[0]!=1)errors=errors+1;
  start_store(1);repeat(3)@(negedge ck);
  if(fault||dut.n!=1||dut.queued_h[0]!=1||dut.queued_h[1]!=0)errors=errors+1;
  wa=2088;wr=1;@(negedge ck);wr=0;repeat(4)@(negedge ck);
  if(fault||seen!=1||dut.n!=0||dut.queued_h[0]!=0)errors=errors+1;
  // Reusing slot0 with an old queued read remains illegal.
  read_v=1;ra=2088+1;@(negedge ck);read_v=0;repeat(3)@(negedge ck);
  start_store(0);repeat(3)@(negedge ck);
  if(!fault||code!=4)errors=errors+1;
  $display("TB_S81_HTRANSFER_SLOTS mut=%0d other_slot_allowed=%0d old_reads=%0d reuse_fault=%0d code=%0d errors=%0d %s",MUT,seen==1,seen,fault,code,errors,errors==0?"PASS":"FAIL");$finish;
 end
endmodule
