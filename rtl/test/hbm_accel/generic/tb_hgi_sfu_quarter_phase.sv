`timescale 1ns/1ps
module tb_hgi_sfu_quarter_phase;
localparam N=16, AW=24, NW=16, WC=130+8+1+2+1+1+4+3+1+1+8+AW+5+1;
reg clk=0; always #0.416667 clk=~clk;
reg rst_n=0;
parameter integer MUT_PHASE=0;
reg  go = '0;
reg [NW-1:0] i_nout = '0;
reg [NW-1:0] i_nin = '0;
reg [1:0] i_asrc = '0;
reg [1:0] i_bsrc = '0;
reg [1:0] i_csrc = '0;
reg [1:0] i_dsrc = '0;
reg [AW-1:0] i_abase = '0;
reg [AW-1:0] i_aso = '0;
reg [AW-1:0] i_asi = '0;
reg [AW-1:0] i_aibase = '0;
reg [1:0] i_aind = '0;
reg [AW-1:0] i_bbase = '0;
reg [AW-1:0] i_bso = '0;
reg [AW-1:0] i_bsi = '0;
reg  i_bhalf = '0;
reg [AW-1:0] i_cbase = '0;
reg [AW-1:0] i_cso = '0;
reg [AW-1:0] i_csi = '0;
reg  i_cpair = '0;
reg [AW-1:0] i_dbase = '0;
reg [AW-1:0] i_dso = '0;
reg [AW-1:0] i_dsi = '0;
reg  i_arnd = '0;
reg  i_arelu = '0;
reg  i_amin = '0;
reg  i_cclip = '0;
reg [2:0] i_m1 = '0;
reg [1:0] i_m2 = '0;
reg [2:0] i_qm = '0;
reg [2:0] i_ad = '0;
reg [2:0] i_sfu = '0;
reg [2:0] i_e1 = '0;
reg [1:0] i_e2 = '0;
reg  i_rnd = '0;
reg [1:0] i_dst = '0;
reg [AW-1:0] i_obase = '0;
reg [AW-1:0] i_oso = '0;
reg [AW-1:0] i_osi = '0;
reg [AW-1:0] i_orow = '0;
reg [1:0] i_red = '0;
reg  i_redsq = '0;
reg  i_redwhole = '0;
reg  i_redtree = '0;
reg  i_redrnd = '0;
reg [AW-1:0] i_rbase = '0;
reg [AW-1:0] i_rso = '0;
reg [31:0] i_imm1 = '0;
reg [31:0] i_imm2 = '0;
reg [31:0] i_imm3 = '0;
reg [1:0] i_ch_src = '0;
reg [7:0] i_ch_seq = '0;
reg [15:0] i_ch_lead = '0;
reg [15:0] i_ch_mul = '0;
reg [7:0] x_seq = '0;
reg [7:0] x_dseq = '0;
reg [15:0] x_cnt = '0;
wire [1741:0] actual; wire ready; wire admission_fault;
wire [15:0] avw,ovw,avr,ovr;wire [383:0] ava,ova,avi,ovi;
wire [511:0] avd,ovd;wire [1535:0] ard,ord;wire [63:0] arre,orre;
reg [2047:0] ardq='0,ordq='0;reg [511:0] aviq='0,oviq='0;
function automatic [31:0] memword(input [23:0] a);memword={1'b0,8'h7e,a[22:0]^23'h312345};endfunction
always @(posedge clk)begin
for(integer j=0;j<16;j++)begin
 if(avr[j])aviq[j*32+:32]<=memword(avi[j*24+:24]);
 if(ovr[j])oviq[j*32+:32]<=memword(ovi[j*24+:24]);
 for(integer k=0;k<4;k++)begin
 if(arre[j*4+k])ardq[(j*4+k)*32+:32]<=memword(ard[(j*4+k)*24+:24]);
 if(orre[j*4+k])ordq[(j*4+k)*32+:32]<=memword(ord[(j*4+k)*24+:24]);
end end end
ot_hgi_sfu_native_quarter #(.ENABLE_NATIVE(1)) dut(.go(go),.i_nout(i_nout),.i_nin(i_nin),.i_asrc(i_asrc),.i_bsrc(i_bsrc),.i_csrc(i_csrc),.i_dsrc(i_dsrc),.i_abase(i_abase),.i_aso(i_aso),.i_asi(i_asi),.i_aibase(i_aibase),.i_aind(i_aind),.i_bbase(i_bbase),.i_bso(i_bso),.i_bsi(i_bsi),.i_bhalf(i_bhalf),.i_cbase(i_cbase),.i_cso(i_cso),.i_csi(i_csi),.i_cpair(i_cpair),.i_dbase(i_dbase),.i_dso(i_dso),.i_dsi(i_dsi),.i_arnd(i_arnd),.i_arelu(i_arelu),.i_amin(i_amin),.i_cclip(i_cclip),.i_m1(i_m1),.i_m2(i_m2),.i_qm(i_qm),.i_ad(i_ad),.i_sfu(i_sfu),.i_e1(i_e1),.i_e2(i_e2),.i_rnd(i_rnd),.i_dst(i_dst),.i_obase(i_obase),.i_oso(i_oso),.i_osi(i_osi),.i_orow(i_orow),.i_red(i_red),.i_redsq(i_redsq),.i_redwhole(i_redwhole),.i_redtree(i_redtree),.i_redrnd(i_redrnd),.i_rbase(i_rbase),.i_rso(i_rso),.i_imm1(i_imm1),.i_imm2(i_imm2),.i_imm3(i_imm3),.i_ch_src(i_ch_src),.i_ch_seq(i_ch_seq),.i_ch_lead(i_ch_lead),.i_ch_mul(i_ch_mul),.x_seq(x_seq),.x_dseq(x_dseq),.x_cnt(x_cnt),.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),.rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),.vi_q(aviq),.rd_q(ardq),.vi_re(avr),.vi_addr(avi),.rd_addr(ard),.rd_re(arre),.vm_we(avw),.vm_waddr(ava),.vm_wdata(avd),.ready(ready),.admission_fault(admission_fault));
assign actual=dut.u_ctl.grid_control;
ot_hdc_v41x_vec #(.N(16),.M(16),.AW(24),.NW(16),.MLAT(6),.ALAT(6),.DDIV(21),.OPR(1),.CAPR(1),.GSH(1),.KIMM(1),.DENR(1),.DRING(3),.SFUT(0),.BCAST_STAGES(1),.RET_STAGES(5),.CTL12(2),.SIDEX(4)) oracle(.go(go),.i_nout(i_nout),.i_nin(i_nin),.i_asrc(i_asrc),.i_bsrc(i_bsrc),.i_csrc(i_csrc),.i_dsrc(i_dsrc),.i_abase(i_abase),.i_aso(i_aso),.i_asi(i_asi),.i_aibase(i_aibase),.i_aind(i_aind),.i_bbase(i_bbase),.i_bso(i_bso),.i_bsi(i_bsi),.i_bhalf(i_bhalf),.i_cbase(i_cbase),.i_cso(i_cso),.i_csi(i_csi),.i_cpair(i_cpair),.i_dbase(i_dbase),.i_dso(i_dso),.i_dsi(i_dsi),.i_arnd(i_arnd),.i_arelu(i_arelu),.i_amin(i_amin),.i_cclip(i_cclip),.i_m1(i_m1),.i_m2(i_m2),.i_qm(i_qm),.i_ad(i_ad),.i_sfu(i_sfu),.i_e1(i_e1),.i_e2(i_e2),.i_rnd(i_rnd),.i_dst(i_dst),.i_obase(i_obase),.i_oso(i_oso),.i_osi(i_osi),.i_orow(i_orow),.i_red(i_red),.i_redsq(i_redsq),.i_redwhole(i_redwhole),.i_redtree(i_redtree),.i_redrnd(i_redrnd),.i_rbase(i_rbase),.i_rso(i_rso),.i_imm1(i_imm1),.i_imm2(i_imm2),.i_imm3(i_imm3),.i_ch_src(i_ch_src),.i_ch_seq(i_ch_seq),.i_ch_lead(i_ch_lead),.i_ch_mul(i_ch_mul),.x_seq(x_seq),.x_dseq(x_dseq),.x_cnt(x_cnt),.clk(clk),.rst_n(rst_n),.vi_q(oviq),.rd_q(ordq),.vi_re(ovr),.vi_addr(ovi),.rd_addr(ord),.rd_re(orre),.vm_we(ovw),.vm_waddr(ova),.vm_wdata(ovd));
wire [1199:0] oracle_terms;
for(genvar s=0;s<5;s++)for(genvar b=0;b<10;b++) begin
if(b<4)assign oracle_terms[(s*10+b)*24+:24]=oracle.tr_ldc[(s*4+b)*24+:24];else assign oracle_terms[(s*10+b)*24+:24]=0;end
wire [1741:0] expected={oracle.tr_ld,oracle.tr_ldbank,oracle_terms,oracle.tr_emit,oracle.tr_bank,oracle.tr_ov,oracle.tr_iv,oracle.tr_no,oracle.tr_ni,oracle.tr_ls,oracle.tr_lvw,oracle.tr_vb,oracle.tr_krow,oracle.tr_obase,oracle.tr_aibase,oracle.tr_aind,oracle.tr_gsh,oracle.tr_cpair,oracle.tr_dst,oracle.tr_srcs,oracle.cwx[WC-9],oracle.cwx[WC-10],oracle.cwx[WC-11],oracle.cwx[WC-12],oracle.cwx[WC-13 -: 32],oracle.cwp[WC-45 -: 3],oracle.cwp[WC-48 -: 32],oracle.cwm[WC-45 -: 3],oracle.cwm[WC-80 -: 2],oracle.cwm[WC-82 -: 3],oracle.cwm[WC-48 -: 32],oracle.cwa[WC-85 -: 3],oracle.cwa[WC-88 -: 32],oracle.cwi[WC-120 -: 3],oracle.cws[WC-120 -: 3],oracle.cws[WC-123 -: 3],oracle.cws[WC-88 -: 32],oracle.cwe[WC-126 -: 2],oracle.cwe[WC-48 -: 32],oracle.cwo[WC-128],oracle.cwo[WC-129 -: 2]};
reg [1741:0] lag; integer checks=0, emits=0, desc=0, words=0;
always @(posedge clk)lag<=actual;
always @(negedge clk)if(rst_n)begin
if((MUT_PHASE?lag:actual)!==expected)$fatal(1,"CONTROL_PHASE_MISMATCH cycle=%0d",checks);
if(dut.u_ctl.ret_p!==oracle.ret_p || dut.u_ctl.ret_i!==oracle.ret_i || dut.u_ctl.cr_cnt!==oracle.cr_cnt || dut.u_ctl.cr_seq!==oracle.cr_seq || dut.u_ctl.cr_dseq!==oracle.cr_dseq || dut.u_ctl.emit!==oracle.emit)$fatal(1,"RETIRE_CREDIT_MISMATCH");
if(avw!==ovw)$fatal(1,"WRITE_PHASE_MISMATCH cycle=%0d actual=%h oracle=%h",checks,avw,ovw);
for(integer j=0;j<16;j++)if(avw[j])begin
 if(ava[j*24+:24]!==ova[j*24+:24] || avd[j*32+:32]!==ovd[j*32+:32])$fatal(1,"WRITE_WORD_MISMATCH cycle=%0d lane=%0d addr=%h/%h data=%h/%h",checks,j,ava[j*24+:24],ova[j*24+:24],avd[j*32+:32],ovd[j*32+:32]);words++;end
checks++;if(dut.u_ctl.emit)emits++;end
initial begin
 i_dst=1;i_asrc=0;i_bsrc=0;i_csrc=0;i_dsrc=0;
 i_asi=1;i_bsi=1;i_csi=1;i_dsi=1;i_osi=1;
 i_imm1=32'h3f800000;i_imm2=32'h3f800000;i_imm3=32'h3f800000;
 x_seq=8'hff;x_dseq=8'hff;
 repeat(4)@(negedge clk);rst_n=1;
 for(integer run=0;run<2;run++)begin
 for(integer d=0;d<96;d++)begin
  while(!ready)@(negedge clk);
  i_nout=16'(1+d%7);i_nin=16'(16+d%9);i_aso=24'(16+d%9);i_bso=i_aso;i_cso=i_aso;i_dso=i_aso;i_oso=i_aso;
  i_abase=24'(d*1024);i_bbase=24'(d*1024+256);i_cbase=24'(d*1024+512);i_dbase=24'(d*1024+768);i_obase=24'(d*1024+8192);
  i_m1=3'(d%3);i_m2=2'(d%2);i_ad=3'(d%3);i_sfu=(d%4==0)?0:(d%4==1)?1:(d%4==2)?4:5;
  i_e1=3'(d%2);i_e2=2'(d%2);i_ch_seq=8'(d);
  go=1;@(negedge clk);go=0;desc++;
  repeat(200)@(negedge clk);
 end
 repeat(300)@(negedge clk);rst_n=0;repeat(3)@(negedge clk);rst_n=1;
 end
 if(emits<192)$fatal(1,"NO_REAL_EMIT");
 i_red=1;go=1;@(negedge clk);go=0;
 if(ready || !admission_fault)$fatal(1,"UNSUPPORTED_REDUCTION_ACCEPTED");
 $display("PASS SFU CLOSED grid c12 phase checks=%0d emits=%0d descriptors=%0d words=%0d warm_reset=1 unsupported_reduction=refused",checks,emits,desc,words);$finish;
end
endmodule
