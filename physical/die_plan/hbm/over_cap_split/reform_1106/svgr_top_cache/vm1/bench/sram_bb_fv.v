// FV stub: read data 0 (rd_out feeds out_packet only, never the control state the wptr invariant reads)
module ot_sram_1r1w_128x256_m1_r0c0_g256(input clk,input r_ce_in,input [6:0] r_addr_in,output [255:0] rd_out,input w_ce_in,input [6:0] w_addr_in,input [255:0] wd_in,input w_mask_in);
assign rd_out=256'd0;
endmodule
