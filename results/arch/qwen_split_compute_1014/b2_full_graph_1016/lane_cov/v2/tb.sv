`timescale 1ns/1ps

// route model: one register per allocated relay edge, tap chosen at run time (+plusarg) so one build sweeps routes
module tb_lr_dly #(parameter integer W=1, DMAX=24)(input wire clk, input wire [5:0] tap, input wire [W-1:0] d, output wire [W-1:0] q);
 reg [W-1:0] r[1:DMAX];
 always @(posedge clk)begin r[1]<=d; for(integer i=2;i<=DMAX;i=i+1) r[i]<=r[i-1]; end
 assign q=(tap==0)?d:r[tap];
 initial if(DMAX<1)$fatal(1,"DMAX");
endmodule

module tb_b2_lane_route;
reg clk=0,rs=0;always #1 clk=~clk;
reg[379:0]cmd=0;
// tree words: random finite FP32 per (absolute cycle, half, word), identical for REF and DUT
reg[2047:0]words[0:5];integer cyc=0;
function automatic [31:0] wv(input integer t,input integer h,input integer i);
 reg[31:0]x; begin x=32'(t)*32'h9E3779B1 ^ 32'(h)*32'h85EBCA77 ^ 32'(i)*32'hC2B2AE3D ^ 32'h27D4EB2F;
 x=x^(x>>15);x=x*32'h2C1B3C6D;x=x^(x>>12);x=x*32'h297A2D39;x=x^(x>>15);
 wv={x[31],8'd112+{3'd0,x[27:23]},x[22:0]}; end
endfunction
always @(negedge clk)begin cyc=cyc+1;for(integer h=0;h<6;h=h+1)for(integer i=0;i<64;i=i+1)words[h][32*i+:32]=wv(cyc,h,i);end

// ================================ composition r ================================
reg[5:0]r_t_TC=0,r_t_AM=0,r_t_LC=0,r_t_F=0,r_t_R=0,r_t_SEL=0,r_t_TY=0,r_t_HL=0;
wire[23:0]r_acc;wire r_idle;wire[15:0]r_prog;wire[94:0]r_ret;wire r_mxwe;wire[23:0]r_mxa;wire[15:0]r_mxm;wire[511:0]r_mxd;
wire r_scale_re,r_pv;wire[23:0]r_gre;wire[575:0]r_scale_addr;wire[112:0]r_pf;wire[12:0]r_sel,r_tv;
wire[305:0]r_pam;wire[5:0]r_pfault;wire[15:0]r_ld;
qfd_tt_ctlm_tree_b2 r_tree(.clk(clk),.rst_n(rs),.me_acc_o(r_acc),.me_idle_o(r_idle),.me_prog_o(r_prog),
 .up_fault(1'b0),.land_cnt(r_ld),.scale_re(r_scale_re),.scale_gre(r_gre),.scale_addr(r_scale_addr),.t_sel_e(r_sel),.t_tv_e(r_tv),.tr_fault(16'd0),
 .p_v_e2(r_pv),.p_f_e2(r_pf),.p_am(r_pam),.p_fault(r_pfault),.fab_fault(1'b0),.ov(),.mx_we(r_mxwe),.mx_addr(r_mxa),.mx_mask(r_mxm),.mx_data(r_mxd),.cmd(cmd),.ret(r_ret));
wire[25:0]r_lc={r_tv,r_sel};wire[25:0]r_lcd;wire[3:0]r_s4,r_s4d;
assign r_s4={r_tv[11],r_tv[10],r_sel[11],r_sel[10]};
tb_lr_dly #(26) r_r_lc(clk,r_t_LC,r_lc,r_lcd);
tb_lr_dly #(4) r_r_sel(clk,r_t_SEL,r_s4,r_s4d);
wire[340:0]r_tc[0:5],r_tcd[0:5];wire[2212:0]r_rq[0:5];wire[51:0]r_am[0:5],r_amd[0:5];wire[2049:0]r_cw[0:5];
wire[2047:0]r_ty[0:5],r_tyd[0:5];wire[512:0]r_hp[0:5];wire[5:0]r_hf;
wire[8*65-1:0]r_face[0:5],r_faced[0:5];wire[7:0]r_ffault[0:5],r_ffaultd[0:5];
wire[8*194-1:0]r_ret_u,r_ret_ud;wire[7:0]r_uf;
for(genvar h=0;h<6;h=h+1)begin:r_g
 assign r_tc[h]={r_scale_addr[192*(h/2)+:192],r_gre[8*(h/2)+:8],r_scale_re,r_pf,r_pv,r_tv,r_sel};
 tb_lr_dly #(341) dl_tc(clk,r_t_TC,r_tc[h],r_tcd[h]);
 tb_lr_dly #(52) dl_am(clk,r_t_AM,r_am[h],r_amd[h]);
 tb_lr_dly #(2048) dl_ty(clk,r_t_TY,r_ty[h],r_tyd[h]);
 tb_lr_dly #(8*65) dl_f(clk,r_t_F,r_face[h],r_faced[h]);
 tb_lr_dly #(8) dl_ff(clk,r_t_F,r_ffault[h],r_ffaultd[h]);
 qfd_port_half_b2 #(.ROM_BAND(h/2),.ROM_HALF(h%2))port(
  .hb(3'(h)),.ck(clk),.rst_n(rs),
  .ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),
  .ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),
  .ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),
  .ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),
  .ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),
  .bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
  .tc(r_tcd[h]),.ty(r_tyd[h]),.rq(r_rq[h]),.am(r_am[h]),.cw0(r_cw[h]));
 assign r_pam[51*h+:51]=r_amd[h][50:0];assign r_pfault[h]=r_amd[h][51];
 qfd_sp_halfband_lanes_b2_l2 hb(
  .ck(clk),.ck_l0(clk),.ck_l1(clk),.ck_l2(clk),.ck_l3(clk),.ck_l4(clk),.ck_l5(clk),.ck_l6(clk),.ck_l7(clk),
  .ck_l8(clk),.ck_l9(clk),.ck_l10(clk),.ck_l11(clk),.ck_l12(clk),.ck_l13(clk),.ck_l14(clk),.ck_l15(clk),
  .rst_n(rs),.b0(h==0),.lnk(r_t_HL),.tw(words[h]),.c(r_lcd),
  .tt_l0(h==0?r_ret_ud[194*0+:194]:194'd0),.tt_l1(h==0?r_ret_ud[194*1+:194]:194'd0),
  .tt_l2(h==0?r_ret_ud[194*2+:194]:194'd0),.tt_l3(h==0?r_ret_ud[194*3+:194]:194'd0),
  .tt_l4(h==0?r_ret_ud[194*4+:194]:194'd0),.tt_l5(h==0?r_ret_ud[194*5+:194]:194'd0),
  .tt_l6(h==0?r_ret_ud[194*6+:194]:194'd0),.tt_l7(h==0?r_ret_ud[194*7+:194]:194'd0),
  .pw_l0(r_face[h][65*0+:65]),.pw_l1(r_face[h][65*1+:65]),.pw_l2(r_face[h][65*2+:65]),.pw_l3(r_face[h][65*3+:65]),
  .pw_l4(r_face[h][65*4+:65]),.pw_l5(r_face[h][65*5+:65]),.pw_l6(r_face[h][65*6+:65]),.pw_l7(r_face[h][65*7+:65]),
  .f_up(r_ffault[h]),.pw(r_hp[h]),.ty(r_ty[h]),.f(r_hf[h]));
end
tb_lr_dly #(8*194) r_r_ret(clk,r_t_R,r_ret_u,r_ret_ud);
for(genvar u=0;u<8;u=u+1)begin:r_gu
 wire[383:0]w;wire[191:0]y;wire[5:0]vv,ff;wire uu,uv;
 for(genvar hh=0;hh<6;hh=hh+1)begin:gi
  assign w[64*hh+:64]=r_faced[hh][65*u+:64];assign vv[hh]=r_faced[hh][65*u+64];assign ff[hh]=r_ffaultd[hh][u];
 end
 qfd_band_upper_b2_l2_s4 up(.clk(clk),.rst_n(rs),.pw(w),.pw_v(vv),.lf(ff),
  .sel_e(r_s4d[1:0]),.tv_e(r_s4d[3:2]),.tt_ty(y),.tt_use(uu),.tt_v(uv),.fault(r_uf[u]));
 assign r_ret_u[194*u+:194]={uv,uu,y};
end
// environment: landed bursts = HB0 result bursts (the VM lands one row burst per HB0 rq burst), fixed 8-edge lag
reg[15:0]r_bursts=0;wire[15:0]r_bd;
always @(posedge clk)if(!rs)r_bursts<=0;else if(r_rq[0][2212])r_bursts<=r_bursts+1;
tb_lr_dly #(16) r_r_ld(clk,6'd8,r_bursts,r_bd);
assign r_ld=r_bd;

// ================================ composition d ================================
reg[5:0]d_t_TC=0,d_t_AM=0,d_t_LC=0,d_t_F=0,d_t_R=0,d_t_SEL=0,d_t_TY=0,d_t_HL=0;
wire[23:0]d_acc;wire d_idle;wire[15:0]d_prog;wire[94:0]d_ret;wire d_mxwe;wire[23:0]d_mxa;wire[15:0]d_mxm;wire[511:0]d_mxd;
wire d_scale_re,d_pv;wire[23:0]d_gre;wire[575:0]d_scale_addr;wire[112:0]d_pf;wire[12:0]d_sel,d_tv;
wire[305:0]d_pam;wire[5:0]d_pfault;wire[15:0]d_ld;
qfd_tt_ctlm_tree_b2 d_tree(.clk(clk),.rst_n(rs),.me_acc_o(d_acc),.me_idle_o(d_idle),.me_prog_o(d_prog),
 .up_fault(1'b0),.land_cnt(d_ld),.scale_re(d_scale_re),.scale_gre(d_gre),.scale_addr(d_scale_addr),.t_sel_e(d_sel),.t_tv_e(d_tv),.tr_fault(16'd0),
 .p_v_e2(d_pv),.p_f_e2(d_pf),.p_am(d_pam),.p_fault(d_pfault),.fab_fault(1'b0),.ov(),.mx_we(d_mxwe),.mx_addr(d_mxa),.mx_mask(d_mxm),.mx_data(d_mxd),.cmd(cmd),.ret(d_ret));
wire[25:0]d_lc={d_tv,d_sel};wire[25:0]d_lcd;wire[3:0]d_s4,d_s4d;
assign d_s4={d_tv[11],d_tv[10],d_sel[11],d_sel[10]};
tb_lr_dly #(26) d_r_lc(clk,d_t_LC,d_lc,d_lcd);
tb_lr_dly #(4) d_r_sel(clk,d_t_SEL,d_s4,d_s4d);
wire[340:0]d_tc[0:5],d_tcd[0:5];wire[2212:0]d_rq[0:5];wire[51:0]d_am[0:5],d_amd[0:5];wire[2049:0]d_cw[0:5];
wire[2047:0]d_ty[0:5],d_tyd[0:5];wire[512:0]d_hp[0:5];wire[5:0]d_hf;
wire[8*65-1:0]d_face[0:5],d_faced[0:5];wire[7:0]d_ffault[0:5],d_ffaultd[0:5];
wire[8*194-1:0]d_ret_u,d_ret_ud;wire[7:0]d_uf;
for(genvar h=0;h<6;h=h+1)begin:d_g
 assign d_tc[h]={d_scale_addr[192*(h/2)+:192],d_gre[8*(h/2)+:8],d_scale_re,d_pf,d_pv,d_tv,d_sel};
 tb_lr_dly #(341) dl_tc(clk,d_t_TC,d_tc[h],d_tcd[h]);
 tb_lr_dly #(52) dl_am(clk,d_t_AM,d_am[h],d_amd[h]);
 tb_lr_dly #(2048) dl_ty(clk,d_t_TY,d_ty[h],d_tyd[h]);
 tb_lr_dly #(8*65) dl_f(clk,d_t_F,d_face[h],d_faced[h]);
 tb_lr_dly #(8) dl_ff(clk,d_t_F,d_ffault[h],d_ffaultd[h]);
 qfd_port_half_b2 #(.ROM_BAND(h/2),.ROM_HALF(h%2))port(
  .hb(3'(h)),.ck(clk),.rst_n(rs),
  .ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),
  .ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),
  .ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),
  .ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),
  .ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),
  .bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
  .tc(d_tcd[h]),.ty(d_tyd[h]),.rq(d_rq[h]),.am(d_am[h]),.cw0(d_cw[h]));
 assign d_pam[51*h+:51]=d_amd[h][50:0];assign d_pfault[h]=d_amd[h][51];
 qfd_sp_halfband_lanes_b2_l2 hb(
  .ck(clk),.ck_l0(clk),.ck_l1(clk),.ck_l2(clk),.ck_l3(clk),.ck_l4(clk),.ck_l5(clk),.ck_l6(clk),.ck_l7(clk),
  .ck_l8(clk),.ck_l9(clk),.ck_l10(clk),.ck_l11(clk),.ck_l12(clk),.ck_l13(clk),.ck_l14(clk),.ck_l15(clk),
  .rst_n(rs),.b0(h==0),.lnk(d_t_HL),.tw(words[h]),.c(d_lcd),
  .tt_l0(h==0?d_ret_ud[194*0+:194]:194'd0),.tt_l1(h==0?d_ret_ud[194*1+:194]:194'd0),
  .tt_l2(h==0?d_ret_ud[194*2+:194]:194'd0),.tt_l3(h==0?d_ret_ud[194*3+:194]:194'd0),
  .tt_l4(h==0?d_ret_ud[194*4+:194]:194'd0),.tt_l5(h==0?d_ret_ud[194*5+:194]:194'd0),
  .tt_l6(h==0?d_ret_ud[194*6+:194]:194'd0),.tt_l7(h==0?d_ret_ud[194*7+:194]:194'd0),
  .pw_l0(d_face[h][65*0+:65]),.pw_l1(d_face[h][65*1+:65]),.pw_l2(d_face[h][65*2+:65]),.pw_l3(d_face[h][65*3+:65]),
  .pw_l4(d_face[h][65*4+:65]),.pw_l5(d_face[h][65*5+:65]),.pw_l6(d_face[h][65*6+:65]),.pw_l7(d_face[h][65*7+:65]),
  .f_up(d_ffault[h]),.pw(d_hp[h]),.ty(d_ty[h]),.f(d_hf[h]));
end
tb_lr_dly #(8*194) d_r_ret(clk,d_t_R,d_ret_u,d_ret_ud);
for(genvar u=0;u<8;u=u+1)begin:d_gu
 wire[383:0]w;wire[191:0]y;wire[5:0]vv,ff;wire uu,uv;
 for(genvar hh=0;hh<6;hh=hh+1)begin:gi
  assign w[64*hh+:64]=d_faced[hh][65*u+:64];assign vv[hh]=d_faced[hh][65*u+64];assign ff[hh]=d_ffaultd[hh][u];
 end
 qfd_band_upper_b2_l2_s4 up(.clk(clk),.rst_n(rs),.pw(w),.pw_v(vv),.lf(ff),
  .sel_e(d_s4d[1:0]),.tv_e(d_s4d[3:2]),.tt_ty(y),.tt_use(uu),.tt_v(uv),.fault(d_uf[u]));
 assign d_ret_u[194*u+:194]={uv,uu,y};
end
// environment: landed bursts = HB0 result bursts (the VM lands one row burst per HB0 rq burst), fixed 8-edge lag
reg[15:0]d_bursts=0;wire[15:0]d_bd;
always @(posedge clk)if(!rs)d_bursts<=0;else if(d_rq[0][2212])d_bursts<=d_bursts+1;
tb_lr_dly #(16) d_r_ld(clk,6'd8,d_bursts,d_bd);
assign d_ld=d_bd;

// ================================ REF vs DUT transaction streams ================================
localparam integer QN=1<<16;
reg[2212:0]rq_q[0:5][0:QN-1];integer rq_w[0:5],rq_r[0:5];
reg[51:0]am_q[0:5][0:QN-1];integer am_w[0:5],am_r[0:5];
reg[551:0]mx_q[0:QN-1];integer mx_w=0,mx_r=0;
integer nrq=0,nam=0,nmx=0,errors=0;integer upper_r[0:7],upper_d[0:7],upper_nz[0:7],upper_use[0:7];reg[50:0]sa_q[0:QN-1];integer sa_w=0,sa_r=0;reg[50:0]r_sa_l=0,d_sa_l=0;reg[31:0]first_rq;integer distinct=0;
initial for(integer u=0;u<8;u=u+1)begin upper_r[u]=0;upper_d[u]=0;upper_nz[u]=0;upper_use[u]=0;end
initial for(integer h=0;h<6;h=h+1)begin rq_w[h]=0;rq_r[h]=0;am_w[h]=0;am_r[h]=0;end
always @(negedge clk)if(rs)begin
 for(integer u=0;u<8;u=u+1)begin
  if(r_ret_u[194*u+193])begin upper_r[u]=upper_r[u]+1;if(r_ret_u[194*u+:192]!=0)upper_nz[u]=upper_nz[u]+1;if(r_ret_u[194*u+192])upper_use[u]=upper_use[u]+1;end
  if(d_ret_u[194*u+193])upper_d[u]=upper_d[u]+1;
 end
 for(integer h=0;h<6;h=h+1)begin
  if(r_rq[h][2212])begin rq_q[h][rq_w[h]%QN]=r_rq[h];rq_w[h]=rq_w[h]+1;
   if(nrq==0)first_rq=r_rq[h][31:0];else if(r_rq[h][31:0]!==first_rq)distinct=distinct+1;end
  if(d_rq[h][2212])begin
   if(rq_r[h]>=rq_w[h])begin if(errors<8)$display("MISMATCH DUT rq beat with no REF beat h%0d",h);errors=errors+1;end
   else begin if(d_rq[h]!==rq_q[h][rq_r[h]%QN])begin if(errors<8)$display("MISMATCH rq h%0d beat%0d dut%h ref%h",h,rq_r[h],d_rq[h][63:0],rq_q[h][rq_r[h]%QN][63:0]);errors=errors+1;end
    rq_r[h]=rq_r[h]+1;nrq=nrq+1;end
  end
  if(r_am[h][50])begin am_q[h][am_w[h]%QN]=r_am[h];am_w[h]=am_w[h]+1;end
  if(d_am[h][50])begin
   if(am_r[h]>=am_w[h]||d_am[h]!==am_q[h][am_r[h]%QN])begin if(errors<8)$display("MISMATCH am h%0d beat%0d",h,am_r[h]);errors=errors+1;end
   am_r[h]=am_r[h]+1;nam=nam+1;
  end
 end
 if(r_ret[77:27]!==r_sa_l)begin r_sa_l=r_ret[77:27];sa_q[sa_w%QN]=r_sa_l;sa_w=sa_w+1;end
 if(d_ret[77:27]!==d_sa_l)begin d_sa_l=d_ret[77:27];if(sa_r>=sa_w||d_sa_l!==sa_q[sa_r%QN])begin if(errors<8)$display("MISMATCH scalar argmax event %0d",sa_r);errors=errors+1;end sa_r=sa_r+1;end
 if(r_mxwe)begin mx_q[mx_w%QN]={r_mxa,r_mxm,r_mxd};mx_w=mx_w+1;end
 if(d_mxwe)begin if(mx_r>=mx_w||{d_mxa,d_mxm,d_mxd}!==mx_q[mx_r%QN])begin if(errors<8)$display("MISMATCH mx write %0d",mx_r);errors=errors+1;end mx_r=mx_r+1;nmx=nmx+1;end
end
task automatic op(input integer pc,nout,tiles,ksize,spacing,wbase,split,wcs,obase,ots,ojs,rounds,xbase,xcs,input integer output_en=1,input integer amax_en=0,input integer rmax_en=0,input integer mbase=0);
 integer ref_busy_seen,dut_busy_seen;
 begin
 cmd={24'(mbase),1'(rmax_en),1'(amax_en),1'(output_en),1'b0,24'(ojs),24'(ots),24'(obase),1'(rounds),24'(wcs),4'(split),3'd0,24'(xcs),24'd0,24'd1,24'(xbase),24'd1,24'd8,24'(spacing),24'(wbase),1'b0,18'(ksize),18'(tiles),18'(nout),1'b1};
 @(negedge clk);#0.01;cmd[0]=0;
 // The registered command/status path keeps old ready high for several
 // edges. Observe this command becoming busy before accepting ready again;
 // otherwise an apparent ready can issue and silently lose the following op.
 ref_busy_seen=0;dut_busy_seen=0;
 while(!(ref_busy_seen&&dut_busy_seen))begin
  @(negedge clk);
  if(!r_ret[0])ref_busy_seen=1;
  if(!d_ret[0])dut_busy_seen=1;
 end
 while(!(r_ret[0]&&d_ret[0]))@(negedge clk);
 // ready covers issue only; idle also covers in-flight port results, argmax,
 // mx writes and LANDED accounting. Drain both before the next command.
 while(!(r_idle&&d_idle))@(negedge clk);
 #0.01;
 if(r_ret[94]||d_ret[94]||(|r_pfault)||(|d_pfault))begin $display("FAULT pc%0d ref%0d dut%0d pref%b pdut%b",pc,r_ret[94],d_ret[94],r_pfault,d_pfault);errors=errors+1;end
 $display("OP pc%0d split%0d tiles%0d rq_ref%0d rq_dut%0d am%0d mx%0d errors%0d",pc,split,tiles,rq_w[0],rq_r[0],nam,nmx,errors);
 end
endtask
initial begin
 r_t_SEL=3;
 void'($value$plusargs("TC=%d",d_t_TC));void'($value$plusargs("AM=%d",d_t_AM));void'($value$plusargs("LC=%d",d_t_LC));
 void'($value$plusargs("F=%d",d_t_F));void'($value$plusargs("R=%d",d_t_R));void'($value$plusargs("SEL=%d",d_t_SEL));
 void'($value$plusargs("TY=%d",d_t_TY));void'($value$plusargs("HL=%d",d_t_HL));
 rs=0;repeat(8)@(negedge clk);#0.01;rs=1;repeat(40)@(negedge clk);#0.01;
 for(integer rep=0;rep<2;rep=rep+1)begin
  op(1,768,1,8,64,0,9,0,768,8,1,1,4096,8,1,1);
  op(2,384,1,8,64,0,10,0,768,8,1,1,4096,8,1,1);
  op(12,4096,3,2,16,64,8,48,0,8,1,1,50672,2,1,1);
  op(3,128,1,8,64,0,11,0,768,8,1,1,4096,8,1,1);
  op(16,3072,1,32,256,112,7,336,2975,8,1,1,4096,32,1,1);
  op(20,4096,3,6,48,368,8,528,0,8,1,1,55280,6,1,1);
  op(4,384,2,8,64,0,10,0,768,8,1,1,4096,8,1,1);
  op(103,6144,8,8,64,0,9,29376,0,8,1,1,8192,8,1,1);
 end
 // Ordinary output ops (no argmax) in addition to the argmax ops.
 op(201,768,1,8,64,0,9,0,768,8,1,1,4096,8,1,0);
 op(202,384,1,8,64,0,10,0,768,8,1,1,4096,8,1,0);
 op(203,128,1,8,64,0,11,0,768,8,1,1,4096,8,1,0);
 // Row-max (rmax) ops: the controller mx write stream (cmd[mbase,rmax], one mx write per op) is produced only by
 // rmax ops (Q-B2r 10-16: the 13:30 baseline failed 'vacuous mx' because no op set rmax; amax does not drive mx).
 op(211,768,1,8,64,0,9,0,768,8,1,1,4096,8,1,0,1,12288);
 op(212,384,1,8,64,0,10,0,768,8,1,1,4096,8,1,0,1,12352);
 op(213,128,1,8,64,0,11,0,768,8,1,1,4096,8,1,0,1,12416);
 op(214,4096,3,2,16,64,8,48,0,8,1,1,50672,2,1,0,1,12480);
 while(!(r_idle&&d_idle))@(negedge clk);
 repeat(400)@(negedge clk);
 for(integer h=0;h<6;h=h+1)if(rq_r[h]!=rq_w[h]||am_r[h]!=am_w[h])begin $display("MISMATCH stream length h%0d rq ref%0d dut%0d am ref%0d dut%0d",h,rq_w[h],rq_r[h],am_w[h],am_r[h]);errors=errors+1;end
 if(sa_r!=sa_w)begin $display("MISMATCH scalar stream ref%0d dut%0d",sa_w,sa_r);errors=errors+1;end
 if(mx_r!=mx_w)begin $display("MISMATCH mx stream ref%0d dut%0d",mx_w,mx_r);errors=errors+1;end
 for(integer u=0;u<8;u=u+1)begin
  $display("COVER upper%0d ref_valid%0d dut_valid%0d nonzero%0d used%0d",u,upper_r[u],upper_d[u],upper_nz[u],upper_use[u]);
  if(upper_r[u]==0||upper_r[u]!=upper_d[u]||upper_nz[u]==0||upper_use[u]==0)begin $display("FAIL vacuous upper%0d",u);errors=errors+1;end
 end
 if(nmx==0)begin $display("FAIL vacuous mx output stream");errors=errors+1;end
 if(nrq<100||distinct<10)begin $display("FAIL vacuous comparison rq%0d distinct%0d",nrq,distinct);$fatal(1);end
 if(errors)begin $display("FAIL b2 lane route equivalence errors%0d",errors);$fatal(1);end
 $display("PASS b2 lane route equivalence REF==DUT rq_beats%0d am%0d mx%0d distinct%0d (TC%0d AM%0d LC%0d F%0d R%0d SEL%0d TY%0d HL%0d)",nrq,nam,nmx,distinct,
  d_t_TC,d_t_AM,d_t_LC,d_t_F,d_t_R,d_t_SEL,d_t_TY,d_t_HL);
 $finish;
end
endmodule
