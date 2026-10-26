#!/usr/bin/env bash
# S81/H23 (10-24): build + run the dsdv_svc_att IK_ROW exact bench (tb_dsdv_svc_att_ik) and its negative controls.
# usage (repo root or any cwd): run_svc_att_ik.sh <outdir> [variant ...]; variants: base (must PASS), mut4 (region hash
# without j[15:12]: must FAIL), mut5 (scale byte of key c ^ 1: must FAIL), mut1 (OWN_ROW scale byte: must FAIL).
# Prints SVCIK_GATE PASS when base passes and every listed mutant fails.  Verilator = the daemon's pinned 5.050.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$1; shift; VARS=${*:-"base mut4 mut5 mut1"}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$R/rtl/dsrom_sys/s81_dv/svc_rs
SRC="rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
 rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_att_ik.sv"
mkdir -p "$O"; bad=0
for v in $VARS; do
  case $v in base) M=0;; mut*) M=${v#mut};; *) echo "variant? $v"; exit 2;; esac
  B=$O/$v; mkdir -p "$B/obj"
  if [ ! -x "$B/obj/Vtb_dsdv_svc_att_ik" ]; then
    $VL --binary --timing -j "${J:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DSVCQ_ENG_FG3 -DTB_MUT=$M \
      --top-module tb_dsdv_svc_att_ik -Mdir "$B/obj" $(for f in $SRC; do echo "$R/$f"; done) > "$O/build_$v.log" 2>&1 \
      || { echo "BUILD_FAIL $v"; tail -20 "$O/build_$v.log"; bad=1; continue; }
  fi
  for s in ${SEEDS:-1 2 3}; do
    "$B/obj/Vtb_dsdv_svc_att_ik" +seed=$s > "$O/run_${v}_s$s.log" 2>&1
    l=$(grep -h '^SVCIK ' "$O/run_${v}_s$s.log" | tail -1); echo "$v s$s: $l"
    if [ "$v" = base ]; then case "$l" in *verdict=PASS*) ;; *) bad=1;; esac
    else case "$l" in *verdict=FAIL*) ;; *) echo "MUTANT_NOT_CAUGHT $v s$s"; bad=1;; esac; fi
  done
done
[ $bad = 0 ] && echo "SVCIK_GATE PASS" || echo "SVCIK_GATE FAIL"; exit $bad
