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
rtl/lib/ot_rst_relay.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_idx_vmux_n32.sv
tools/s81_dv/layer_prog/bk/tb_idx_tree.sv"
TXS=${TXS:-0}; XINIT=${XINIT:-0}
# S81-RTLGAP/RG-L20 (10-21): DIEM=1 builds each die as the 72-frame die master dsdv_bk_sel_vmtx (vmux + bk_sel +
# dsdv_idx_tx_n32) instead of the 3 separate units; same stimulus, same checker.
DIEM=${DIEM:-0}; DF=""; [ "$DIEM" = 1 ] && DF="-DTREE_DIEM"
# STW-S81-TOPK-VMUX (10-21): DIEM=2 builds each die as vmtx' dsdv_bk_sel_vmtx_n32 (vmux_n32 + landed PlanA n32 parent +
# vdly VDLY + tx_n32) with the exact defines / sources of the PlanA n32 production build (topk_control_local_1021
# run_production.sh + bkg1.sh VL_EXTRA); its stimulus is booked with lower_bk tree-rd --plana.  VMN32=1 (DIEM 0) swaps
# only the vmux for dsdv_idx_vmux_n32.  VM_MUT / DL_MUT: vmux_n32 / vdly negative controls.
VMN32=${VMN32:-0}; VM_MUT=${VM_MUT:-0}; DL_MUT=${DL_MUT:-0}; VDLY=${VDLY:-28}
[ "$VMN32" = 1 ] && DF="$DF -DTREE_VMN32"
DF="$DF -DVM_MUT=$VM_MUT -DDL_MUT=$DL_MUT -DVDLY=$VDLY"
if [ "$DIEM" = 2 ]; then
  DF="$DF -DTREE_DIEM_N32 -DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_HQ -DOT_HARD_CHILDREN -DOT_S81PH_HQ_INPUT_RAW -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR"
  SRC="physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v
physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v
rtl/lib/ot_sram_showahead_1r1w.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_parts.sv
rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_slice.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_hq_tile.sv
rtl/common/landed_parent/ot_pl_land.sv
rtl/common/landed_parent/ot_pl_land_rst_copy.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/dsdv_bk_plana_station.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/dsdv_bksel_q_pa.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_mux.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_search.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_sel_ctl.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_queue.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_packet.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_ctl.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bksel_c_pa_n32.sv
rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv
rtl/dsrom_sys/s81_dv/idx/dsdv_bk_sel_vmtx_n32.sv
$SRC"
fi
XF=""; RF=""
[ "$XINIT" = 1 ] && { XF="-DOT_MEM_NO_INIT --x-initial unique --x-assign unique"; RF="+verilator+rand+reset+2 +verilator+seed+${SEED:-7}"; }
B="$OUT/build_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}"
mkdir -p "$B"
( sha256sum $SRC tools/s81_dv/layer_prog/lower_bk.py; $VL --version ) > "$B/sources.sha256"
if [ ! -x "$B/obj/Vtb_idx_tree" ]; then
  /usr/bin/time -v -o "$B/build.time" $VL --binary --timing -j "${J:-16}" -Wno-fatal -Wno-lint -Wno-style \
    -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -DTX_MUT=$TXM -DTX_SRAM=$TXS $DF $XF \
    --top-module tb_idx_tree $SRC -Mdir "$B/obj" > "$B/build.log" 2>&1 || {
    grep -q 'pch' "$B/build.log" && $VL --binary --timing -j "${J:-16}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
      -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -DTX_MUT=$TXM -DTX_SRAM=$TXS $DF $XF --top-module tb_idx_tree \
      $SRC -Mdir "$B/obj" > "$B/build.log" 2>&1; } || { tail -20 "$B/build.log"; echo "IDX_TREE BUILD FAIL"; exit 2; }
fi
rc=0
for D in "$@"; do
  /usr/bin/time -v -o "$D/run_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}.time" "$B/obj/Vtb_idx_tree" +STIM=$D/stim.txt $(cat "$D/args.txt") $RF > "$D/run_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}.log" 2>&1
  python3 tools/s81_dv/layer_prog/lower_bk.py tree-rd-check --run "$D/run_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}.log" --dir "$D" | tee "$D/verdict_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}.txt" || rc=1
  cp "$D/check_result.json" "$D/check_result_m${TXM}_s${TXS}_x${XINIT}_d${DIEM}${VTAG:-}.json"
done
exit $rc
