#!/bin/bash
# PG-ACTIVITY-KVHBM 10-27: measured activity of the KV P.V pair core (kv3_pv_pair = 2 x ot_qwen_tp8_pv_slice_t, RESET_PIN 1).
# Bench = pv_pair_bench.sh form (tb_qwen_tp8_pv_wide_pair, golden pv_pair_ref.py, PV_PAIR PASS), one context T (default 1000),
# Verilator 5.050 --trace (non-hierarchical), VCD of u.g_col[0].u_col.g_bank[0|1].u_bank.   usage: kv_pv_activity_sim.sh OUTDIR [T]
set -eu
R=$(cd "$(dirname "$0")/../../.." && pwd); O=$(realpath -m "$1"); T=${2:-1000}; mkdir -p "$O"; cd $R
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sed 's|^\( initial begin\)$|  initial begin $dumpfile("'$O'/pv.vcd"); $dumpvars(0, tb_qwen_tp8_pv_wide_pair.u.g_col[0].u_col.g_bank[0].u_bank); $dumpvars(0, tb_qwen_tp8_pv_wide_pair.u.g_col[0].u_col.g_bank[1].u_bank); end\n\1|' \
  rtl/test/nearhbm/tb_qwen_tp8_pv_wide_pair.sv > $O/tb_vcd.sv
grep -q dumpvars $O/tb_vcd.sv || { echo NO_DUMP_HOOK; exit 5; }
$V --binary --timing -O1 --trace --trace-max-width 20000 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 \
 --top-module tb_qwen_tp8_pv_wide_pair -GPAIR=0 -GMUT=0 -GCTL_RESET_PIN=1 -GLEAF_RESET_PIN=1 --Mdir $O/obj \
 rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $O/tb_vcd.sv > $O/build.log 2>&1 || { tail -20 $O/build.log; echo BUILD_FAILED; exit 3; }
python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair 0 --seed $T --out $O/vec > $O/ref.log
$O/obj/Vtb_qwen_tp8_pv_wide_pair +VEC=$O/vec +CTX=$T +MODE=steady > $O/run.log 2>&1 || true
grep -E "^PV_PAIR|MISMATCH" $O/run.log | tail -2; ls -la $O/pv.vcd
