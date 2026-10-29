`timescale 1ns/1ps
// Smallest B-hop mechanism: the first required gated capture is s=3
// stages from the ungated launch. K=2 must capture it; K=3 must miss it.
module tb_hop_bound;
  reg ck=0;
  always #0.5 ck=~ck;
  reg rst_n=0, en=0, valid=0;
  reg [31:0] data=0;
  reg p0_v=0,p1_v=0;
  reg [31:0] p0=0,p1=0;
  wire good_ck,bad_ck;
  ot_a0_icg_hop #(.K(2)) good(.ck(ck),.rst_n(rst_n),.en(en),.xk(1'b0),.gck(good_ck));
  ot_a0_icg_hop #(.K(2)) mutant(.ck(ck),.rst_n(rst_n),.en(en),.xk(1'b1),.gck(bad_ck));
  always @(posedge ck) begin
    p0_v<=valid; p1_v<=p0_v; p0<=data; p1<=p0;
  end
  reg [31:0] good_q=0,bad_q=0;
  always @(posedge good_ck) if(p1_v) good_q<=p1;
  always @(posedge bad_ck) if(p1_v) bad_q<=p1;
  integer checks=0, caught=0, errors=0;
  initial begin
    repeat(8) @(negedge ck);
    rst_n=1;
    repeat(8) @(negedge ck);
    for(integer i=1;i<=32;i=i+1) begin
      data=32'h3f800000+i; valid=1; en=1;
      @(negedge ck); valid=0; en=0;
      repeat(2) @(negedge ck);
      checks=checks+1;
      if(good_q !== data) errors=errors+1;
      if(bad_q !== data) caught=caught+1;
      repeat(8) @(negedge ck);
    end
    if(errors || caught != checks) $fatal(1,"HOP_BOUND_FAIL checks=%0d errors=%0d caught=%0d",checks,errors,caught);
    $display("HOP_BOUND_PASS s=3 K=2 checks=%0d errors=0 K3_mutant_caught=%0d",checks,caught);
    $finish;
  end
endmodule
