`timescale 1ns/1ps
// Directed boundary regression: 32 accepted group writes must retire before WB owns PC0.
// Controller responses are declared input stimuli; this complements the real-controller/SRAM quadrant bench.
module tb_hbm_svc_wb_kshare_drain;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg[3:0]gv=0,done=0,wv=0;wire[3:0]gr,cv,wr,gdone,wdone;wire[67:0]ctag;
 reg cmd=0;integer accepted=0,returned=0,wbissued=0;
 ot_hbm_svc_vm_kshare u(.sm(3'd0),.hbm_clk(clk),.hbm_rst_n(rst),.stream_clk(clk),.stream_rst_n(rst),
  .g_k_v(gv),.g_k_rdy(gr),.g_k_addr(120'd0),.g_k_len({4{4'd1}}),.g_k_tag(68'd0),
  .g_k_we(4'hf),.g_k_wdata(1024'd0),.g_k_wstrb({128{1'b1}}),.g_k_wr_done(gdone),
  .g_kr_v(),.g_kr_rdy(4'hf),.g_kr_tag(),.g_kr_beat(),.g_kr_data(),
  .c_k_v(cv),.c_k_rdy(4'hf),.c_k_addr(),.c_k_len(),.c_k_tag(ctag),.c_k_we(),.c_k_wdata(),.c_k_wstrb(),.c_k_wr_done(done),
  .c_kr_v(4'b0),.c_kr_rdy(),.c_kr_tag(68'd0),.c_kr_beat(16'd0),.c_kr_data(1024'd0),
  .vm_v(1'b0),.vm_bank(1'b0),.vm_epoch(16'd0),.vm_row(15'd0),.vm_col(4'd0),
  .wbw_v(cmd),.wbw_base(30'd0),.wbw_total(12'd1),
  .w_k_v(wv),.w_k_rdy(wr),.w_k_addr(120'd0),.w_k_wdata(1024'd0),.w_k_wr_done(wdone),
  .fill_v(),.fill_bank(),.fill_slot(),.fill_epoch(),.fill_data(),.fault());
 always @(posedge clk)if(rst)begin
  if(cv[0])begin
   if(ctag[16])begin
    if(returned!=32)$fatal(1,"PREMATURE_WB accepted=%0d returned=%0d",accepted,returned);
    wbissued=wbissued+1;
   end else accepted=accepted+1;
  end
  if(gdone[0])returned=returned+1;
 end
 integer sent;
 initial begin
  repeat(4)@(negedge clk);rst=1;repeat(8)@(negedge clk);
  sent=0;gv=1;
  while(sent<32)begin @(posedge clk);if(gr[0])sent=sent+1;@(negedge clk);end
  gv=0;repeat(6)@(negedge clk);
  if(accepted!=32)$fatal(1,"stimulus accepted=%0d",accepted);
  cmd=1;@(negedge clk);cmd=0;wv=1;
  // Two WB-side skid entries are sufficient for this single-beat stimulus.
  @(posedge clk);while(!wr[0])@(posedge clk);@(negedge clk);wv=0;
  repeat(20)@(negedge clk);
  if(wbissued!=0)$fatal(1,"WB issued before any group completion");
  done=1;repeat(32)@(negedge clk);done=0;
  repeat(12)@(negedge clk);
  if(returned!=32||wbissued!=1)$fatal(1,"drain mismatch group=%0d wb=%0d",returned,wbissued);
  done=1;@(negedge clk);done=0;repeat(3)@(negedge clk);
  $display("PASS tb_hbm_svc_wb_kshare_drain group_completed=%0d wb_issued=%0d",returned,wbissued);$finish;
 end
 initial begin #10000;$fatal(1,"drain timeout");end
endmodule
