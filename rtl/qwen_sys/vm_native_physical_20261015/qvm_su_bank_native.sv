// Exact selected NSB1/DEPTHS695/LAWS10 operand-bank physical partition.
module qvm_su_bank_ctrl_native(input wire clk,rst_n,re,we,input wire[9:0]ra,wl,input wire[15:0]wm,
 output reg p_re,p_we,output reg[9:0]p_ra,p_wl,output reg[15:0]p_wm);
 reg rr;
 always @(posedge clk or negedge rst_n)if(!rst_n)rr<=0;else rr<=1;
 always @(posedge clk or negedge rr)if(!rr)begin p_re<=0;p_we<=0;end else begin p_re<=re;p_we<=we;end
 always @(posedge clk)begin p_ra<=ra;p_wl<=wl;p_wm<=wm;end
endmodule
module qvm_su_bank_native #(parameter integer MUT=0)(
 input wire ck_ctrl,ck_in_lo,ck_in_hi,ck_mem_lo,ck_mem_hi,ck_cap_lo,ck_cap_hi,ck_out_lo,ck_out_hi,
 input wire rst_n,re,we,input wire[9:0]ra,wl,input wire[15:0]wm,input wire[511:0]wd,output wire[511:0]q);
 wire pre,pwe;wire[9:0]pra,pwl;wire[15:0]pwm;wire[511:0]pwd,bq,cq,bm;
 qvm_su_bank_ctrl_native u_ctrl(.clk(ck_ctrl),.rst_n(rst_n),.re(re),.we(we),.ra(ra),.wl(wl),.wm(wm),.p_re(pre),.p_we(pwe),.p_ra(pra),.p_wl(pwl),.p_wm(pwm));
 qvm_data256_native u_in_lo(.clk(ck_in_lo),.d(wd[255:0]^(MUT==2?256'd1:256'd0)),.q(pwd[255:0]));
 qvm_data256_native u_in_hi(.clk(ck_in_hi),.d(wd[511:256]),.q(pwd[511:256]));
 genvar e;generate for(e=0;e<16;e=e+1)begin:g_mask assign bm[e*32+:32]={32{pwm[e]}};end endgenerate
 ot_sram_1r1w_1024x256_m2_r2c2 u_lo(.clk(ck_mem_lo),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[255:0]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[255:0]),.w_mask_in(bm[255:0]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_1024x256_m2_r2c2 u_hi(.clk(ck_mem_hi),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[511:256]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[511:256]),.w_mask_in(bm[511:256]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 qvm_data256_native u_cap_lo(.clk(ck_cap_lo),.d(bq[255:0]),.q(cq[255:0]));
 qvm_data256_native u_cap_hi(.clk(ck_cap_hi),.d(bq[511:256]),.q(cq[511:256]));
 qvm_data256_native u_out_lo(.clk(ck_out_lo),.d(MUT==1?bq[255:0]:cq[255:0]),.q(q[255:0]));
 qvm_data256_native u_out_hi(.clk(ck_out_hi),.d(cq[511:256]),.q(q[511:256]));
endmodule
