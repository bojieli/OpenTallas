// bench-only behavioural 1R1W SRAM (registered read on r_ce_in, write on w_ce_in); both instances use the same model.
module ot_sram_1r1w_128x256_m1_r0c0_g256(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,input wire w_mask_in);
 reg[255:0]m[0:127];
 always @(posedge clk)begin if(r_ce_in)rd_out<=m[r_addr_in];if(w_ce_in&&w_mask_in)m[w_addr_in]<=wd_in;end
endmodule
