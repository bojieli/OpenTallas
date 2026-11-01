#!/bin/bash
# DIE-QC-59S STA-0171 repro: actual signed QC child headers/libs/LEFs (codex 50faadff5 + its input LEFs) in a minimal
# ORFS `make synth` (synth -> synth_odb = OpenROAD read_verilog of 1_2_yosys.v).  Variants: main = origin/main
# native_bb.py; fix = this branch; neg = fix with a non-default MIF(1) override (must stop synth).
set -euo pipefail
R=$1; WT=$2; MAINBB=$3
D=results/rtl/qc_parameter_macro_preload_1101
IN=/srv/opentallas-scratch2/claude/codex-qc-param-preload-1101/input
mkdir -p $R/src
for m in qfd_dv_s8x_vmr qfd_dv_s8_crh_rp1; do
  git -C ~/OpenTallas show 50faadff5:$D/$m/${m}_bb.v > $R/src/${m}_bb.v
  git -C ~/OpenTallas show 50faadff5:$D/$m/native.sv > $R/src/${m}_native.sv
  git -C ~/OpenTallas show 50faadff5:$D/$m/signed.lib > $R/src/${m}_tc.lib
  cp $IN/$m.lef $R/src/$m.lef
done
for v in main fix neg; do
  K=$R/$v; rm -rf $K; mkdir -p $K/rtl; cp $R/src/* $K/rtl/
  if [ $v = main ]; then cp $MAINBB $K/native_bb.py; else cp $WT/tools/die_plan/native_bb.py $K/native_bb.py; fi
  P=0; [ $v = neg ] && P=1
  cat > $K/rtl/top.sv <<SV
module top (input wire ck, input wire rst_n, input wire [7:0] re, input wire [191:0] addr,
    input wire [7:0] vm_we, input wire [191:0] vm_waddr, input wire [255:0] vm_wdata,
    input wire w16_we, input wire [23:0] w16_addr, input wire [511:0] w16_data,
    input wire w1_we, input wire [23:0] w1_addr, input wire [31:0] w1_data,
    input wire tw_we, input wire [1:0] tw_kind, input wire [23:0] tw_addr, input wire [511:0] tw_d,
    output wire [255:0] q_v, output wire [255:0] q_c0, output wire [255:0] q_c1, output wire [2:0] fault);
  // parent form of qfd_dv_s8_vm8q_rp1: .MIF(MIF) / .MUT(MUT) elaborate to numeric overrides on the signed masters
  qfd_dv_s8x_vmr #(.MUT(0), .MIF($P)) u_va (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(q_v), .vm_we(vm_we),
    .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
    .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fault[0]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
  qfd_dv_s8_crh_rp1 #(.MIF(0)) u_cl (.ck(ck), .rst_n(rst_n), .cr_re(re), .cr_addr(addr), .q(q_c0), .tw_we(tw_we),
    .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(fault[1]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
  qfd_dv_s8_crh_rp1 u_ch (.ck(ck), .rst_n(rst_n), .cr_re(re), .cr_addr(addr), .q(q_c1), .tw_we(tw_we),
    .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(fault[2]), .ft_ck_i(ck), .ft_ck_o(), .ft_rst_i(rst_n), .ft_rst_o());
endmodule
SV
  echo 'create_clock -name ck -period 833 [get_ports ck]' > $K/constraint.sdc
  cat > $K/config.mk <<MK
export PLATFORM = asap7
export DESIGN_NAME = top
export DESIGN_NICKNAME = top
export VERILOG_FILES = /work/rtl/qfd_dv_s8x_vmr_bb.v /work/rtl/qfd_dv_s8_crh_rp1_bb.v /work/rtl/qfd_dv_s8x_vmr_native.sv /work/rtl/qfd_dv_s8_crh_rp1_native.sv /work/rtl/top.sv
export SDC_FILE = /work/constraint.sdc
export ADDITIONAL_LEFS = /work/rtl/qfd_dv_s8x_vmr.lef /work/rtl/qfd_dv_s8_crh_rp1.lef
export ADDITIONAL_LIBS = /work/rtl/qfd_dv_s8x_vmr_tc.lib /work/rtl/qfd_dv_s8_crh_rp1_tc.lib
export DIE_AREA = 0 0 800 800
export CORE_AREA = 5 5 795 795
MK
done
sha256sum $R/src/* > $R/inputs.sha256
