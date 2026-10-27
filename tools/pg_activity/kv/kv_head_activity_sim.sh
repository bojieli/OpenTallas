#!/bin/bash
# PG-ACTIVITY-KVHBM 10-27: measured switching activity of the KV head eighth (lane8 + stin + stk, t-lanes 2/3 = kv3_head_eighth_e1).
# Bench = tb_qkh_head_r4_s (head_st_bench.sh: Q load + K passes 600/300/400 rows on every cycle, PASS lockstep), Verilator 5.050 --trace,
# VCD of ua (ot_qkh_head_native_r4) g_t[2] + g_t[3] only.   usage: kv_head_activity_sim.sh OUTDIR   (cwd-independent)
set -eu
R=$(cd "$(dirname "$0")/../../.." && pwd); O=$(realpath -m "$1"); mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S=$R/rtl/qwen_sys/split_20261014; H=$R/rtl/hdc
sed 's|^\(\s*initial begin\)$|  initial begin $dumpfile("'$O'/head.vcd"); $dumpvars(0, tb_qkh_head_r4_s.ua.g_t[2]); $dumpvars(0, tb_qkh_head_r4_s.ua.g_t[3]); end\n\1|' \
  $R/rtl/test/qwen_kv_die/tb_qkh_head_r4_s.sv > $O/tb_vcd.sv
grep -q dumpvars $O/tb_vcd.sv || { echo NO_DUMP_HOOK; exit 5; }
SRC="$O/tb_vcd.sv $S/ot_qkh_head_native_r4_s.sv $S/ot_qkh_head_native_r4.sv $S/ot_qkh_head_native_r4_ft.sv
 $S/ot_qkh_head_native.sv $S/ot_qkh_head_native_r3.sv $S/qkh_head_gather_stage.sv $S/qkh_head_stages.sv
 $H/nearhbm/ot_qkh_subtiles.sv $H/nearhbm/ot_qwen_nearhbm_head_hs.sv $H/nearhbm/ot_qwen_nearhbm_prod.sv
 $H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/lib/ot_rst_relay.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat_nr.sv
 $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv"
$V --version
$V --binary -j 16 --timing -O1 --trace --trace-max-width 2048 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkh_head_r4_s \
  -DKVD_HEADS=1 -DKVD_Q_FP32=1 -DKVD_HSTMUT=0 -Mdir $O/obj -o Vtb $SRC > $O/build.log 2>&1 || { tail -20 $O/build.log; echo BUILD_FAILED; exit 3; }
$O/obj/Vtb > $O/run.log 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' $O/run.log | head; ls -la $O/head.vcd
