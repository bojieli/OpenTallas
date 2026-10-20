`timescale 1ns/1ps
module tb_rst32;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;wire[191:0]q;wire[27:0]old;
 ot_rst_relay #(.REGIONS(28)) ref_relay(.clk(ck),.rst_n_in(rst),.rst_n(old));
 genvar g;generate for(g=0;g<6;g=g+1)begin:bank
`ifdef OT_RST32_MUT
 ot_rst_relay #(.REGIONS(32),.TREE_STAGES(2)) dut(.clk(ck),.rst_n_in(rst),.rst_n(q[g*32+:32]));
`else
 ot_rst_relay #(.REGIONS(32)) dut(.clk(ck),.rst_n_in(rst),.rst_n(q[g*32+:32]));
`endif
 end endgenerate
 integer checks=0;integer seed=17;
 always @(rst or posedge ck)begin #0.01;if(q!=={192{old[0]}})begin $display("RST32 FAIL checks=%0d",checks);$fatal;end checks=checks+1;end
 initial begin
 #1;for(integer k=0;k<1000;k=k+1)begin
 #($urandom_range(1,27))rst=0;
 #($urandom_range(1,51))rst=1;
 #($urandom_range(40,110));
 end
 $display("RST32 PASS checks=%0d",checks);$finish;
 end
endmodule
