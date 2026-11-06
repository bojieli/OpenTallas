module ot_sram_1r1w_128x256_m1_r2c2(input clk,r_ce_in,input[6:0]r_addr_in,output reg[255:0]rd_out,input w_ce_in,input[6:0]w_addr_in,input[255:0]wd_in,w_mask_in,input[1:0]rr_en,input[13:0]rr_addr,input[1:0]cr_en,input[15:0]cr_sel);
reg[255:0]mem[0:127];always @(posedge clk)begin if(w_ce_in)mem[w_addr_in]<=(mem[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);if(r_ce_in)rd_out<=mem[r_addr_in];end endmodule
