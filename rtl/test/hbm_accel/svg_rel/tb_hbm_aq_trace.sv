`timescale 1ps/1fs
// Replays the EXACT accepted AQ entries captured from a production four-PC
// SM replay, including reset levels and idle cycles. No behavioural scheduler.
module tb_hbm_aq_trace;
 reg clk=0;always #512 clk=~clk;
 reg rst_n=0,wv=0;reg[29:0]token=0;
 reg[31:0]trace_mem[0:65535];integer n,i,cycles=0,pushes=0,columns=0;string tf;
 wire wr_r,rv,cv,cwe,caq,fault;wire[2:0]op;wire[4:0]rb,cb,cc;wire[18:0]row;
 ot_hbm_r14_aq_pc_safe #(.WQ(64)) dut(.clk(clk),.rst_n(rst_n),.reset_regions({64{rst_n}}),.slot_parity(1'b1),.refresh_reload(8'd121),
  .row_v(rv),.row_op(op),.row_bank(rb),.row_row(row),.col_v(cv),.col_bank(cb),.col_col(cc),.ref_fault(fault),
  .wr_v(wv),.wr_bank(token[29:25]),.wr_col(token[24:20]),.wr_row(token[19:1]),.wr_rd(token[0]),.wr_r(wr_r),
  .col_we(cwe),.col_aq(caq),.dbg_held());
 wire[31:0]dv;wire[8191:0]dd;
 tb_svg_rel_dram_sparse dram(.clk(clk),.rst_n(rst_n),.row_v({30'b0,rv,1'b0}),.row_op({90'b0,op,3'b0}),
  .row_bank({150'b0,rb,5'b0}),.row_row({570'b0,row,19'b0}),.col_v({30'b0,cv,1'b0}),.col_we({30'b0,cwe,1'b0}),
  .col_bank({150'b0,cb,5'b0}),.col_col({150'b0,cc,5'b0}),.col_data(8192'b0),.col_strb(1024'b0),.dram_rvalid(dv),.dram_rdata(dd));
 always @(posedge clk)begin
  if(rst_n)begin
   cycles=cycles+1;
   if(wv)begin if(!wr_r)$fatal(1,"AQ_TRACE_BACKPRESSURE cycle%0d",cycles);pushes=pushes+1;end
   if(cv)columns=columns+1;
  end
  #1;if(fault)$fatal(1,"AQ_TRACE_REF_FAULT cycle%0d ref_c%0d bank%0d pending%0d",cycles,dut.ref_c,dut.rb,dut.ref_pend);
 end
 initial begin
  if(!$value$plusargs("TRACE=%s",tf)||!$value$plusargs("N=%d",n)||n>65536)$fatal(1,"trace args");
  $readmemh(tf,trace_mem,0,n-1);
  for(i=0;i<n;i=i+1)begin @(negedge clk);rst_n=trace_mem[i][31];wv=trace_mem[i][30];token=trace_mem[i][29:0];end
  @(negedge clk);wv=0;rst_n=1;
  repeat(400)@(negedge clk);
  if(pushes!=columns)$fatal(1,"AQ_TRACE_CONSERVATION pushes%0d columns%0d",pushes,columns);
  $display("AQ_TRACE_PASS cycles%0d pushes%0d columns%0d",cycles,pushes,columns);$finish;
 end
endmodule
