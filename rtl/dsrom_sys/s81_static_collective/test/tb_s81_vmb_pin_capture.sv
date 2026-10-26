`timescale 1ns/1ps
module tb_s81_vmb_pin_capture;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,read_slot=0,hc_write_slot=0,reduced_valid=0;
 reg [13:0]read_row=42;
 wire[14:0]t_crq;wire[2203:0]t_vm;wire fault,pack_bad_out;
 s81_static_vm_boundary #(.PINCAP(1),.MUT(MUT)) u (
  .clk(clk),.rst_n(rst_n),.read_slot(read_slot),.read_row(read_row),.t_crq(t_crq),.t_vm(t_vm),
  .commit_gather(1'b0),.hc_reduce_slot(1'b0),.gather_we(4'b0),.gather_rows({4{15'd42}}),.gather_data(2048'b0),.gather_tag(32'b0),
  .hc_write_slot(hc_write_slot),.reduced_valid(reduced_valid),.reduced_error(1'b0),.reduced_last(1'b1),
  .reduced_seq(16'd9),.hc_expect_seq(16'd9),.hc_expect_last(1'b1),.reduced_data(512'hdeadbeef),.reduced_tag(32'h12),
  .raw_sources(1102'b0),.phy_rx_fault(8'b0),.phy_rx_valid(8'b0),.phy_rx_live(8'b0),.issue_slot(1'b0),
  .raw_capture(1'b0),.raw_capture_payload_slot(1'b0),.raw_capture_meta_slot(1'b0),.raw_tx_count(3'b0),.host_rx(516'b0),
  .pack_bad_out(pack_bad_out),.fault(fault));
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  // Startup release is three fixed edges; row metadata traverses 18 actual registers.
  repeat(24)@(negedge clk);
  read_slot=1;hc_write_slot=1;reduced_valid=1;
  @(negedge clk);
  if(t_crq!=={14'd42,1'b1}||t_vm[0]!==1'b0)$fatal(1,"VMB read or first write edge mismatch");
  read_slot=0;hc_write_slot=0;reduced_valid=0;
  @(negedge clk);
  if(t_crq!=={14'd42,1'b0}||t_vm!=={1653'd0,8'h12,512'hdeadbeef,16'hffff,14'd42,1'b1})$fatal(1,"VMB payload or second write edge mismatch");
  if(fault||pack_bad_out)$fatal(1,"VMB unexpected fault");
  @(negedge clk);if(t_vm[0]!==0)$fatal(1,"VMB duplicate write");
  $display("VMB_PIN_CAPTURE PASS read1 write2 row42 payload512");$finish;
 end
endmodule
