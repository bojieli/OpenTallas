#!/usr/bin/env bash
set -euo pipefail
out_dir=$(realpath -m "$1");mkdir -p "$out_dir"
root_dir=$(cd "$(dirname "$0")/.." && pwd);cd "$root_dir"
verilator_bin=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$verilator_bin" --binary --timing -O1 -j 8 -Wno-fatal -Wno-WIDTH ${XDEF:-} --top-module tb_hbm_norm_sum_node -Mdir "$out_dir/obj" \
 rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv \
 rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/ot_hdc_sfu.sv \
 rtl/hdc/v41x/ot_hbm_norm_sum_node.sv rtl/test/tb_hbm_norm_sum_node.sv > "$out_dir/build.log" 2>&1
"$out_dir/obj/Vtb_hbm_norm_sum_node" > "$out_dir/run.log" 2>&1
cat "$out_dir/run.log"
grep -q '^NORM_SUM_NODE PASS$' "$out_dir/run.log"
