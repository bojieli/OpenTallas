`timescale 1ps/1fs
module tb_qfd_typed_static_issue;
 parameter integer MUT=0;
 reg clk=0;always #512 clk=~clk;
 reg rst_n=0,q_v=0,q_we=0,q_sidecar=0,q_emb=0,q_fence=0;
 reg[18:0]q_row=0;reg[4:0]q_bank=0,q_col=0;
 reg[15:0]q_tag=0;reg[16:0]q_sec=0;reg[7:0]q_lrow=0;reg[255:0]q_data=0;
 wire q_rdy,s_v,s_we;wire[18:0]s_row;wire[4:0]s_bank,s_col;
 wire ct_col_v,ct_col_sr,ct_col_we,ct_s_cr,ct_row_v,ct_fault,ct_busy,unused_cmd_credit;
 wire[4:0]ct_col_bank,ct_col_col,ct_row_bank;wire[2:0]ct_row_op;wire[18:0]ct_row_row;
 reg phy_ready=1,provider_drained=1;
 wire issue_v,issue_we,issue_sidecar,issue_emb,issue_fence,logical_data_issue,drained,fault;
 wire[18:0]issue_row;wire[4:0]issue_bank,issue_col;wire[15:0]issue_tag;
 wire[16:0]issue_sec;wire[7:0]issue_lrow;wire[255:0]issue_data;
 ot_qwen_ctrl_pc_emb #(.ENABLE(1),.PC(17),.SQD(4)) controller(.clk(clk),.rst_n(rst_n),
 .cmd_v(1'b0),.cmd(32'd0),.read_credit(3'd0),.cmd_credit(unused_cmd_credit),
 .row_v(ct_row_v),.row_op(ct_row_op),.row_bank(ct_row_bank),.row_row(ct_row_row),
 .col_v(ct_col_v),.col_bank(ct_col_bank),.col_col(ct_col_col),.col_we(ct_col_we),
 .busy(ct_busy),.fault(ct_fault),.s_v(s_v),.s_we(s_we),.s_bank(s_bank),.s_col(s_col),.s_row(s_row),
 .s_cr(ct_s_cr),.col_sr(ct_col_sr));
 ot_qfd_typed_static_issue #(.ENABLE(1),.TYPED_ONLY(1),.MUT_CLASS(MUT)) dut(.*);
 `include "ot_qwen_kv_map_m.svh"
 reg[329:0]expected[0:255];integer accepted=0,seen=0,logical_count=0,cycles=0;
 reg monitor=1,had_first=0;integer at_first=0,i,j,basej;reg[4:0]db,dc;reg[18:0]dr;
 wire[329:0]output_packet={issue_we,issue_sidecar,issue_emb,issue_fence,issue_row,issue_bank,issue_col,issue_tag,issue_sec,issue_lrow,issue_data};
 always @(posedge clk)if(rst_n&&monitor)begin
  cycles=cycles+1;
  if(q_v&&q_rdy)begin expected[accepted]={q_we,q_sidecar,q_emb,q_fence,q_row,q_bank,q_col,q_tag,q_sec,q_lrow,q_data};accepted=accepted+1;end
  if(issue_v)begin
   if(!had_first)begin had_first=1;at_first=accepted;end
   if(seen>=accepted || output_packet!==expected[seen])$fatal(1,"typed actualissue metadata/class mismatch%0d",seen);
   if(logical_data_issue!==( !issue_we&&!issue_sidecar&&!issue_fence))$fatal(1,"logicalwindow class contamination");
   if(logical_data_issue)logical_count=logical_count+1;
   seen=seen+1;
  end
  if(fault||ct_fault)$fatal(1,"unexpected typed native controller fault");
 end
 task reset;begin
  @(negedge clk);rst_n=0;q_v=0;monitor=0;phy_ready=1;
  repeat(5)@(negedge clk);rst_n=1;accepted=0;seen=0;had_first=0;logical_count=0;cycles=0;monitor=1;
 end endtask
 initial begin
  reset;
  for(i=0;i<128;i=i+1)begin
   @(negedge clk);
   if(i%4==0)begin db=5'((i/4)%32);dc=5'(i*3);dr=19'((i/32)%36);basej={db[4:2],dc,db[1:0]};end
   q_v=1;q_we=0;q_sidecar=(i%4==1)||(i%4==3);q_emb=0;q_fence=(i%4>=2);
   q_row=q_sidecar?dr+64:dr;q_bank=q_sidecar?{db[4:2]^3'd4,2'b00}:db;
   q_col=q_sidecar?5'((basej>>3)&15):dc;q_lrow=8'(dr);q_sec=m_p2l(17,basej);
   q_tag=16'(i+1);q_data={8{32'(i*7919+31)}};
   // Actual static queue is finite; held request cannot spend another seat.
   while(!q_rdy)@(negedge clk);
   @(posedge clk);#1;@(negedge clk);q_v=0;
  end
  // Finite128-command bound covers production refresh/ACT/PRE timings plus
  // static-starvation priority, not a guessed wall-time deadline.
  j=0;while((seen!=128 || !drained) && j<128*(342+28+16+19+8+16)*4)begin @(negedge clk);j=j+1;end
  if(seen!=128 || accepted!=128 || !drained || logical_count!=32 || at_first!=4)
   $fatal(1,"native typed incomplete seen%0d logical%0d initialseats%0d",seen,logical_count,at_first);
  $display("PASS actualSROW128typed DATA/SIDECAR/fence withrealACTrow32banks finite4credits logicalDATA32 cycles%0d HCLK1024ps",cycles);
  reset;monitor=0;q_v=1;q_we=0;q_emb=0;q_sidecar=0;q_fence=0;q_row=0;q_bank=0;q_col=0;
  while(!q_rdy)@(negedge clk);@(posedge clk);#1;@(negedge clk);q_v=0;
  while(!(ct_col_v&&ct_col_sr))@(negedge clk);
  phy_ready=0;@(posedge clk);#1;
  if(!fault||issue_v)$fatal(1,"unreservedPHYissue not failclosed");
  $display("PASS realPHYcapacity violation suppressespublication");$finish;
 end
endmodule
