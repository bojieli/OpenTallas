#!/bin/bash
# HBM-IDXAM3 2026-10-18: bench of the uniform n+12 operand-reader master (pin-registered tile + 1/1 die relays).
# Arg 1 = output dir; optional arg 2 = MUT (run only that variant, exit with its status). Without arg 2: MUT0 must
# pass and MUT1..7 must fail.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-vm-query-n12}")
mkdir -p "$out"
python3 tools/hbm_idx_static_query_vectors.py "$out"
src=(rtl/hbm_accel/index/ot_hbm_idx_vm_query_static_n12.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv rtl/hdc/ot_hdc_delay_rf.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_vm_query_n12.sv)
single=${2:-}
for m in ${single:-0 1 2 3 4 5 6 7}; do
 iverilog -g2012 -s tb_vm_query_n12 -Ptb_vm_query_n12.MUT="$m" -Ptb_vm_query_n12.PERIOD="${PERIOD:-1}" -o "$out/vqn$m.vvp" "${src[@]}" > "$out/vqnbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "vqn$m.vvp") > "$out/vqnrun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/vqnrun$m.log"
 if [ -n "$single" ]; then exit "$rc"; fi
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
