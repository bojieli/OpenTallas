module ot_sram_1r1w_1024x256_m2_r2c2(input wire clk,input wire[1:0] cr_en,input wire[15:0] cr_sel,input wire[9:0] r_addr_in,input wire r_ce_in,output reg[255:0] rd_out,input wire[17:0] rr_addr,input wire[1:0] rr_en,input wire[9:0] w_addr_in,input wire w_ce_in,input wire[255:0] w_mask_in,input wire[255:0] wd_in);
reg[255:0] mem[0:1023];integer i;
always @(posedge clk)begin
if(w_ce_in)for(i=0;i<256;i=i+1)if(w_mask_in[i])mem[w_addr_in][i]<=wd_in[i];
if(r_ce_in)rd_out<=mem[r_addr_in];
end
endmodule
