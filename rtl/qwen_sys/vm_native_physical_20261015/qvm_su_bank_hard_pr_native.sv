// su5 pin-register successor of qvm_su_bank_hard_native.sv (su3): same ports, same edges, same data/contents.
// su3 native audit: q launched from the hard u_out_lo/hi data256 leaves (launch 300.1 on 512 pins) and ra/re captured
// inside the hard u_ctrl leaf (168.1 raw, ~223 with the child's 54.9 ps insertion).  As in qvm_bank ne5, the control stage
// and the output stage sit in this parent as pin registers on their own CTS roots (ck_ctrl, ck_out_lo, ck_out_hi):
// bit-identical logic to qvm_su_bank_ctrl_native and qvm_data256_native, zero added edges.  u_in_lo/hi, u_cap_lo/hi
// (hard data256 views) and the two 1024x256 SRAMs keep their direct clock entries.
module qvm_su_bank_native #(parameter integer MUT=0)(
 input wire ck_ctrl,ck_in_lo,ck_in_hi,ck_mem_lo,ck_mem_hi,ck_cap_lo,ck_cap_hi,ck_out_lo,ck_out_hi,
 input wire rst_n,re,we,input wire[9:0]ra,wl,input wire[15:0]wm,input wire[511:0]wd,output reg[511:0]q);
 reg pre,pwe;reg[9:0]pra,pwl;reg[15:0]pwm;reg rr;
 wire[511:0]pwd,bq,cq,bm;
 // control pin registers (exact qvm_su_bank_ctrl_native body)
 always @(posedge ck_ctrl or negedge rst_n)if(!rst_n)rr<=0;else rr<=1;
 always @(posedge ck_ctrl or negedge rr)if(!rr)begin pre<=0;pwe<=0;end else begin pre<=(MUT==4?1'b1:re);pwe<=we;end
 always @(posedge ck_ctrl)begin pra<=ra;pwl<=wl;pwm<=wm;end
 qvm_data256_native u_in_lo(.clk(ck_in_lo),.d(wd[255:0]^(MUT==2?256'd1:256'd0)),.q(pwd[255:0]));
 qvm_data256_native u_in_hi(.clk(ck_in_hi),.d(wd[511:256]),.q(pwd[511:256]));
 genvar e;generate for(e=0;e<16;e=e+1)begin:g_mask assign bm[e*32+:32]={32{pwm[e]}};end endgenerate
 ot_sram_1r1w_1024x256_m2_r2c2 u_lo(.clk(ck_mem_lo),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[255:0]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[255:0]),.w_mask_in(bm[255:0]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_1024x256_m2_r2c2 u_hi(.clk(ck_mem_hi),.r_ce_in(pre),.r_addr_in(pra),.rd_out(bq[511:256]),.w_ce_in(pwe),.w_addr_in(pwl),.wd_in(pwd[511:256]),.w_mask_in(bm[511:256]),.rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 qvm_data256_native u_cap_lo(.clk(ck_cap_lo),.d(bq[255:0]),.q(cq[255:0]));
 qvm_data256_native u_cap_hi(.clk(ck_cap_hi),.d(bq[511:256]),.q(cq[511:256]));
 // output pin registers (exact qvm_data256_native body); MUT 3 drops the lo register (q one edge early)
 generate if(MUT==3)begin:g_drop
  always @(posedge ck_out_hi)q[511:256]<=cq[511:256];
  always @* q[255:0]=cq[255:0];
 end else begin:g_reg
  always @(posedge ck_out_lo)q[255:0]<=(MUT==1?bq[255:0]:cq[255:0]);
  always @(posedge ck_out_hi)q[511:256]<=cq[511:256]^(MUT==5?(256'd1<<200):256'd0);
 end endgenerate
endmodule
