#!/usr/bin/env bash
# S81U-SVC: build + run the dsdv_svc_sx exact bench (16 slices vs the golden engine lane tree).
# S81U-SVCX4: the split form (8 x dsdv_svc_sx_hrow half-row centre leaves + closed dsfd_dvrly_276 relay stations).
# Usage (repo root): tools/s81_dv/svc_rs/sx_bench.sh OUTDIR [base|mut1|mut2|mutorder|mutskew|selmut|fmask] [seed...]
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; V=${2:-base}; shift 2 || true; SEEDS=${*:-1 2}
D=rtl/dsrom_sys/s81_dv/svc_rs
DEF=()
case "$V" in
  base) ;; mut1) DEF=(-DMUT=1);; mut2) DEF=(-DMUT=2);; mutorder) DEF=(-DDSDV_SX_MUT_ORDER);;
  mutskew) DEF=(-DSX_MUT_SKEW);; selmut) DEF=(-DOT_HROW_SEL_MUT);;   # S81-KITS-HROW: one replicated select copy wrong
  fmask) DEF=(-DSX_FMASK);; fmaskmut) DEF=(-DSX_FMASK -DSX_FMASK_MUT);;   # S81-P9-FACE: role-derived face-masked slices
  *) echo "variant?" >&2; exit 2;;
esac
mkdir -p "$O/$V"
"$VL" --binary --top-module tb_dsdv_svc_sx -Mdir "$O/$V/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
  -I$D "${DEF[@]}" rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fp32_f12.sv \
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv \
  rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv \
  $D/dsdv_svc_sx_hrow.sv $D/dsdv_svc_sx.sv $D/test/tb_dsdv_svc_sx.sv > "$O/$V/build.log" 2>&1 || { tail -30 "$O/$V/build.log"; exit 1; }
for s in $SEEDS; do "$O/$V/obj/Vtb_dsdv_svc_sx" +seed=$s > "$O/$V/run_s$s.log" 2>&1 || true
  echo "$V seed $s: $(grep -E 'SX root|SX_BENCH' "$O/$V/run_s$s.log" | tr '\n' ' ')"
  grep -E '^(SX root|SX_BENCH)' "$O/$V/run_s$s.log" || true; done   # the verdict lines on stdout, at line start (closure-loop regexes)
