#!/bin/bash
# QC-PLAN-F4A: F4A column-SRAM MIF0 kits for vmr / rp1 (COORD RULING QC-PLAN-F4A: kit specs -> column SRAM, MIF0).
# base = gen_core_kit_qc.py on the F4A plan delta (recipes_f4a.json: F4A spec, plan F4A pin table, track-snapped sites, G1);
# overlay = the QC-SU-KITS-2 MIF0 SU recipe (cores/su/f4a/kit_overlay, copied unchanged from prog_m0): pushdown (ck interior
# M5 pin + die ft cells + entry root FIRM), face pin registers, macro-pin flops, entry-root-only placement spec; the core
# H-tree is computed by the plan model on the PLACED geometry and built at CTS (a later step).
# usage: mk_kits_f4a.sh OUTDIR
set -euo pipefail
W=$(cd "$(dirname "$0")/../../.." && pwd); OUT=$1; mkdir -p "$OUT"; cd "$W"
QC=physical/die_plan/qwen_compute; OV=$QC/cores/su/f4a/kit_overlay
for m in qfd_dv_s8x_vmr qfd_dv_s8_crh_rp1; do
  python3 $QC/cores/legacy/gen_core_kit_qc.py --module ${m}_f4a --recipes $QC/cores/legacy/recipes_f4a.json \
      --plan $QC/candidate_qc_f4a_1026.json --out "$OUT" | tail -1
  K=$OUT/${m}_f4a
  (cd $OV && tar cf - --exclude SOURCE_MD5.txt .) | (cd $K && tar xf -)
  sed -i 's/qcsuk2-/qcf4a-/; s#python3 "$K/../collect_native.py" "$K" || true#true#' $K/place_m0.sh $K/cts_m0.sh
  cat > $K/mscts_place.tcl <<'T'
# QC-PLAN-F4A MIF0 placement spec: entry root only at the plan entry (125.28, 108) = centre of the F4A outline (RULING (3));
# the core tree (L1 islands, L2/L3, leaves) is re-derived by the plan model (f4_g4c) on this kit's placed geometry and built
# at CTS from its own spec.
set ot_ms_port ck
set ot_ms_root {125.280 108.000}
set ot_h_entry_n 0
set ot_h_fixed {
 {ot_ms_root BUFx24_ASAP7_75t_R 125.280 108.000}
}
set ot_ms_tree {}
set ot_ms_leaves {}
set ot_ms_macros {}
T
  MPF="export OT_MPF_HALO_UM = 4.32"
  if [ $m = qfd_dv_s8x_vmr ]; then MPF="$MPF
export OT_MPF_TREE = 1
export OT_MPF_SHARED = 1"; fi
  cat >> $K/config.mk <<C

# ---- QC-PLAN-F4A 2026-10-26: F4A column-SRAM MIF0 kit = QC-SU-KITS-2 MIF0 SU recipe (prog_m0) on the F4A plan delta.
# Module defaults (MIF=0, no top params).  ck = interior M5 pin at (125.292, 108) (pushdown.tcl), entry root FIRM at the
# plan entry; PRE_GPL = pushdown + face pin registers + macro-pin flops; RC = the SU lineage rc_cal (MODEL-REFIT basis).
# Placement only here; CTS+GRT stage appended after the plan model is re-run on the placed geometry.  No pads / trims.
export DESIGN_NICKNAME = kq_${m}_f4a_m0
export VERILOG_TOP_PARAMS =
export HOLD_SLACK_MARGIN = 5
export SKIP_INCREMENTAL_REPAIR = 1
override export LAYER_PARASITICS_FILE = /work/cf/rc_cal.tcl
override export SET_RC_TCL = /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
export OT_RC_CAL = 0.8,0.9
override export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_m0.tcl
override export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_m0.tcl
$MPF
export OT_CK_PIN_X = 125.292
export OT_CK_PIN_Y = 108.000
export OT_MSCTS_SPEC = /work/mscts_place.tcl
export OT_MSCTS_EXPLICIT = 1
export OT_MSCTS_ITERS = 0
export OT_H_NO_TRITON = 1
export OT_MSCTS_TRUNK_CELL = BUFx16f_ASAP7_75t_R
export OT_S5_MAX_WIRE_UM = 100
export MIN_CLK_ROUTING_LAYER = M4
export MAX_CLK_ROUTING_LAYER = M5
C
  echo "KIT $K config_md5 $(md5sum < $K/config.mk | cut -c1-12)"
done
