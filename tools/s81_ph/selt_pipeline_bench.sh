#!/bin/bash
# Full-shape selector transaction gate. Build/sim have no wall-clock deadline.
set -euo pipefail
out=$1; tag=$2; pipe=$3; shift 3
mkdir -p "$out/$tag"
verilator --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_s81ph_sel -GSEARCH_PIPE="$pipe" "$@" -Mdir "$out/$tag/obj" \
 rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_ph/dsfd_bk_selector.sv \
 rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv > "$out/$tag/build.log" 2>&1
"$out/$tag/obj/Vtb_s81ph_sel" > "$out/$tag/run.log" 2>&1
grep '^RESULT\|^FAIL\|^fault case\|^SEG' "$out/$tag/run.log" > "$out/$tag/summary.txt" || true
if grep -q '^RESULT PASS' "$out/$tag/run.log" && ! grep -q '^FAIL' "$out/$tag/run.log"; then
 echo 'SELT_PIPE PASS'
else
 echo 'SELT_PIPE FAIL'
 exit 1
fi
