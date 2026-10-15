`timescale 1ns/1ps
module tb_qfd_vm_producer_disabled_seq40;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,v=0; wire write_allowed,acquire_ready,read_v,q_v,release_ready,flush_ack;
 ot_qfd_vm_producer_lease_seq40 dut(.clk(clk),.rst_n(rst_n),.acquire_v(v),.acquire_ready(acquire_ready),
 .held_ib(379'b0),.held_mode(1'b0),.held_context(16'b0),.request_phase(4'b0),.request_address(96'b0),.request_root(5'b0),.request_recipient(16'b0),
 .query_v(v),.commit_v(v),.commit_pending(v),.native_write_allowed(write_allowed),.read_v(read_v),.read_ready(v),
 .response_v(v),.response_data(512'b0),.q_v(q_v),.q_ready(v),.release_v(v),.release_ready(release_ready),.release_context(16'b0),.release_version(32'b0),
 .recipients_quiescent(v),.transport_flush_req(v),.transport_flush_ack(flush_ack));
 integer i;
 initial begin
  for(i=0;i<32;i=i+1) begin @(negedge clk); rst_n=1; v=i[0]; #1;
   if(!write_allowed||acquire_ready||read_v||q_v||release_ready||flush_ack) $fatal(1,"disabled adapter changes native acceptance");
  end
  $display("PASS default-off adapter leaves native write acceptance enabled and emits no transport events"); $finish;
 end
endmodule
