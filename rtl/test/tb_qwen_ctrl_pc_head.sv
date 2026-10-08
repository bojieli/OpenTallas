`timescale 1ns/1ps
module tb_qwen_ctrl_pc;
 parameter integer PC=0,NEG=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cmd_v=0;reg [31:0] cmd=0;reg [2:0] read_credit=0;
 wire cmd_credit,row_v,col_v,col_we,busy,fault;
 wire [2:0] row_op;wire [4:0] row_bank,col_bank,col_col;wire [18:0] row_row;
 ot_qwen_ctrl_pc_head #(.ENABLE(1),.PC(PC)) dut(.*);
 // Independent software-like command queue, connected to the unmodified golden
 // controller. Captures packet ingress; compares all emitted command transactions.
 reg capv=0;reg [31:0] cap=0;
 reg [31:0] mq[0:7];integer w=0,r=0,sz=0;
 wire [31:0] hd=mq[r];
 wire rd,wr,rv,cv,cwe,fb,bb;wire [2:0] ro;wire [4:0] rb,cb,cc;wire [18:0] rr;
 reg [2:0] crq=0;
 wire malformed=hd[31:30]==3 || (hd[31:30]==0 && (hd[29:19]==0 || hd[29:19]>1024));
 wire consume=sz!=0 && (malformed || (hd[31:30]==0 ? rd : hd[31:30]==2 ? wr : 1));
 wire push=capv && sz<8;
 ot_hbm_r14_stream_pc #(.ENABLE(1),.PC(PC),.REF_MODE(1),.CRED(32),
  .REF_PHASE((PC*118)/32),.WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0)) refpc(
  .clk(clk),.rst_n(rst_n),.desc_v(sz!=0 && !malformed && hd[31:30]==0),.desc_r(rd),
  .desc_row(hd[18:0]),.desc_n(hd[29:19]),.go(sz!=0 && hd[31:30]==1),.next_posted(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(1'b1),.row_op(ro),.row_bank(rb),.row_row(rr),
  .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(crq),.busy(bb),.ref_fault(fb),
  .wr_v(sz!=0 && hd[31:30]==2),.wr_bank(hd[4:0]),.wr_col(hd[9:5]),
  .wr_r(wr),.col_we(cwe),.wr_rd(1'b0),.col_aq());
 reg erow=0,ecol=0,ewe=0,ecredit=0;
 reg [2:0] eop;reg [4:0] erb,ecb,ecc;reg [18:0] er;
 integer sent=0,acked=0,reads=0,writes=0,rows=0,cycles=0,pending_reads=0,ret=0;
 task fail(input [255:0] msg);
 begin $display("FAIL ctrl_pc %s PC=%0d reads=%0d writes=%0d",msg,PC,reads,writes);$fatal(1);end endtask
 always @(posedge clk) if(rst_n) begin
  cap<=cmd;capv<=cmd_v;crq<=read_credit;
  if(push) begin mq[w]<=cap;w<=(w+1)%8;end
  if(consume) r<=(r+1)%8;
  sz<=sz+push-consume;
  erow<=rv;ecol<=cv;ewe<=cwe;eop<=ro;erb<=rb;er<=rr;ecb<=cb;ecc<=cc;ecredit<=consume;
  if(cmd_v) sent=sent+1;
  if(cmd_credit) acked=acked+1;
 end
 always @(negedge clk) if(rst_n) begin
  cycles=cycles+1;
  if(dut.core.on.write_ready_bank !== (dut.core.on.open & ~dut.core.on.stale & dut.core.on.rcdw_z & ~dut.core.on.blk)) fail("eligibility invariant");
  if(dut.count!=0 && dut.head !== dut.fifo[dut.rp]) fail("head invariant");
  if(row_v!==erow || col_v!==ecol || cmd_credit!==ecredit) fail("valid or credit");
  if(row_v) begin
   if({row_op,row_bank,row_row}!=={eop,erb,er}) fail("row command");
   rows=rows+1;
  end
  if(col_v) begin
   if({col_we,col_bank,col_col}!=={ewe,ecb,ecc ^ ((NEG && reads==17) ? 5'd1:5'd0)}) fail("column command");
   if(col_we) writes=writes+1;else begin reads=reads+1;pending_reads=pending_reads+1;end
  end
  // Return read credits after deterministic backpressure bursts.
  ret=(cycles%19==0) ? (pending_reads>7 ? 7:pending_reads):0;
  read_credit=3'(ret);pending_reads=pending_reads-ret;
 end
 task send(input [31:0] packet);
 begin
  @(negedge clk);cmd_v=0;
  while(sent-acked>=8) @(negedge clk);
  cmd=packet;cmd_v=1;
  @(negedge clk);cmd_v=0;
 end endtask
 integer x;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  send({2'b00,11'd1024,19'd7});send({2'b01,30'd0});
  wait(reads==1024);
  for(x=0;x<16;x=x+1) send({2'b10,20'd0,5'(x),5'(x%4)});
  wait(writes==16);
  send({2'b00,11'd1024,19'd8});send({2'b01,30'd0});
  wait(reads==2048);
  repeat(500) @(negedge clk);
  if(fault || fb) fail("legal traffic fault");
  // A reserved opcode must retire its credit, issue no command, and latch fault.
  send(32'hc0000000);repeat(8) @(negedge clk);
  if(!fault) fail("invalid opcode not detected");
  if(sent!=acked) fail("credits not conserved");
  $display("PASS ctrl_pc PC=%0d reads=%0d writes=%0d rows=%0d packets=%0d invalid_opcode=detected",PC,reads,writes,rows,sent);$finish;
 end
 initial begin #2000000;fail("watchdog");end
endmodule
