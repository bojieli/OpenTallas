`timescale 1ps/1fs
module tb_hbm_svc_native_row_lease;
 reg clk=0;always #512 clk=~clk;reg rst_n=0,row_gnt=1;
 wire desc_r,row_v,row_prio,col_v,busy,ref_fault,wr_r,col_we,col_aq;
 wire [2:0] row_op;wire [4:0]row_bank,col_bank,col_col;wire [18:0]row_row;
 ot_hbm_svc_native_stream_pc_lease #(.ENABLE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.COLUMN_CLOSE_GUARD(1),.AQ_ROW_LEASE(1)) dut(
 .clk(clk),.rst_n(rst_n),.desc_v(1'b0),.desc_r(desc_r),.desc_row(19'b0),.desc_n(11'b0),.go(1'b0),.next_posted(1'b0),
 .row_v(row_v),.row_prio(row_prio),.row_gnt(row_gnt),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_bank(col_bank),.col_col(col_col),.cred_ret(3'b0),.busy(busy),.ref_fault(ref_fault),
 .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(wr_r),.col_we(col_we),.wr_rd(1'b0),.col_aq(col_aq));
 task check(input bit expect_pre,input bit expect_forced,input integer id);begin
  #1;if(dut.on.pre_cand[12]!==expect_pre||dut.on.forced_pre!==expect_forced)
   $fatal(1,"row lease case=%0d pre=%0d forced=%0d expected=%0d/%0d",id,dut.on.pre_cand[12],dut.on.forced_pre,expect_pre,expect_forced);
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  force dut.on.open=32'h1000;force dut.on.wopen=32'h1000;force dut.on.sneed=0;
  force dut.on.done=0;force dut.on.stale=0;force dut.on.blk=0;force dut.on.ras_z='1;force dut.on.rtp_z='1;
  force dut.on.hold=0;force dut.on.hold_n=0;force dut.on.ref_pend=0;
  check(0,0,1);
  force dut.on.stale=32'h1000;check(1,0,2);
  force dut.on.stale=0;force dut.on.done=32'h1000;check(1,0,3);
  force dut.on.done=0;force dut.on.blk=32'h1000;force dut.on.ref_pend=1;check(0,1,4);
  force dut.on.ref_c=1;force dut.on.rb=12;#1;
  if(!dut.on.r_v||dut.on.r_op!==6||dut.on.r_bank!==12)$fatal(1,"row lease changed due REFpb command");
  $display("NATIVE_ROW_LEASE PASS ordinary_PRE_suppressed stale_done_PRE_preserved forced_PRE_preserved due_REFpb_preserved");$finish;
 end
endmodule
