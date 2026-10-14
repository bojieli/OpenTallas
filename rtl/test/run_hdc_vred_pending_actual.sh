#!/bin/bash
set -e
out=$1; kind=${2:-exact}; qla=${3:-3};qlm=${4:-3};top=tb_hdc_vred_pending_actual
if [ "$kind" = phase ];then top=tb_hdc_vred_phase_mut;fi
mkdir -p "$out"
extra=(); if [ "$kind" = mutant ]; then extra+=(-DOT_VRED_REGION_MUT);fi
if [ "$kind" = guard_mutant ]; then extra+=(-DOT_VRED_PENDING_MUT);fi
iverilog -g2012 "${extra[@]}" -s "$top" -P"$top.DUTQLA=$qla" -P"$top.DUTQLM=$qlm" -o "$out/bench.vvp" rtl/test/tb_hdc_vred_pending_actual.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/physical/ot_hdc_vreduce_entries64.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fpu.sv >"$out/compile.log" 2>&1
set +e
vvp "$out/bench.vvp" >"$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
exit "$rc"
