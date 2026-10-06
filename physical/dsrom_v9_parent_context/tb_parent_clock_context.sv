`timescale 1ns/1ps
module tb_parent_clock_context;
 reg clk=0,rst_n=1;always #5 clk=~clk;
 reg [1629:0] bc=0;reg en=1;reg [15:0] row=16'hc123;reg rv=0;
 wire gclk;wire [548:0] xs;wire [66:0] root;
 ot_v41_v9_parent_clock_context dut(.clk(clk),.rst_n(rst_n),.broadcast_source(bc),.cfg_rom_q(48'd0),
 .walk_busy(1'b0),.drain_gt1(1'b0),.qz_en_r(en),.qz_ext_lo(1'b0),
 .tree_valid(2'b0),.tree_idle(2'b11),.tree_payload(124'd0),.busy_source(1'b0),
 .frontend_fault_source(1'b0),.bank_fault_source(2'b0),.root_v(rv),.root_e(1'b0),
 .root_row(row),.root_bf(16'h7654),.root_pos(3'd3),.root_fp32(32'h3f800000),
 .engine_clk(gclk),.engine_xs(xs),.captured_root(root));
 integer edges=0;
 always @(posedge gclk) begin if (clk!==1) $fatal(1,"gated edge unrelated to Qfree");edges=edges+1;end
 reg [548:0] held;integer stopped;
 initial begin
 #1 rst_n=0;repeat(4) @(negedge clk);rst_n=1;rv=1;
 repeat(8) @(negedge clk);
 if(root!=={1'b1,1'b0,14'h0123,16'h7654,3'd3,32'h3f800000}) $fatal(1,"actual root14 capture differs");
 en=0;repeat(5) @(negedge clk);stopped=edges;held=xs;
 // XS q0 data bit in literal BW1630 broadcast packing, while cfg/go stay zero.
 bc[1350]=1;row=16'hffff;
 repeat(6) @(negedge clk);
 if(edges!=stopped || xs!==held) $fatal(1,"gated XS changed while gate stopped");
 if(root[64:51]!==14'h3fff) $fatal(1,"free root capture stopped with child gate");
 en=1;repeat(6) @(negedge clk);
 if(edges<=stopped || xs===held) $fatal(1,"gated XS did not resume on Qfree edges");
 $display("PASS parent same-master gated XS freeze/resume; independent free root14 capture");$finish;
 end
endmodule
