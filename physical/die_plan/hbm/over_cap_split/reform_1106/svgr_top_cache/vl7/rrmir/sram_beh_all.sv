// bench-only behavioural SRAMs, zero-initialised (2-state contents; an X descriptor made if(x) branch differently) (registered read on r_ce_in, write on w_ce_in), same model for ref and dut.
module ot_sram_1r1w_128x256_m1_r0c0_g256(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,input wire w_mask_in);
 reg[255:0]m[0:127];integer ii;initial begin rd_out=0;for(ii=0;ii<128;ii=ii+1)m[ii]=0;end
 always @(posedge clk)begin if(r_ce_in)rd_out<=m[r_addr_in];if(w_ce_in&&w_mask_in)m[w_addr_in]<=wd_in;end
endmodule
module ot_sram_1r1w_128x256_m1_r2c2(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,input wire[255:0]w_mask_in,input wire[1:0]rr_en,input wire[13:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg[255:0]m[0:127];integer ii;initial begin rd_out=0;for(ii=0;ii<128;ii=ii+1)m[ii]=0;end
 always @(posedge clk)begin if(r_ce_in)rd_out<=m[r_addr_in];if(w_ce_in)m[w_addr_in]<=(m[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);end
endmodule
module ot_sram_1r1w_1024x256_m2_r2c2(input wire clk,r_ce_in,input wire[9:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[9:0]w_addr_in,input wire[255:0]wd_in,input wire[255:0]w_mask_in,input wire[1:0]rr_en,input wire[17:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg[255:0]m[0:1023];integer ii;initial begin rd_out=0;for(ii=0;ii<1024;ii=ii+1)m[ii]=0;end
 always @(posedge clk)begin if(r_ce_in)rd_out<=m[r_addr_in];if(w_ce_in)m[w_addr_in]<=(m[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);end
endmodule
