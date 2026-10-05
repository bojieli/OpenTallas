`timescale 1ns/1ps
// Disabled successor must not disturb the original owner, even with a live
// shared bus carrying another client's responses and posted commands.
module tb_hbm_accel_su_fused_mreq_off;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 wire ready,busy,done,fault,rv,rr,we,rd_debt,wr_debt;
 ot_hbm_accel_su_fused_mreq #(.N(32),.D(32)) dut (
  .clk(clk),.rst_n(rst_n),.cmd_valid(1'b1),.lease_grant(1'b1),.prior_route_drained(1'b1),
  .cmd_ready(ready),.busy(busy),.done(done),.fault(fault),.job_id(32'd17),
  .vm_byte_base(32'd0),.cr_byte_base(32'd0),.xbase(24'd0),.ybase(24'd0),.gain_base(24'd0),
  .n_f(32'd0),.eps(32'd0),.completion_id(),.req_v(rv),.req_rdy(1'b1),.req_we(we),
  .req_addr(),.req_wstrb(),.req_wdata(),.req_tag(),.rsp_v(1'b1),.rsp_rdy(rr),
  .rsp_tag(16'hffff),.rsp_we(1'b1),.rsp_data(256'd0),.read_sectors(),.write_sectors(),
  .publication_sectors(),.read_debt(rd_debt),.write_debt(wr_debt));
 initial begin
  repeat(2) @(negedge clk);rst_n=1;
  repeat(8) begin
   @(negedge clk);
   if(ready||busy||done||fault||rv||rr||rd_debt||wr_debt) $fatal(1,"disabled successor changed original bus ownership");
  end
  $display("DEFAULT_OFF_PASS live_foreign_bus_ignored cycles=8");$finish;
 end
endmodule
