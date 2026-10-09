#!/bin/bash
# hbm-forks 2026-10-09: TT mapped-cell area (yosys + ASAP7 RVT TT, no P&R) of the SM's BF16 MAC column
# (ot_hbm_accel_smh_tc_col) at L = 16 (today, per tile) and L = 32 (one-beat INT8 issue), and of the INT8 line
# adapter (64 converters, today) -- the inputs of the one-beat INT8 pricing in review_queue/hbm-forks.md.
# Usage (repo root, remote): bash physical/hbm_forks/int8_issue_area.sh OUTDIR
set -u
O=$1; rm -rf $O; mkdir -p $O
PDK=$HOME/.local/opentallas-pdk-asap7/lib/NLDM
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
{ echo 'library (cmb) {'; for f in $(ls $PDK/*_RVT_TT_*.lib | sort); do sed '1,/{/d;$d' $f; done; echo '}'; } > $O/combined.lib
SRC="rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/v41rom/ot_v41_bterm.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/gpu/ot_gpu_fadd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv"
run() { # tag top params
  cat > $O/$1.ys <<YS
read_verilog -sv -Irtl/hdc -Irtl/common $SRC
hierarchy -check -top $2 $3
synth -top $2 -flatten
dfflibmap -liberty $O/combined.lib
abc -liberty $O/combined.lib
clean
tee -o $O/$1.stat stat -liberty $O/combined.lib
YS
  $Y -q -s $O/$1.ys > $O/$1.log 2>&1; echo "$1 rc=$? $(grep -i 'chip area' $O/$1.stat)" >> $O/summary.txt
}
run tc16 ot_hbm_accel_smh_tc_col "-chparam L 16" &
run tc32 ot_hbm_accel_smh_tc_col "-chparam L 32" &
run line ot_hbm_accel_int8_line "" &
wait; cat $O/summary.txt
