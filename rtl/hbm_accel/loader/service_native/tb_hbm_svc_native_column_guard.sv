`timescale 1ps/1fs
module tb_hbm_svc_native_column_guard;
 reg clk=0;always #512 clk=~clk;reg rst_n=0,row_gnt=1;
 wire desc_r,row_v,row_prio,col_v,busy,ref_fault,wr_r,col_we,col_aq;
 wire [2:0] row_op;wire [4:0]row_bank,col_bank,col_col;wire [18:0]row_row;
 ot_hbm_svc_native_stream_pc #(.ENABLE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.COLUMN_CLOSE_GUARD(1)) dut(
 .clk(clk),.rst_n(rst_n),.desc_v(1'b0),.desc_r(desc_r),.desc_row(19'b0),.desc_n(11'b0),.go(1'b0),.next_posted(1'b0),
 .row_v(row_v),.row_prio(row_prio),.row_gnt(row_gnt),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_bank(col_bank),.col_col(col_col),.cred_ret(3'b0),.busy(busy),.ref_fault(ref_fault),
 .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(wr_r),.col_we(col_we),.wr_rd(1'b0),.col_aq(col_aq));
 // Directed local eligibility proof. Freeze only timing/queue prerequisites,
 // then change the actual issued row-command state and old bank-open mask.
 // The real column_open/open_nx expressions remain unforced.
 task check(input bit expected,input integer id);begin
  #1;if(dut.on.wr_bank_rdy!==expected||dut.on.rd_ok_base!==expected)
   $fatal(1,"column guard case=%0d expected=%0d queued=%0d stream=%0d",id,expected,dut.on.wr_bank_rdy,dut.on.rd_ok_base);
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  force dut.on.wq_ne=1;force dut.on.hb_oh=32'h1000;force dut.on.rd_oh=32'h1000;
  force dut.on.stale=0;force dut.on.rcd_z='1;force dut.on.rcdw_z='1;force dut.on.blk=0;
  force dut.on.running=1;force dut.on.streaming=1;force dut.on.rd_block=0;
  force dut.on.rd_bgoh=4'b0001;force dut.on.ccdl_z=4'b1111;force dut.on.cred_nz=1;
  force dut.on.c_v=1;force dut.on.c_op=0;force dut.on.c_bank=12;force dut.on.c_oh=32'h1000;force dut.on.open=32'h1000;
  row_gnt=0;check(0,9);row_gnt=1;check(0,1); // PRE same bank must block queued and streaming columns.
  force dut.on.c_bank=13;force dut.on.c_oh=32'h2000;check(1,2);
  force dut.on.c_op=1;force dut.on.c_bank=12;force dut.on.c_oh=32'h1000;force dut.on.open=0;check(0,3);
  force dut.on.open=32'h1000;force dut.on.c_op=6;check(0,4);
  force dut.on.c_bank=13;force dut.on.c_oh=32'h2000;check(1,5);
  force dut.on.c_op=4;check(0,6); // all-bank refresh closes eligibility.
  force dut.on.c_op=5;check(0,7); // PREALL.
  force dut.on.c_v=0;check(1,8);
  $display("NATIVE_COLUMN_GUARD PASS directed_cases=9 queued_and_streaming_paths=2");$finish;
 end
endmodule
