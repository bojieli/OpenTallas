`timescale 1ns/1ps
module tb_reset_publication_v3;
 parameter integer MUT=0;
 reg ck=0,rst_n=1;always #1 ck=~ck;
 wire [0:0] old_rp;wire old_r0,old_rc,old_rsc;
 wire [23:0] rp;wire [11:0] rc;wire [8:0] rsc;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) a(.clk(ck),.rst_n_in(rst_n),.rst_n(old_rp));
 ot_nhb_rleaf_h b(.clk(ck),.arst_n(old_rp[0]),.d(1'b1),.q(old_r0));
 ot_nhb_rleaf_h c(.clk(ck),.arst_n(old_rp[0]),.d(old_r0),.q(old_rc));
 ot_nhb_rleaf_h d(.clk(ck),.arst_n(old_rp[0]),.d(old_r0),.q(old_rsc));
 ot_ectl_h15_reset_publish32 #(.MUT(MUT)) candidate(.clk(ck),.rst_n(rst_n),.rp(rp),.rc(rc),.rsc(rsc));
 integer epoch,k,checks=0;
 task automatic check;
  if(rp!=={24{old_rp[0]}} || rc!=={12{old_rc}} || rsc!=={9{old_rsc}})
   $fatal(1,"RESET_PUBLICATION_STAGE_MISMATCH epoch%0d step%0d",epoch,k);
  checks=checks+1;
 endtask
 initial begin
  // Establish asserted reset across clock edges before observations of
  // arbitrary power-up state. Subsequent assertions compare asynchronously.
  epoch=0;k=0;#0.25;rst_n=0;repeat(2)@(negedge ck);#0.1;check();
  for(epoch=0;epoch<8;epoch=epoch+1)begin
   repeat(3)@(negedge ck);rst_n=1;
   for(k=1;k<=8;k=k+1)begin
    @(posedge ck);#0.1;check();
    if(rp!=={24{(k>=3)}} || rc!=={12{(k>=5)}} || rsc!=={9{(k>=5)}})$fatal(1,"RESET_PUBLICATION_ABSOLUTE_AGE");
    @(negedge ck);
   end
   #0.25;rst_n=0;#0.1;check();
   if(rp!==0 || rc!==0 || rsc!==0)$fatal(1,"RESET_PUBLICATION_ASYNC_ASSERT");
  end
  $display("RESET_PUBLICATION_PASS checks=%0d epochs=%0d RP3_R0_4_RC_RSC5 async_assert",checks,epoch);$finish;
 end
endmodule
