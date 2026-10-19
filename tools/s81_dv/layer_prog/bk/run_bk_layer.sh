#!/usr/bin/env bash
# TOK-S81-GAPS/IDX: build + run the bk_sel layer-job bench (tb_bk_layer) on the compiler's stimulus.  Run from the
# source root.  usage: run_bk_layer.sh <out> <stim dir>... (one build, one run per stim dir; each dir gets run.log).
# Verilator = the closure daemon's pinned 5.050 (VL overrides).  Every source the bench reads is listed here.
set -u -o pipefail
OUT=$1; shift
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
SRC="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
rtl/common/ot_fwd_link_stage.sv
rtl/hdc/ot_hdc_prefix.sv
rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
rtl/dsrom_sys/s81_dv/unit/ot_dsdv_vstop.sv
rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv
rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
rtl/hdc/v41x/ot_hdc_v41x_sel.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_g.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv
rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv
tools/s81_dv/layer_prog/bk/tb_bk_layer.sv"
( sha256sum $SRC; $VL --version ) > "$OUT/sources.sha256"
$VL --version > "$OUT/verilator.version"
if [ ! -x "$OUT/obj/Vtb_bk_layer" ]; then
  /usr/bin/time -v -o "$OUT/build.time" $VL --binary --timing -j "${J:-16}" -Wno-fatal -Wno-lint -Wno-style \
    -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE \
    --top-module tb_bk_layer $SRC -Mdir "$OUT/obj" > "$OUT/build.log" 2>&1 || { tail -20 "$OUT/build.log"; echo "BK_LAYER BUILD FAIL"; exit 2; }
fi
rc=0
for D in "$@"; do
  n=$(python3 -c "import json,sys;print(json.load(open('$D/meta.json'))['ncyc'])")
  /usr/bin/time -v -o "$D/run.time" "$OUT/obj/Vtb_bk_layer" +STIM=$D/stim.txt +NCYC=$n > "$D/run.log" 2>&1
  python3 tools/s81_dv/layer_prog/lower_bk.py check --run "$D/run.log" --dir "$D" | tee "$D/verdict.txt" || rc=1
done
exit $rc
