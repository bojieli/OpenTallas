// Physical pin-access successor; same 32x512 mask32/RW ABI and one-cycle read.
module ot_sram_1r1w_32x512_m1 (
 input wire clk,r_ce_in,input wire[4:0]r_addr_in,output wire[511:0]rd_out,
 input wire w_ce_in,input wire[4:0]w_addr_in,input wire[511:0]wd_in,input wire[15:0]w_mask_in);
 ot_sram_1r1w_32x512_m1_p192_mir u_p192 (
 .clk(clk),.r_ce_in(r_ce_in),.r_addr_in(r_addr_in),.rd_out(rd_out),
 .w_ce_in(w_ce_in),.w_addr_in(w_addr_in),.wd_in(wd_in),.w_mask_in(w_mask_in));
endmodule
