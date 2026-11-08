module ot_sram_1r1w_128x256_m1_r2c2(input clk,input r_ce_in,input [6:0] r_addr_in,output [255:0] rd_out,input w_ce_in,input [6:0] w_addr_in,input [255:0] wd_in,input [255:0] w_mask_in,input [1:0] rr_en,input [13:0] rr_addr,input [1:0] cr_en,input [15:0] cr_sel);
(* anyseq *) reg [255:0] fv_rd; assign rd_out=fv_rd;
endmodule
