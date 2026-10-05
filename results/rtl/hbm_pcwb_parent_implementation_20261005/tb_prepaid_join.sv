`timescale 1ps/1fs
// Minimum new join: actual CMD1 PC -> finite C/A grants and prepaid PHY queue.
// PHY accept and visibility are independent external events, not WR issue ACK.
module tb_prepaid_join;
 reg clk=0,rst=0,ctx=0;always #512 clk=~clk;
 reg wr_v=0,phy_r=0,vis_v=0,consume=0;
 reg [4:0] wr_col=0;reg [255:0] wr_data=0;
 reg [198:0] vis_receipt=0;
 wire wr_r,wq_v,wq_r,col_v,col_we,phy_v,phy_we,vis_r,ret_v,fault,ca_fault,pc_fault;
 wire [4:0] cb,cc,pb,pc;wire [18:0] cr,pr;
 wire [255:0] cd,pd;wire [198:0] receipt,returned;
 wire [6:0] queued;wire [3:0] inflight,held;wire drained;
 wire rv,rg;wire [2:0] ro;wire [4:0] rb;wire [18:0] rr;
 wire [31:0] grants;wire [15:0] ca_valid;
 integer phy_count=0,issue_count=0;reg [198:0] saved[0:3];
 ot_hbm_pcwb_prepaid_column #(.ENABLE(1),.PC(0)) a(
  .service_clk(clk),.por_n(rst),.context_valid(ctx),.operation(64'd123),.phase(32'd45),.generation(32'd67),
  .wr_v(wr_v),.wr_r(wr_r),.wr_bank(5'd0),.wr_row(19'd99),.wr_col(wr_col),.wr_data(wr_data),
  .wq_v(wq_v),.wq_r(wq_r),.col_v(col_v),.col_we(col_we),.col_bank(cb),.col_row(cr),.col_col(cc),.col_data(cd),
  .phy_col_v(phy_v),.phy_col_r(phy_r),.phy_we(phy_we),.phy_bank(pb),.phy_row(pr),.phy_col(pc),.phy_data(pd),.phy_receipt(receipt),
  .visible_v(vis_v),.visible_r(vis_r),.visible_receipt(vis_receipt),.wr_visible_v(ret_v),.wr_visible_r(consume),.wr_visible_receipt(returned),
  .queued(queued),.inflight(inflight),.visible_not_returned(held),.all_writes_drained(drained),.fault(fault));
 ot_hbm_accel_stream_pc_wb_command_match #(.ENABLE(1),.WB_EN(1),.WA_LATE(1),.DIGEST_CUT(1),.CMD_MATCH_CUT(1),.PC(0),.REF_MODE(1),.CRED(64),.WQ(8)) c(
  .clk(clk),.rst_n(rst),.desc_v(1'b0),.desc_r(),.desc_row(19'b0),.desc_n(11'b0),.go(1'b0),.next_posted(1'b0),.notice(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(rg),.row_op(ro),.row_bank(rb),.row_row(rr),
  .col_v(col_v),.col_bank(cb),.col_col(cc),.cred_ret(3'b0),.busy(),.ref_fault(pc_fault),
  .wq_v(wq_v),.wq_bank(5'd0),.wq_row(19'd99),.wq_col(wr_col),.wq_data(wr_data),.wq_r(wq_r),
  .col_we(col_we),.col_wdata(cd),.col_row(cr),.wr_ack(),.wq_empty());
 ot_hbm_pcwb_ca_slots #(.ENABLE(1)) ca(
  .service_clk(clk),.por_n(rst),.run_enable(1'b1),.row_req({31'b0,rv}),.row_op({93'b0,ro}),
  .row_bank({155'b0,rb}),.row_row({589'b0,rr}),.ca_ready(16'hffff),.row_grant(grants),
  .ca_valid(ca_valid),.ca_pc_lsb(),.ca_op(),.ca_bank(),.ca_row(),.fault(ca_fault));
 assign rg=grants[0];
 always @(posedge clk)if(rst)begin
  if(col_v&&col_we)issue_count=issue_count+1;
  if(phy_v&&phy_r)begin
   if(!phy_we||pr!=99||pd!=256'(100+pc))$fatal(1,"actual PHY payload mismatch");
   saved[phy_count]=receipt;phy_count=phy_count+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task send_visible(input integer n);begin
  @(negedge clk);vis_receipt=saved[n];vis_v=1;#1;
  if(!vis_r)$fatal(1,"matching PHY-accepted visibility refused");
  tick();@(negedge clk);vis_v=0;
 end endtask
 initial begin
  #1;rst=0;repeat(2)tick();@(negedge clk);rst=1;
  // Missing owner refuses ingress. No constant positive frame supplied by parent.
  wr_v=1;#1;if(wr_r||wq_v)$fatal(1,"unowned ingress admitted");
  tick();@(negedge clk);ctx=1;wr_v=0;
  for(integer n=0;n<4;n=n+1)begin
   @(negedge clk);wr_v=1;wr_col=5'(n);wr_data=256'(100+n);#1;
   while(!wr_r)begin tick();@(negedge clk);end
   tick();@(negedge clk);wr_v=0;
  end
  // Actual controller issues while external PHY stalls; all four seats remain.
  for(integer n=0;n<900&&queued!=4;n=n+1)tick();
  if(queued!=4||issue_count!=4||drained||ret_v||fault||pc_fault||ca_fault)$fatal(1,"WR issue falsely visible or join failed");
  @(negedge clk);phy_r=1;
  while(phy_count!=4)tick();@(negedge clk);phy_r=0;
  if(inflight!=4||drained)$fatal(1,"PHY acceptance freed a write lease");
  // Out-of-order visibility, held until real writer consumption.
  send_visible(2);if(!ret_v||returned!=saved[2]||held!=1)$fatal(1,"visibility not retained");
  repeat(3)tick();if(held!=1||drained)$fatal(1,"held receipt prematurely freed");
  @(negedge clk);consume=1;tick();@(negedge clk);consume=0;
  send_visible(0);@(negedge clk);consume=1;tick();@(negedge clk);consume=0;
  send_visible(3);@(negedge clk);consume=1;tick();@(negedge clk);consume=0;
  send_visible(1);@(negedge clk);consume=1;tick();@(negedge clk);consume=0;
  if(!drained||fault)$fatal(1,"positive receipts did not drain exactly");
  // Replay of a consumed full identity cannot produce another writer ACK.
  vis_receipt=saved[0];vis_v=1;#1;if(vis_r||ret_v)$fatal(1,"duplicate accepted");
  tick();if(!fault)$fatal(1,"duplicate did not latch refusal");
  $display("PASS_PREPAID_ACTUAL_PC_JOIN four WRs; issue/PHY/visibility/consume distinct; duplicate refused");$finish;
 end
endmodule
