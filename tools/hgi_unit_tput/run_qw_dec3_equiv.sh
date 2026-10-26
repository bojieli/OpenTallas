#!/bin/bash
# ot_hgi_qw_dec3 (3-tile decoder, track B) vs ot_hgi_qw_dec cycle-exact equivalence: m0 PASS, m1 (fp4 flip) FAIL.
# usage (repo root): tools/hgi_unit_tput/run_qw_dec3_equiv.sh <out dir> [beats]
set -euo pipefail
out=$(realpath -m "$1"); N=${2:-20000}; mkdir -p "$out"; VL=${VERILATOR:-verilator}
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
     rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
     physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
     rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
     rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv
     rtl/test/hbm_accel/generic/tb_hgi_qw_dec3_equiv.sv)
for m in 0 1; do
  "$VL" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m --top-module tb_hgi_qw_dec3_equiv \
    -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1 &
done
wait
for m in 0 1; do "$out/m$m.obj/sim" +N=$N > "$out/m$m.log" 2>&1 || true; done
ok=1; grep -q "^PASS HGI_QW_DEC3_EQUIV" "$out/m0.log" || ok=0; grep -q "^FAIL HGI_QW_DEC3_EQUIV" "$out/m1.log" || ok=0
tail -1 "$out/m0.log"; tail -1 "$out/m1.log"
[ $ok = 1 ] && echo "QW_DEC3_EQUIV GATE PASS (m0 PASS, m1 FAIL)" | tee "$out/gate" || { echo "QW_DEC3_EQUIV GATE FAIL" | tee "$out/gate"; exit 1; }
