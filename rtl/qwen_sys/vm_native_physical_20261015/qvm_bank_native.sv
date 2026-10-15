// Opt-in physical partition of actual DEPTH174/LAW8 bank. Existing macro,
// input, capture and output edges are preserved; every clock is a real root.
module qvm_bank_input_native(
 input wire clk,rst_n,re,we,
 input wire[7:0]ra,wl,input wire[15:0]wm,input wire[511:0]wd,
 output reg p_re,p_we,output reg[7:0]p_ra,p_wl,
 output reg[15:0]p_wm,output reg[511:0]p_wd);
 reg rr;
 always @(posedge clk or negedge rst_n)if(!rst_n)rr<=0;else rr<=1;
 always @(posedge clk or negedge rr)if(!rr)begin p_re<=0;p_we<=0;end else begin p_re<=re;p_we<=we;end
 always @(posedge clk)begin p_ra<=ra;p_wl<=wl;p_wm<=wm;p_wd<=wd;end
endmodule

module qvm_bank_native #(parameter integer MUT_CAPTURE=0)(
 input wire ck_in,ck_mem_lo,ck_mem_hi,ck_cap,ck_out,
 input wire rst_n,re,we,input wire[7:0]ra,wl,input wire[15:0]wm,
 input wire[511:0]wd,output wire[511:0]q);
 wire pre,pwe;wire[7:0]pra,pwl;wire[15:0]pwm;wire[511:0]pwd,bq,cq,bm;
 qvm_bank_input_native u_input(.clk(ck_in),.rst_n(rst_n),.re(re),.we(we),.ra(ra),.wl(wl),.wm(wm),.wd(wd ^ (MUT_CAPTURE==2 ? 512'd1 : 512'd0)),.p_re(pre),.p_we(pwe),.p_ra(pra),.p_wl(pwl),.p_wm(pwm),.p_wd(pwd));
 genvar e;generate for(e=0;e<16;e=e+1)begin:g_mask assign bm[e*32+:32]={32{pwm[e]}};end endgenerate
 ot_sram_1r1w_256x256_m2_r2c2 u_lo(.clk(ck_mem_lo),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[255:0]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[255:0]),.w_mask_in(bm[255:0]),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_256x256_m2_r2c2 u_hi(.clk(ck_mem_hi),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[511:256]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[511:256]),.w_mask_in(bm[511:256]),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_qfd_vm_delay1_t u_capture(.clk(ck_cap),.d(bq),.q(cq));
 ot_qfd_vm_delay1_t u_output(.clk(ck_out),.d(MUT_CAPTURE==1 ? bq : cq),.q(q));
endmodule
