`timescale 1ps/1fs
module tb_hbm_svc_native_committed_candidate;
 reg clk=0;always #512 clk=~clk;reg rst_n=0,row_gnt=1;
 wire desc_r,row_v,row_prio,col_v,busy,ref_fault,wr_r,col_we,col_aq;
 wire [2:0] row_op;wire [4:0]row_bank,col_bank,col_col;wire [18:0]row_row;
 ot_hbm_svc_native_stream_pc_candidate #(.ENABLE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.COLUMN_CLOSE_GUARD(1),.AQ_ROW_LEASE(1),.USE_COMMITTED_OPEN(1)) dut(
 .clk(clk),.rst_n(rst_n),.desc_v(1'b0),.desc_r(desc_r),.desc_row(19'b0),.desc_n(11'b0),.go(1'b0),.next_posted(1'b0),
 .row_v(row_v),.row_prio(row_prio),.row_gnt(row_gnt),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_bank(col_bank),.col_col(col_col),.cred_ret(3'b0),.busy(busy),.ref_fault(ref_fault),
 .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(wr_r),.col_we(col_we),.wr_rd(1'b0),.col_aq(col_aq));
 initial begin
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  force dut.on.wq_in=32'b1;force dut.on.wq_bq=160'd12;
  force dut.on.open=0;force dut.on.blk=0;force dut.on.aok_z='1;force dut.on.rrdl_z=4'b1111;
  force dut.on.c_v=1;force dut.on.c_op=1;force dut.on.c_oh=32'h1000;force dut.on.c_bank=12;
  #1;if(dut.on.wq_act[0]!==0)$fatal(1,"committed ACT reselected same bank");
  if(dut.on.column_open[12]!==0)$fatal(1,"sameedge ACT bypassed oldopen column admission");
  force dut.on.c_oh=32'h2000;force dut.on.c_bank=13;
  #1;if(dut.on.wq_act[0]!==1)$fatal(1,"otherbank ACT wrongly excluded candidate");
  force dut.on.open=32'h1000;force dut.on.c_op=0;force dut.on.c_oh=32'h1000;force dut.on.c_bank=12;
  force dut.on.wcand_q=1;force dut.on.wab=12;force dut.on.wab_oh=32'h1000;
  #1;if(dut.on.wq_act[0]!==1||dut.on.wact_ok!==0)$fatal(1,"PRE candidate ignored oldopen launch guard");
  force dut.on.open=0;force dut.on.aok_z=0;
  #1;if(dut.on.wact_ok!==0)$fatal(1,"PRE candidate bypassed aok/tRP");
  $display("NATIVE_COMMITTED_CANDIDATE PASS ACT_exclusion otherbank_candidate PRE_oldopen_guard aok_tRP_guard no_column_bypass");$finish;
 end
endmodule
