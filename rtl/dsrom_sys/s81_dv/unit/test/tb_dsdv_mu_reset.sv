`timescale 1ns/1ps
module tb_dsdv_mu_reset;
 reg clk=0, rst=0; always #0.5 clk=~clk;
 wire [759:0] old_r,new_r;
 ot_rst_relay #(.REGIONS(760)) old(.clk(clk),.rst_n_in(rst),.rst_n(old_r));
 dsdv_mu_reset_tree #(.REGIONS(760)) dut(.clk(clk),.rst_n_in(rst),.rst_n(new_r));
 integer checks=0;
 always @(negedge clk) begin
   if(new_r!==old_r) $fatal(1,"reset release differs old %b new %b",old_r[0],new_r[0]);
   checks=checks+1;
 end
 initial begin
   #0.1; repeat(20) begin #4.2 rst=1; #8.7 rst=0; end
   #3; $display("MU_RESET PASS checks %0d regions760 release_edges3 async_assert1",checks); $finish;
 end
endmodule
