#!/usr/bin/env bash
# S81-L20DIE (10-19): build + run the rank-tree compose bench (tb_idx_tree: 6 x {dsdv_idx_vmux, dsdv_bk_sel, dsdv_idx_tx})
# on the compiler's stimulus.  Run from the source root.  usage: run_idx_tree.sh <out> <tx_mut> <case dir>...
# (one build per tx_mut, one run per case dir; each dir gets run.log + verdict.txt).  Verilator = the closure daemon's
# pinned 5.050 (VL overrides).  Every source the bench reads is listed here.
# S81-L20 idxrd2 (10-19): TXS=1 builds the TX with SRAM_MACRO 1 (ot_sram_1r1w_1024x256 score store / IDX buffer);
# XINIT=1 also leaves every macro array uninitialised and randomises it at start (+verilator+rand+reset+2): the tx must
# write every score it reads in the current job (stale-memory / write-before-use proof).
set -u -o pipefail
OUT=$1; TXM=$2; shift 2
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
SRC="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
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
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv
tools/s81_dv/layer_prog/bk/tb_idx_tree.sv"
TXS=${TXS:-0}; XINIT=${XINIT:-0}
XF=""; RF=""
[ "$XINIT" = 1 ] && { XF="-DOT_MEM_NO_INIT --x-initial unique --x-assign unique"; RF="+verilator+rand+reset+2 +verilator+seed+${SEED:-7}"; }
B="$OUT/build_m${TXM}_s${TXS}_x${XINIT}"
mkdir -p "$B"
( sha256sum $SRC tools/s81_dv/layer_prog/lower_bk.py; $VL --version ) > "$B/sources.sha256"
if [ ! -x "$B/obj/Vtb_idx_tree" ]; then
  /usr/bin/time -v -o "$B/build.time" $VL --binary --timing -j "${J:-16}" -Wno-fatal -Wno-lint -Wno-style \
    -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -DTX_MUT=$TXM -DTX_SRAM=$TXS $XF \
    --top-module tb_idx_tree $SRC -Mdir "$B/obj" > "$B/build.log" 2>&1 || {
    grep -q 'pch' "$B/build.log" && $VL --binary --timing -j "${J:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
      -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -DTX_MUT=$TXM -DTX_SRAM=$TXS $XF --top-module tb_idx_tree \
      $SRC -Mdir "$B/obj" > "$B/build.log" 2>&1; } || { tail -20 "$B/build.log"; echo "IDX_TREE BUILD FAIL"; exit 2; }
fi
rc=0
for D in "$@"; do
  /usr/bin/time -v -o "$D/run_m${TXM}_s${TXS}_x${XINIT}.time" "$B/obj/Vtb_idx_tree" +STIM=$D/stim.txt $(cat "$D/args.txt") $RF > "$D/run_m${TXM}_s${TXS}_x${XINIT}.log" 2>&1
  python3 tools/s81_dv/layer_prog/lower_bk.py tree-rd-check --run "$D/run_m${TXM}_s${TXS}_x${XINIT}.log" --dir "$D" | tee "$D/verdict_m${TXM}_s${TXS}_x${XINIT}.txt" || rc=1
  cp "$D/check_result.json" "$D/check_result_m${TXM}_s${TXS}_x${XINIT}.json"
done
exit $rc
