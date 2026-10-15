// Joint physical hardening of actual SRAM→capture path. Two256-sink
// capture roots inside this bank, all other stage roots hard. Same9roots/4edges.
module qvm_su_bank_jointcap_native #(parameter integer MUT=0)(
 input wire ck_ctrl,ck_in_lo,ck_in_hi,ck_mem_lo,ck_mem_hi,ck_cap_lo,ck_cap_hi,ck_out_lo,ck_out_hi,
 input wire rst_n,re,we,input wire[9:0]ra,wl,input wire[15:0]wm,input wire[511:0]wd,output wire[511:0]q);
 wire pre,pwe;wire[9:0]pra,pwl;wire[15:0]pwm;wire[511:0]pwd,bq,cq,bm;
 qvm_su_bank_ctrl_native u_ctrl(.clk(ck_ctrl),.rst_n(rst_n),.re(re),.we(we),.ra(ra),.wl(wl),.wm(wm),.p_re(pre),.p_we(pwe),.p_ra(pra),.p_wl(pwl),.p_wm(pwm));
 qvm_data256_native u_in_lo(.clk(ck_in_lo),.d(wd[255:0]^(MUT==2?256'd1:256'd0)),.q(pwd[255:0]));
 qvm_data256_native u_in_hi(.clk(ck_in_hi),.d(wd[511:256]),.q(pwd[511:256]));
 genvar e;generate for(e=0;e<16;e=e+1)begin:g_mask assign bm[e*32+:32]={32{pwm[e]}};end endgenerate
 ot_sram_1r1w_1024x256_m2_r2c2 u_lo(.clk(ck_mem_lo),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[255:0]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[255:0]),.w_mask_in(bm[255:0]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_1024x256_m2_r2c2 u_hi(.clk(ck_mem_hi),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[511:256]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[511:256]),.w_mask_in(bm[511:256]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 reg [255:0] cap_lo;
 always @(posedge ck_cap_lo)cap_lo<=bq[255:0];
 assign cq[255:0]=cap_lo;
 reg [255:0] cap_hi;
 always @(posedge ck_cap_hi)cap_hi<=bq[511:256];
 assign cq[511:256]=cap_hi;
 qvm_data256_native u_out_lo(.clk(ck_out_lo),.d(MUT==1?bq[255:0]:cq[255:0]),.q(q[255:0]));
 qvm_data256_native u_out_hi(.clk(ck_out_hi),.d(cq[511:256]),.q(q[511:256]));
endmodule
