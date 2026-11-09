#!/bin/bash
set -e
ROOT=$PWD
OUT=$1;MUT=${2:-0}
mkdir -p "$OUT"
S="$ROOT/rtl"
VL=$HOME/.local/opentallas-tools/bin/verilator
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_sml_fold2 -Mdir "$OUT/obj" -j 4 --unroll-count 4 -fno-dfg \
  -GMUT=$MUT -CFLAGS -O1 "${SMTX[@]}" \
  "$S/dsrom_sys/s81_dv/su_sm/test/tb_sml_fold2.sv" "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_sml_fold2.sv" "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv" \
  "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv" \
  "$S/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" "$S/hdc/ot_hdc_delay.sv" "$S/hdc/ot_hdc_fastfp_lat_f12.sv" \
  "$S/hdc/ot_hdc_fastfp.sv" "$S/hdc/ot_hdc_fp32_add_lat.sv" "$S/hdc/ot_hdc_fp32_f12.sv" "$S/hdc/ot_hdc_fp32_mul_lat.sv" \
  "$S/hdc/ot_hdc_prefix.sv" "$S/hdc/ot_hdc_sfu.sv" "$S/hdc/v41x/ot_dsrom_fp32_add_l6.sv" "$S/hdc/v41x/ot_dsrom_su_add6.sv" \
  "$S/hdc/v41x/ot_dsrom_su_f12.sv" "$S/hdc/v41x/ot_dsrom_su_fdiv_f12.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_add6.sv" \
  "$S/hdc/v41x/ot_dsrom_su_softmax_add.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_f12r.sv" \
  "$S/hdc/v41x/ot_dsrom_su_softmax_m9.sv" "$S/hdc/v41x/ot_hdc_v41x_sfu.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_sml_fold2" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
