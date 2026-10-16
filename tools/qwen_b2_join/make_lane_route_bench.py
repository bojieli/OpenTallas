#!/usr/bin/env python3
"""Q-B2 10-16: controller + ports + halfband lanes + compact uppers, REF vs DUT route equivalence (back-to-back ops).

Two complete compositions of the ACTUAL RTL receive the same command stream and the same tree words on the same
absolute cycles (the tiles' word timing is set by the ME issue path, which the b2 remap does not touch):
  REF: zero die routes, generic constants (controller tree LNK 0 / CLNK 0, halfband lnk 0) -- the component design point;
  DUT: every b2 route as a register chain of its allocated edge count (TC tc->port, AM port->controller, LC lc->halfband,
       F halfband->upper words, R upper->HB0 return, SEL selector->upper incl. the 3 fork registers, TY halfband->port)
       and the calibrated constants (controller tree LNK / CLNK successor, halfband lnk strap).
Ops run BACK TO BACK (one reset at start only).  Checked transaction streams, REF vs DUT, in order and bit-exact:
every port rq beat (rows, masks, 16 x FP32 results = tree result x released scale) of all six halves, every port am
partial, every controller mx write and the controller's final scalar argmax of every op.  Words are random FP32 per
cycle, so any relative shift between tags, selects, words and returns changes results.  REF results must vary (not
vacuous).  Defines: OT_LR_TC, OT_LR_AM, OT_LR_LC, OT_LR_F, OT_LR_R, OT_LR_SEL, OT_LR_TY, OT_LR_HL (DUT halfband lnk).
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM_TB = 'tools/qwen_b2_join/tb_b2_rom_e3.sv'

DLY = '''
// route model: one register per allocated relay edge, tap chosen at run time (+plusarg) so one build sweeps routes
module tb_lr_dly #(parameter integer W=1, DMAX=24)(input wire clk, input wire [5:0] tap, input wire [W-1:0] d, output wire [W-1:0] q);
 reg [W-1:0] r[1:DMAX];
 always @(posedge clk)begin r[1]<=d; for(integer i=2;i<=DMAX;i=i+1) r[i]<=r[i-1]; end
 assign q=(tap==0)?d:r[tap];
 initial if(DMAX<1)$fatal(1,"DMAX");
endmodule
'''

INST = r'''
// ================================ composition {X} ================================
reg[5:0]{X}_t_TC=0,{X}_t_AM=0,{X}_t_LC=0,{X}_t_F=0,{X}_t_R=0,{X}_t_SEL=0,{X}_t_TY=0,{X}_t_HL=0;
wire[23:0]{X}_acc;wire {X}_idle;wire[15:0]{X}_prog;wire[94:0]{X}_ret;wire {X}_mxwe;wire[23:0]{X}_mxa;wire[15:0]{X}_mxm;wire[511:0]{X}_mxd;
wire {X}_scale_re,{X}_pv;wire[23:0]{X}_gre;wire[575:0]{X}_scale_addr;wire[112:0]{X}_pf;wire[12:0]{X}_sel,{X}_tv;
wire[305:0]{X}_pam;wire[5:0]{X}_pfault;wire[15:0]{X}_ld;
{TREE} {X}_tree(.clk(clk),.rst_n(rs),.me_acc_o({X}_acc),.me_idle_o({X}_idle),.me_prog_o({X}_prog),
 .up_fault(1'b0),.land_cnt({X}_ld),.scale_re({X}_scale_re),.scale_gre({X}_gre),.scale_addr({X}_scale_addr),.t_sel_e({X}_sel),.t_tv_e({X}_tv),.tr_fault(16'd0),
 .p_v_e2({X}_pv),.p_f_e2({X}_pf),.p_am({X}_pam),.p_fault({X}_pfault),.fab_fault(1'b0),.ov(),.mx_we({X}_mxwe),.mx_addr({X}_mxa),.mx_mask({X}_mxm),.mx_data({X}_mxd),.cmd(cmd),.ret({X}_ret));
wire[25:0]{X}_lc={{X}_tv,{X}_sel};wire[25:0]{X}_lcd;wire[3:0]{X}_s4,{X}_s4d;
assign {X}_s4={{X}_tv[11],{X}_tv[10],{X}_sel[11],{X}_sel[10]};
tb_lr_dly #(26) {X}_r_lc(clk,{X}_t_LC,{X}_lc,{X}_lcd);
tb_lr_dly #(4) {X}_r_sel(clk,{X}_t_SEL,{X}_s4,{X}_s4d);
wire[340:0]{X}_tc[0:5],{X}_tcd[0:5];wire[2212:0]{X}_rq[0:5];wire[51:0]{X}_am[0:5],{X}_amd[0:5];wire[2049:0]{X}_cw[0:5];
wire[2047:0]{X}_ty[0:5],{X}_tyd[0:5];wire[512:0]{X}_hp[0:5];wire[5:0]{X}_hf;
wire[8*65-1:0]{X}_face[0:5],{X}_faced[0:5];wire[7:0]{X}_ffault[0:5],{X}_ffaultd[0:5];
wire[8*194-1:0]{X}_ret_u,{X}_ret_ud;wire[7:0]{X}_uf;
for(genvar h=0;h<6;h=h+1)begin:{X}_g
 assign {X}_tc[h]={{X}_scale_addr[192*(h/2)+:192],{X}_gre[8*(h/2)+:8],{X}_scale_re,{X}_pf,{X}_pv,{X}_tv,{X}_sel};
 tb_lr_dly #(341) r_tc(clk,{X}_t_TC,{X}_tc[h],{X}_tcd[h]);
 tb_lr_dly #(52) r_am(clk,{X}_t_AM,{X}_am[h],{X}_amd[h]);
 tb_lr_dly #(2048) r_ty(clk,{X}_t_TY,{X}_ty[h],{X}_tyd[h]);
 tb_lr_dly #(8*65) r_f(clk,{X}_t_F,{X}_face[h],{X}_faced[h]);
 tb_lr_dly #(8) r_ff(clk,{X}_t_F,{X}_ffault[h],{X}_ffaultd[h]);
 qfd_port_half_b2 #(.ROM_BAND(h/2),.ROM_HALF(h%2))port(
  .hb(3'(h)),.ck(clk),.rst_n(rs),
  .ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),
  .ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),
  .ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),
  .ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),
  .ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),
  .bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
  .tc({X}_tcd[h]),.ty({X}_tyd[h]),.rq({X}_rq[h]),.am({X}_am[h]),.cw0({X}_cw[h]));
 assign {X}_pam[51*h+:51]={X}_amd[h][50:0];assign {X}_pfault[h]={X}_amd[h][51];
 qfd_sp_halfband_lanes_b2_l2 hb(
  .ck(clk),.ck_l0(clk),.ck_l1(clk),.ck_l2(clk),.ck_l3(clk),.ck_l4(clk),.ck_l5(clk),.ck_l6(clk),.ck_l7(clk),
  .ck_l8(clk),.ck_l9(clk),.ck_l10(clk),.ck_l11(clk),.ck_l12(clk),.ck_l13(clk),.ck_l14(clk),.ck_l15(clk),
  .rst_n(rs),.b0(h==0),.lnk({X}_t_HL),.tw(words[h]),.c({X}_lcd),
  .tt_l0(h==0?{X}_ret_ud[194*0+:194]:194'd0),.tt_l1(h==0?{X}_ret_ud[194*1+:194]:194'd0),
  .tt_l2(h==0?{X}_ret_ud[194*2+:194]:194'd0),.tt_l3(h==0?{X}_ret_ud[194*3+:194]:194'd0),
  .tt_l4(h==0?{X}_ret_ud[194*4+:194]:194'd0),.tt_l5(h==0?{X}_ret_ud[194*5+:194]:194'd0),
  .tt_l6(h==0?{X}_ret_ud[194*6+:194]:194'd0),.tt_l7(h==0?{X}_ret_ud[194*7+:194]:194'd0),
  .pw_l0({X}_face[h][65*0+:65]),.pw_l1({X}_face[h][65*1+:65]),.pw_l2({X}_face[h][65*2+:65]),.pw_l3({X}_face[h][65*3+:65]),
  .pw_l4({X}_face[h][65*4+:65]),.pw_l5({X}_face[h][65*5+:65]),.pw_l6({X}_face[h][65*6+:65]),.pw_l7({X}_face[h][65*7+:65]),
  .f_up({X}_ffault[h]),.pw({X}_hp[h]),.ty({X}_ty[h]),.f({X}_hf[h]));
end
tb_lr_dly #(8*194) {X}_r_ret(clk,{X}_t_R,{X}_ret_u,{X}_ret_ud);
for(genvar u=0;u<8;u=u+1)begin:{X}_gu
 wire[383:0]w;wire[191:0]y;wire[5:0]vv,ff;wire uu,uv;
 for(genvar hh=0;hh<6;hh=hh+1)begin:gi
  assign w[64*hh+:64]={X}_faced[hh][65*u+:64];assign vv[hh]={X}_faced[hh][65*u+64];assign ff[hh]={X}_ffaultd[hh][u];
 end
 qfd_band_upper_b2_l2_s4 up(.clk(clk),.rst_n(rs),.pw(w),.pw_v(vv),.lf(ff),
  .sel_e({X}_s4d[1:0]),.tv_e({X}_s4d[3:2]),.tt_ty(y),.tt_use(uu),.tt_v(uv),.fault({X}_uf[u]));
 assign {X}_ret_u[194*u+:194]={uv,uu,y};
end
// environment: landed bursts = HB0 result bursts (the VM lands one row burst per HB0 rq burst), fixed 8-edge lag
reg[15:0]{X}_bursts=0;wire[15:0]{X}_bd;
always @(posedge clk)if(!rs){X}_bursts<=0;else if({X}_rq[0][2212]){X}_bursts<={X}_bursts+1;
tb_lr_dly #(16) {X}_r_ld(clk,6'd8,{X}_bursts,{X}_bd);
assign {X}_ld={X}_bd;
'''

TOP = r'''
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
'''

CHECK = r'''
// ================================ REF vs DUT transaction streams ================================
localparam integer QN=1<<16;
reg[2212:0]rq_q[0:5][0:QN-1];integer rq_w[0:5],rq_r[0:5];
reg[51:0]am_q[0:5][0:QN-1];integer am_w[0:5],am_r[0:5];
reg[551:0]mx_q[0:QN-1];integer mx_w=0,mx_r=0;
integer nrq=0,nam=0,nmx=0,errors=0;reg[31:0]first_rq;integer distinct=0;
initial for(integer h=0;h<6;h=h+1)begin rq_w[h]=0;rq_r[h]=0;am_w[h]=0;am_r[h]=0;end
always @(negedge clk)if(rs)begin
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
 if(r_mxwe)begin mx_q[mx_w%QN]={r_mxa,r_mxm,r_mxd};mx_w=mx_w+1;end
 if(d_mxwe)begin if(mx_r>=mx_w||{d_mxa,d_mxm,d_mxd}!==mx_q[mx_r%QN])begin if(errors<8)$display("MISMATCH mx write %0d",mx_r);errors=errors+1;end mx_r=mx_r+1;nmx=nmx+1;end
end
task automatic op(input integer pc,nout,tiles,ksize,spacing,wbase,split,wcs,obase,ots,ojs,rounds,xbase,xcs,input integer output_en=1,input integer amax_en=0);
 begin
 cmd={24'd0,1'b0,1'(amax_en),1'(output_en),1'b0,24'(ojs),24'(ots),24'(obase),1'(rounds),24'(wcs),4'(split),3'd0,24'(xcs),24'd0,24'd1,24'(xbase),24'd1,24'd8,24'(spacing),24'(wbase),1'b0,18'(ksize),18'(tiles),18'(nout),1'b1};
 @(negedge clk);#0.01;cmd[0]=0;
 // back to back: the next op issues as soon as BOTH controllers are idle again (no reset)
 repeat(20)@(negedge clk);
 while(!(r_idle&&d_idle))@(negedge clk);
 #0.01;
 if(amax_en)begin
  if(r_ret[77:27]!==d_ret[77:27])begin $display("MISMATCH scalar argmax pc%0d ref%h dut%h",pc,r_ret[77:27],d_ret[77:27]);errors=errors+1;end
 end
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
  op(12,4096,3,2,16,64,8,48,0,8,1,1,50672,2,1,1);
  op(16,3072,1,32,256,112,7,336,2975,8,1,1,4096,32,1,1);
  op(20,4096,3,6,48,368,8,528,0,8,1,1,55280,6,1,1);
  op(103,6144,8,8,64,0,9,29376,0,8,1,1,8192,8,1,1);
 end
 repeat(400)@(negedge clk);
 for(integer h=0;h<6;h=h+1)if(rq_r[h]!=rq_w[h]||am_r[h]!=am_w[h])begin $display("MISMATCH stream length h%0d rq ref%0d dut%0d am ref%0d dut%0d",h,rq_w[h],rq_r[h],am_w[h],am_r[h]);errors=errors+1;end
 if(mx_r!=mx_w)begin $display("MISMATCH mx stream ref%0d dut%0d",mx_w,mx_r);errors=errors+1;end
 if(nrq<100||distinct<10)begin $display("FAIL vacuous comparison rq%0d distinct%0d",nrq,distinct);$fatal(1);end
 if(errors)begin $display("FAIL b2 lane route equivalence errors%0d",errors);$fatal(1);end
 $display("PASS b2 lane route equivalence REF==DUT rq_beats%0d am%0d mx%0d distinct%0d (TC%0d AM%0d LC%0d F%0d R%0d SEL%0d TY%0d HL%0d)",nrq,nam,nmx,distinct,
  d_t_TC,d_t_AM,d_t_LC,d_t_F,d_t_R,d_t_SEL,d_t_TY,d_t_HL);
 $finish;
end
endmodule
'''


def make(ref_tree, dut_tree, out):
    body = TOP
    for X, tree, z in (('r', ref_tree, True), ('d', dut_tree, False)):
        s = INST.replace('{X}', X).replace('{TREE}', tree)
        body += s
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('`timescale 1ns/1ps\n' + DLY + body + CHECK)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ref-tree', required=True)
    ap.add_argument('--dut-tree', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    make(a.ref_tree, a.dut_tree, a.out)


if __name__ == '__main__':
    main()
