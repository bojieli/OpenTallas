#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-vm-query-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_query_vectors.py "$out"
src=(rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_vm_query_static.sv)
for m in 0 1 2 3; do
 iverilog -g2012 -s tb_vm_query_static -Ptb_vm_query_static.MUT="$m" -o "$out/vq$m.vvp" "${src[@]}" > "$out/vqbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "vq$m.vvp") > "$out/vqrun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/vqrun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
